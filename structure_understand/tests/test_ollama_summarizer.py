from __future__ import annotations

from collections.abc import Iterator
from types import ModuleType, SimpleNamespace

import pytest

from structure_understand import ollama_summarizer


class _DummyClient:
    def __init__(self, host: str | None = None, **kwargs: object) -> None:
        self.host = host
        self.kwargs = kwargs
        self.chat_calls: list[dict[str, object]] = []

    def chat(self, **kwargs: object) -> SimpleNamespace:
        self.chat_calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content="ollama response"))


@pytest.fixture(autouse=True)
def ensure_ollama_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    fake_ollama = ModuleType("ollama")
    fake_ollama.Client = _DummyClient  # type: ignore[attr-defined]
    import sys

    monkeypatch.setitem(sys.modules, "ollama", fake_ollama)
    yield fake_ollama


def test_ollama_summarizer_builds_options():
    config = {
        "host": "http://localhost:11434",
        "model": "llama3-70b",
        "temperature": 0.1,
        "max_tokens": 15,
        "system_message": "custom system",
    }

    summarizer = ollama_summarizer.OllamaSummarizer(config)
    result = summarizer.summarize("folder/file.py", "body text")

    assert result == "ollama response"
    client = summarizer.client
    assert client.host == config["host"]
    assert client.chat_calls
    call = client.chat_calls[-1]
    assert call["messages"][0]["content"] == config["system_message"]
    assert call["options"]["temperature"] == pytest.approx(config["temperature"])
    assert call["options"]["num_predict"] == config["max_tokens"]