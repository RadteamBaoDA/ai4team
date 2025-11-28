import asyncio
from types import SimpleNamespace

import httpx
import pytest

from ollama_guardrails.middleware import http_client


class DummyConfig(dict):
    def get(self, key, default=None):
        return super().get(key, default)


@pytest.fixture(autouse=True)
def reset_http_client(monkeypatch):
    monkeypatch.setattr(http_client, "_HTTP_CLIENT", None)
    yield
    monkeypatch.setattr(http_client, "_HTTP_CLIENT", None)


def test_env_helpers(monkeypatch):
    monkeypatch.setenv("TEST_INT", "42")
    monkeypatch.setenv("TEST_FLOAT", "3.14")
    monkeypatch.setenv("TEST_BOOL", "on")
    assert http_client._env_int("TEST_INT", 0) == 42
    assert http_client._env_int("MISSING_INT", 5) == 5
    assert http_client._env_float("TEST_FLOAT", 0.0) == pytest.approx(3.14)
    assert http_client._env_float("BAD_FLOAT", 1.5) == 1.5
    assert http_client._env_bool("TEST_BOOL", False) is True
    assert http_client._env_bool("MISSING_BOOL", True) is True


def test_summarize_and_estimate_payload():
    payload = {"text": "hello\nworld"}
    summary = http_client._summarize_payload(payload, limit=5)
    assert summary.endswith("(truncated)")
    estimate = http_client._estimate_payload_size({"a": [1, 2, 3]})
    assert estimate > 0


@pytest.mark.asyncio
async def test_json_stream_splits_chunks():
    stream = http_client._json_stream({"key": "value"}, chunk_size=5)
    chunks = [chunk async for chunk in stream]
    assert b"".join(chunks) == b'{"key":"value"}'
    assert len(chunks) > 1


@pytest.mark.asyncio
async def test_prepare_payload_streams_large_body(monkeypatch):
    monkeypatch.setattr(http_client, "_STREAM_THRESHOLD", 10)
    payload = {"big": "x" * 50}
    plan = http_client._prepare_payload(payload)
    assert plan["json"] is None
    assert plan["content"] is not None
    chunks = [chunk async for chunk in plan["content"]]
    assert b"".join(chunks).startswith(b"{")


def test_prepare_payload_small_body(monkeypatch):
    monkeypatch.setattr(http_client, "_STREAM_THRESHOLD", 10_000)
    plan = http_client._prepare_payload({"small": True})
    assert plan["json"] == {"small": True}
    assert plan["content"] is None


def test_get_http_client_respects_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HTTP_MAX_CONNECTIONS", "20")
    monkeypatch.setenv("OLLAMA_HTTP_MAX_KEEPALIVE", "10")
    monkeypatch.setenv("OLLAMA_HTTP_KEEPALIVE_EXPIRY", "5")
    monkeypatch.setenv("OLLAMA_HTTP_READ_TIMEOUT", "2")
    monkeypatch.setenv("OLLAMA_HTTP_CONNECT_TIMEOUT", "1")
    monkeypatch.setenv("OLLAMA_HTTP_WRITE_TIMEOUT", "3")
    monkeypatch.setenv("OLLAMA_HTTP_POOL_TIMEOUT", "4")
    monkeypatch.setenv("HTTPX_TRUST_ENV", "true")
    monkeypatch.setenv("OLLAMA_HTTP_RETRIES", "7")

    def fake_import(name):
        raise ImportError("no h2")

    created = {}

    class DummyTransport:
        def __init__(self, retries, http2):
            created["transport"] = {"retries": retries, "http2": http2}

    class DummyAsyncClient:
        def __init__(self, **kwargs):
            created["client"] = kwargs

        async def aclose(self):
            created["client"]["closed"] = True

    monkeypatch.setattr(http_client.importlib, "import_module", fake_import)
    monkeypatch.setattr(http_client.httpx, "AsyncHTTPTransport", DummyTransport)
    monkeypatch.setattr(http_client.httpx, "AsyncClient", DummyAsyncClient)

    client = http_client.get_http_client(max_pool=50)
    assert client is not None
    limits = created["client"]["limits"]
    assert limits.max_connections == 20
    assert created["transport"]["http2"] is False
    assert created["client"]["trust_env"] is True


@pytest.mark.asyncio
async def test_close_http_client(monkeypatch):
    class DummyClient:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    dummy = DummyClient()
    monkeypatch.setattr(http_client, "_HTTP_CLIENT", dummy)
    await http_client.close_http_client()
    assert dummy.closed is True
    assert http_client._HTTP_CLIENT is None


@pytest.mark.asyncio
async def test_safe_json_success_and_failure():
    ok = httpx.Response(200, content=b'{"foo": 1}')
    data, err = await http_client.safe_json(ok)
    assert data == {"foo": 1}
    assert err is None

    bad = httpx.Response(200, content=b"not json")
    data, err = await http_client.safe_json(bad)
    assert data is None
    assert "Expecting" in err


@pytest.mark.asyncio
async def test_forward_request_get(monkeypatch):
    class DummyClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, headers=None, timeout=None):
            self.calls.append(("GET", url))
            return httpx.Response(200, request=httpx.Request("GET", url), json={"ok": True})

    dummy = DummyClient()
    monkeypatch.setattr(http_client, "get_http_client", lambda max_pool=100: dummy)

    resp, err = await http_client.forward_request(
        DummyConfig({"ollama_url": "http://upstream"}),
        "/api/test",
        payload=None,
    )

    assert err is None
    assert resp.status_code == 200
    assert dummy.calls == [("GET", "http://upstream/api/test")]


@pytest.mark.asyncio
async def test_forward_request_post_and_stream(monkeypatch):
    class DummyStream:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyClient:
        def __init__(self):
            self.post_calls = []
            self.stream_calls = []

        async def post(self, url, **kwargs):
            self.post_calls.append((url, kwargs))
            return httpx.Response(200, request=httpx.Request("POST", url), json={"done": True})

        def stream(self, method, url, **kwargs):
            self.stream_calls.append((method, url, kwargs))
            return DummyStream()

    dummy = DummyClient()
    monkeypatch.setattr(http_client, "get_http_client", lambda max_pool=100: dummy)

    resp, err = await http_client.forward_request(
        DummyConfig({"ollama_url": "http://upstream"}),
        "/api/generate",
        payload={"prompt": "hi"},
    )
    assert err is None
    assert resp.status_code == 200
    assert dummy.post_calls

    stream_ctx, err = await http_client.forward_request(
        DummyConfig({"ollama_url": "http://upstream"}),
        "/api/generate",
        payload={"prompt": "hi"},
        stream=True,
    )
    assert err is None
    assert dummy.stream_calls
    assert isinstance(stream_ctx, DummyStream)


@pytest.mark.asyncio
async def test_forward_request_handles_http_error(monkeypatch):
    class ErrorClient:
        async def get(self, url, headers=None, timeout=None):
            raise httpx.RequestError("boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(http_client, "get_http_client", lambda max_pool=100: ErrorClient())
    resp, err = await http_client.forward_request(
        DummyConfig({"ollama_url": "http://upstream"}),
        "/api/error",
        payload=None,
    )
    assert resp is None
    assert "boom" in err