import json

import httpx
import pytest

from ollama_guardrails.api import streaming_handlers


class DummyGuardManager:
    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self.calls = []

    async def scan_output(self, text, *args, **kwargs):
        self.calls.append(text)
        if self._responses:
            return self._responses.pop(0)
        return {"allowed": True, "scanners": {}}


def _make_response(lines):
    """Create an httpx.Response whose aiter_lines yields the provided lines."""
    payload = ("\n".join(lines) + "\n").encode()
    request = httpx.Request("POST", "http://test/api")
    return httpx.Response(200, request=request, content=payload)


def test_build_guard_block_chunk_formats_markdown():
    guard_payload = {
        "message": "Blocked by policy",
        "failed_scanners": [
            {"scanner": "Toxicity", "reason": "unsafe"}
        ],
    }

    chunk = streaming_handlers._build_guard_block_chunk(
        model_name="llama3",
        message_content="Please stop",
        detected_lang="en",
        guard_payload=guard_payload,
    )

    assert chunk["done_reason"] == "guard_blocked"
    assert chunk["error"]["failed_scanners"][0]["scanner"] == "Toxicity"
    message_body = chunk["message"]["content"]
    assert message_body.startswith("\n\n\n")
    assert message_body.endswith("\n")


@pytest.mark.asyncio
async def test_stream_response_with_guard_passthrough(monkeypatch):
    monkeypatch.delenv("INLINE_GUARD_ERRORS", raising=False)
    response = _make_response([
        json.dumps({"response": "safe chunk"}),
        json.dumps({"message": {"content": "more"}}),
    ])
    guard_manager = DummyGuardManager()
    config = {"enable_output_guard": False}

    chunks = []
    async for chunk in streaming_handlers.stream_response_with_guard(
        response,
        guard_manager,
        config,
        detected_lang="en",
    ):
        chunks.append(chunk)

    assert chunks == [json.dumps({"response": "safe chunk"}) + "\n", json.dumps({"message": {"content": "more"}}) + "\n"]
    assert guard_manager.calls == []
    assert response.is_closed


@pytest.mark.asyncio
async def test_stream_response_with_guard_blocks_output(monkeypatch):
    monkeypatch.delenv("INLINE_GUARD_ERRORS", raising=False)
    monkeypatch.setattr(streaming_handlers, "min_output_length", 5)

    guard_manager = DummyGuardManager([
        {
            "allowed": False,
            "scanners": {
                "Toxicity": {
                    "passed": False,
                    "reason": "bad",
                    "score": 0.9,
                }
            },
        }
    ])
    config = {"enable_output_guard": True, "inline_guard_errors": True}
    response = _make_response([json.dumps({"response": "x" * 10})])

    chunks = []
    async for chunk in streaming_handlers.stream_response_with_guard(
        response,
        guard_manager,
        config,
        detected_lang="en",
    ):
        chunks.append(chunk)

    assert len(chunks) == 1
    payload = json.loads(chunks[0])
    assert payload["done_reason"] == "guard_blocked"
    assert payload["guard"]["failed_scanners"][0]["scanner"] == "Toxicity"
    assert "Response blocked" in payload["message"]["content"]
    assert guard_manager.calls != []
    assert response.is_closed
