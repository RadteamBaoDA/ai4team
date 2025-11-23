from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace, ModuleType

import pytest

from structure_understand import openai_summarizer


class _DummyCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="generated summary"))])


class _DummyChat:
    def __init__(self) -> None:
        self.completions = _DummyCompletions()


class _CapturedOpenAI:
    def __init__(self, api_key: str | None = None, **kwargs: object) -> None:
        self.api_key = api_key
        self.kwargs = kwargs
        self.chat = _DummyChat()


@pytest.fixture(autouse=True)
def ensure_openai_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    fake_openai = ModuleType("openai")
    clients: list[_CapturedOpenAI] = []

    def _factory(api_key: str | None = None, **kwargs: object) -> _CapturedOpenAI:
        client = _CapturedOpenAI(api_key, **kwargs)
        clients.append(client)
        return client

    fake_openai.OpenAI = _factory  # type: ignore[attr-defined]
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    yield fake_openai


def test_openai_summarizer_honors_config(monkeypatch):
    config = {
        "api_key": "test-key",
        "model": "gpt-test",
        "temperature": 0.3,
        "max_tokens": 42,
        "system_message": "test system",
        "base_url": "https://api.openai.com",
    }
    summarizer = openai_summarizer.OpenAISummarizer(config)

    result = summarizer.summarize("file.txt", "text")
    assert result == "generated summary"

    completions = summarizer.client.chat.completions
    assert completions.calls
    call = completions.calls[-1]
    assert call["model"] == "gpt-test"
    assert "system" not in call
    assert call["temperature"] == 0.3
    assert call["max_tokens"] == 42
    assert call["messages"][0]["content"] == config["system_message"]

    assert summarizer.client.api_key == config["api_key"]
    assert summarizer.client.kwargs.get("base_url") == config["base_url"]


def test_openai_summarizer_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        openai_summarizer.OpenAISummarizer({})
