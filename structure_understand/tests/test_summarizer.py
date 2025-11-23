from __future__ import annotations

from structure_understand.summarizer import PlaceholderSummarizer, SummaryEngine


class _FailingSummarizer(PlaceholderSummarizer):
    def summarize(self, rel_path: str, preview_text: str) -> str:
        raise RuntimeError("boom")


class _EmptySummarizer(PlaceholderSummarizer):
    def summarize(self, rel_path: str, preview_text: str) -> str:
        return ""


def test_placeholder_replaces_newlines_without_extra_trimming():
    summarizer = PlaceholderSummarizer({"max_chars": 50})
    text = "line1\nline2"
    result = summarizer.summarize("file.txt", text)
    assert "line1 line2" in result


def test_summary_engine_falls_back_on_error():
    fallback = PlaceholderSummarizer({"max_chars": 20})
    engine = SummaryEngine(_FailingSummarizer({}), fallback)
    assert engine.summarize("file.txt", "example") == fallback.summarize("file.txt", "example")


def test_summary_engine_falls_back_on_empty():
    fallback = PlaceholderSummarizer({"max_chars": 20})
    engine = SummaryEngine(_EmptySummarizer({}), fallback)
    assert engine.summarize("file.txt", "abc") == fallback.summarize("file.txt", "abc")
