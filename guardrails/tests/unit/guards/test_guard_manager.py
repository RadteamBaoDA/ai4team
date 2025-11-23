import asyncio
from types import MethodType, SimpleNamespace

import pytest

from ollama_guardrails.guards import guard_manager


@pytest.fixture
def stub_guard_env(monkeypatch):
    module = guard_manager

    class StubScanner:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class StubAnonymize(StubScanner):
        def __init__(self, vault, **kwargs):
            super().__init__(vault, **kwargs)
            self.vault = vault

    class StubVault:
        pass

    for name in [
        "InputBanSubstrings",
        "PromptInjection",
        "InputToxicity",
        "Secrets",
        "InputCode",
        "OutputBanSubstrings",
        "OutputToxicity",
        "MaliciousURLs",
        "NoRefusal",
        "OutputCode",
    ]:
        monkeypatch.setattr(module, name, StubScanner)

    monkeypatch.setattr(module, "Anonymize", StubAnonymize)
    monkeypatch.setattr(module, "Vault", StubVault)

    model_stub = lambda: SimpleNamespace(path=None, kwargs={})
    monkeypatch.setattr(module, "PROMPT_INJECTION_MODEL", model_stub())
    monkeypatch.setattr(module, "TOXICITY_MODEL", model_stub())
    monkeypatch.setattr(module, "MALICIOUS_URLS_MODEL", model_stub())
    monkeypatch.setattr(module, "NO_REFUSAL_MODEL", model_stub())
    monkeypatch.setattr(module, "CODE_MODEL", model_stub())
    monkeypatch.setattr(module, "DEBERTA_AI4PRIVACY_v2_CONF", {"DEFAULT_MODEL": model_stub()})

    def fake_scan_prompt(scanners, prompt, fail_fast):
        results_valid = {f"Scanner{i}": True for i in range(len(scanners))}
        results_score = {name: 0.25 for name in results_valid}
        return prompt.upper(), results_valid, results_score

    def fake_scan_output(scanners, prompt, text, fail_fast):
        results_valid = {f"Out{i}": True for i in range(len(scanners))}
        results_score = {name: 0.75 for name in results_valid}
        return text[::-1], results_valid, results_score

    monkeypatch.setattr(module, "scan_prompt", fake_scan_prompt)
    monkeypatch.setattr(module, "scan_output", fake_scan_output)
    monkeypatch.setattr(module, "HAS_LLM_GUARD", True)

    return module


def test_detect_device_override_cpu(monkeypatch):
    monkeypatch.setenv("LLM_GUARD_DEVICE", "cpu")
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=False)
    assert manager.device == "cpu"


def test_use_local_models_flag(monkeypatch):
    monkeypatch.setenv("LLM_GUARD_USE_LOCAL_MODELS", "1")
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=False)
    assert manager.use_local_models is True


def test_count_tokens_uses_stub_encoder(monkeypatch):
    class DummyEncoder:
        def encode(self, text):
            return list(text)

    class DummyTiktoken:
        def get_encoding(self, name):
            return DummyEncoder()

    monkeypatch.setattr(guard_manager, "tiktoken", DummyTiktoken())
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=False)
    assert manager._count_tokens("tokens") == 6


def test_ensure_input_scanners_initialized_creates_vault(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=True, enable_output=False, lazy_init=True)
    manager._ensure_input_scanners_initialized()
    assert manager._input_scanners_initialized is True
    assert manager.vault is not None
    assert len(manager.input_scanners) > 0


def test_ensure_output_scanners_initialized_builds_scanners(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=True, lazy_init=True)
    manager._ensure_output_scanners_initialized()
    assert manager._output_scanners_initialized is True
    assert len(manager.output_scanners) > 0


def test_initialize_all_eager_mode(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=True, enable_output=True, lazy_init=False)
    assert manager._initialized is True
    assert len(manager.input_scanners) > 0
    assert len(manager.output_scanners) > 0


@pytest.mark.asyncio
async def test_scan_input_returns_sanitized_payload(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=True, enable_output=False, lazy_init=True)
    result = await manager.scan_input("hello world")
    assert result["allowed"] is True
    assert result["sanitized"] == "HELLO WORLD"
    assert result["scanner_count"] == len(manager.input_scanners)


@pytest.mark.asyncio
async def test_scan_input_block_on_error_returns_error(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=True, enable_output=False, lazy_init=False)
    manager.input_scanners = [object()]

    async def failing(self, prompt):
        raise RuntimeError("input boom")

    manager._run_input_scanners = MethodType(failing, manager)
    result = await manager.scan_input("blocked", block_on_error=True)
    assert result["allowed"] is False
    assert result["error"] == "input boom"


@pytest.mark.asyncio
async def test_run_input_scanners_handles_scan_prompt_errors(stub_guard_env, monkeypatch):
    manager = guard_manager.LLMGuardManager(enable_input=True, enable_output=False, lazy_init=False)
    manager.input_scanners = [object()]

    def blowing_scan(scanners, prompt, fail_fast):
        raise RuntimeError("scan failure")

    monkeypatch.setattr(guard_manager, "scan_prompt", blowing_scan)
    sanitized, allowed, details = await manager._run_input_scanners("prompt")
    assert sanitized == "prompt"
    assert allowed is False
    assert details["error"] == "scan failure"


@pytest.mark.asyncio
async def test_scan_output_returns_reversed_text(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=True, lazy_init=True)
    result = await manager.scan_output("GOOD", prompt="src")
    assert result["allowed"] is True
    assert result["sanitized"] == "DOOG"
    assert result["scanner_count"] == len(manager.output_scanners)


@pytest.mark.asyncio
async def test_scan_output_block_on_error(stub_guard_env):
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=True, lazy_init=False)
    manager.output_scanners = [object()]

    async def failing(self, text, prompt="", block_on_error=False):
        raise RuntimeError("output boom")

    manager._run_output_scanners = MethodType(failing, manager)
    result = await manager.scan_output("oops", block_on_error=True)
    assert result["allowed"] is False
    assert result["error"] == "output boom"


@pytest.mark.asyncio
async def test_run_output_scanners_handles_scan_errors(stub_guard_env, monkeypatch):
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=True, lazy_init=False)
    manager.output_scanners = [object()]

    def blowing_scan(scanners, prompt, text, fail_fast):
        raise RuntimeError("failure")

    monkeypatch.setattr(guard_manager, "scan_output", blowing_scan)
    sanitized, allowed, details = await manager._run_output_scanners("text")
    assert sanitized == "text"
    assert allowed is False
    assert details["error"] == "failure"


def test_configure_local_models_set_paths(stub_guard_env, monkeypatch):
    monkeypatch.setenv("LLM_GUARD_MODELS_PATH", "/models")
    manager = guard_manager.LLMGuardManager(enable_input=False, enable_output=False, lazy_init=True)
    manager.use_local_models = True
    manager._configure_local_models_in()
    assert guard_manager.PROMPT_INJECTION_MODEL.path.endswith("prompt-injection-v2")
    manager._configure_local_models_out()
    assert guard_manager.NO_REFUSAL_MODEL.path.endswith("distilroberta-base-rejection-v1")