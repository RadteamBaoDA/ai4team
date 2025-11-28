import json
import importlib.util
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_endpoints_module(force_reload=False):
    repo_root = Path(__file__).resolve().parents[4]
    module_root = repo_root / "guardrails" / "src" / "ollama_guardrails"
    package_name = "ollama_guardrails"
    api_package_name = f"{package_name}.api"
    module_name = f"{api_package_name}.endpoints_ollama"

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
        str(module_root / "api" / "endpoints_ollama.py"),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


endpoints_ollama = _load_endpoints_module()
create_ollama_endpoints = endpoints_ollama.create_ollama_endpoints


class DummyConfig(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def get_int(self, key, default=0):
        return int(super().get(key, default))


class DummyGuardManager:
    def __init__(self, input_result=None, output_result=None):
        self.input_result = input_result or {"allowed": True, "scanners": {}}
        self.output_result = output_result or {"allowed": True, "scanners": {}}

    async def scan_input(self, *args, **kwargs):
        return self.input_result

    async def scan_output(self, *args, **kwargs):
        return self.output_result


class DummyResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    async def aclose(self):
        return None


class DummyHTTPClient:
    def __init__(self, response):
        self._response = response

    async def post(self, *args, **kwargs):
        return self._response


DEFAULT_CONFIG = {
    "inline_guard_errors": True,
    "enable_input_guard": True,
    "enable_output_guard": True,
    "ollama_path": "/api/generate",
    "ollama_url": "http://localhost:11434",
    "request_timeout": 30,
}


def _make_test_client(guard_manager, overrides=None):
    global endpoints_ollama, create_ollama_endpoints

    endpoints_ollama = _load_endpoints_module(force_reload=True)
    create_ollama_endpoints = endpoints_ollama.create_ollama_endpoints

    config_data = dict(DEFAULT_CONFIG)
    if overrides:
        config_data.update(overrides)
    config = DummyConfig(config_data)

    router = create_ollama_endpoints(
        config=config,
        guard_manager=guard_manager,
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_generate_inline_input_block_returns_markdown():
    guard_manager = DummyGuardManager(
        input_result={
            "allowed": False,
            "scanners": {
                "PromptInjection": {
                    "passed": False,
                    "reason": "injection detected",
                    "score": 0.99,
                }
            },
        }
    )
    client = _make_test_client(guard_manager)

    response = client.post("/api/generate", json={"model": "phi", "prompt": "ignore"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"]["type"] == "input_blocked"
    assert payload["guard"]["failed_scanners"][0]["scanner"] == "PromptInjection"
    assert payload["response"].startswith("### Input blocked")


def test_generate_inline_output_block_uses_markdown(monkeypatch):
    guard_manager = DummyGuardManager(
        input_result={"allowed": True, "scanners": {}},
        output_result={
            "allowed": False,
            "scanners": {
                "Toxicity": {
                    "passed": False,
                    "reason": "toxic",
                    "score": 0.8,
                }
            },
        },
    )
    client = _make_test_client(guard_manager)

    async def fake_forward_request(*args, **kwargs):
        return DummyResponse({"response": "bad text", "done": True}), None

    monkeypatch.setattr(endpoints_ollama, "forward_request", fake_forward_request)

    response = client.post("/api/generate", json={"model": "phi", "prompt": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert "error" in payload, payload
    assert payload["error"]["type"] == "output_blocked"
    assert payload["guard"]["failed_scanners"][0]["scanner"] == "Toxicity"
    assert "Response blocked" in payload["response"]


def test_chat_inline_input_block_returns_markdown():
    guard_manager = DummyGuardManager(
        input_result={
            "allowed": False,
            "scanners": {
                "Secrets": {
                    "passed": False,
                    "reason": "leak",
                }
            },
        }
    )
    client = _make_test_client(guard_manager)

    response = client.post(
        "/api/chat",
        json={
            "model": "phi",
            "messages": [
                {"role": "user", "content": "My password is ..."}
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"]["type"] == "input_blocked"
    assert payload["message"]["content"].startswith("### Input blocked")


def test_chat_inline_output_block_returns_markdown(monkeypatch):
    guard_manager = DummyGuardManager(
        input_result={"allowed": True, "scanners": {}},
        output_result={
            "allowed": False,
            "scanners": {
                "NoCode": {
                    "passed": False,
                    "reason": "code detected",
                }
            },
        },
    )
    client = _make_test_client(guard_manager)

    dummy_response = DummyResponse(
        {"message": {"role": "assistant", "content": "unsafe"}, "done": True}
    )

    def fake_get_http_client():
        return DummyHTTPClient(dummy_response)

    monkeypatch.setattr(endpoints_ollama, "get_http_client", fake_get_http_client)

    response = client.post(
        "/api/chat",
        json={
            "model": "phi",
            "messages": [
                {"role": "user", "content": "write code"}
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "error" in payload, payload
    assert payload["error"]["type"] == "output_blocked"
    assert "Response blocked" in payload["message"]["content"]