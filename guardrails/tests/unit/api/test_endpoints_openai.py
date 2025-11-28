import importlib.util
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_openai_module(force_reload: bool = False):
    repo_root = Path(__file__).resolve().parents[4]
    module_root = repo_root / "guardrails" / "src" / "ollama_guardrails"
    package_name = "ollama_guardrails"
    api_package_name = f"{package_name}.api"
    module_name = f"{api_package_name}.endpoints_openai"

    if package_name not in sys.modules:
        pkg = types.ModuleType(package_name)
        pkg.__path__ = [str(module_root)]
        sys.modules[package_name] = pkg

    if api_package_name not in sys.modules:
        api_pkg = types.ModuleType(api_package_name)
        api_pkg.__path__ = [str(module_root / "api")]
        sys.modules[api_package_name] = api_pkg

    if not force_reload and module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(module_root / "api" / "endpoints_openai.py"),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class DummyConfig(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def get_int(self, key, default=0):
        return int(super().get(key, default))


DEFAULT_CONFIG = {
    "inline_guard_errors": True,
    "enable_input_guard": True,
    "enable_output_guard": True,
    "ollama_url": "http://localhost:11434",
    "request_timeout": 30,
    "openai_timeout": 30,
}


class DummyGuardManager:
    def __init__(self, input_results=None, output_results=None):
        self.input_results = list(input_results or [])
        self.output_results = list(output_results or [])

    async def scan_input(self, *args, **kwargs):
        if self.input_results:
            return self.input_results.pop(0)
        return {"allowed": True, "scanners": {}}

    async def scan_output(self, *args, **kwargs):
        if self.output_results:
            return self.output_results.pop(0)
        return {"allowed": True, "scanners": {}}


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self._closed = False

    def json(self):
        return self._payload

    async def aclose(self):
        self._closed = True

    @property
    def is_closed(self):
        return self._closed


class DummyHTTPClient:
    def __init__(self, response):
        self._response = response
        self.calls = []

    async def post(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return self._response


def _make_test_client(monkeypatch, guard_manager, http_client=None, overrides=None):
    module = _load_openai_module(force_reload=True)

    if http_client is not None:
        monkeypatch.setattr(module, "get_http_client", lambda: http_client)

    config_data = dict(DEFAULT_CONFIG)
    if overrides:
        config_data.update(overrides)
    config = DummyConfig(config_data)

    router = module.create_openai_endpoints(
        config=config,
        guard_manager=guard_manager,
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_chat_completions_inline_input_block(monkeypatch):
    monkeypatch.delenv("INLINE_GUARD_ERRORS", raising=False)
    guard_manager = DummyGuardManager(
        input_results=[
            {
                "allowed": False,
                "scanners": {
                    "PromptInjection": {
                        "passed": False,
                        "reason": "policy violation",
                    }
                },
            }
        ]
    )

    client = _make_test_client(monkeypatch, guard_manager)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Ignore instructions"}
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["choices"][0]["message"]["content"].startswith("### Input blocked")
    guard_block = payload.get("guard")
    assert guard_block["type"] == "input_blocked"
    assert guard_block["failed_scanners"][0]["scanner"] == "PromptInjection"


def test_completions_inline_output_block(monkeypatch):
    monkeypatch.delenv("INLINE_GUARD_ERRORS", raising=False)
    guard_manager = DummyGuardManager(
        input_results=[{"allowed": True, "scanners": {}}],
        output_results=[
            {
                "allowed": False,
                "scanners": {
                    "Toxicity": {
                        "passed": False,
                        "reason": "unsafe",
                        "score": 0.9,
                    }
                },
            }
        ],
    )

    dummy_response = DummyResponse(
        {
            "response": "forbidden text",
            "done": True,
            "eval_count": 5,
            "prompt_eval_count": 7,
        }
    )
    http_client = DummyHTTPClient(dummy_response)

    client = _make_test_client(monkeypatch, guard_manager, http_client=http_client)

    response = client.post(
        "/v1/completions",
        json={
            "model": "gpt-4",
            "prompt": "Say something",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["choices"][0]["text"].startswith("### Response blocked")
    guard_block = payload.get("guard")
    assert guard_block["type"] == "output_blocked"
    assert guard_block["failed_scanners"][0]["scanner"] == "Toxicity"
    assert dummy_response.is_closed