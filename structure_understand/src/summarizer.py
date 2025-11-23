from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseSummarizer:
    def summarize(self, rel_path: str, preview_text: str) -> str:
        raise NotImplementedError


class PlaceholderSummarizer(BaseSummarizer):
    def __init__(self, config: dict[str, Any]) -> None:
        self.max_chars = int(config.get("max_chars", 250))

    def summarize(self, rel_path: str, preview_text: str) -> str:
        trimmed = " ".join(preview_text.splitlines())
        if not trimmed:
            return "(empty or binary file)"
        if len(trimmed) <= self.max_chars:
            return trimmed
        return trimmed[: self.max_chars].rstrip() + " ..."


class SummaryEngine:
    def __init__(self, primary: Optional[BaseSummarizer], fallback: BaseSummarizer) -> None:
        self.primary = primary
        self.fallback = fallback

    def summarize(self, rel_path: str, preview_text: str) -> str:
        provider_name = type(self.primary).__name__ if self.primary else "placeholder"
        logger.info("Invoking %s summarizer for %s", provider_name, rel_path)
        if self.primary:
            try:
                text = self.primary.summarize(rel_path, preview_text)
                if text:
                    return text
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("LLM summarization failed for %s: %s", rel_path, exc)
        logger.info("Falling back to placeholder summarizer for %s", rel_path)
        return self.fallback.summarize(rel_path, preview_text)


def build_summary_engine(config: dict[str, Any]) -> SummaryEngine:
    placeholder = PlaceholderSummarizer(config.get("placeholder", {}))
    provider = (config.get("provider") or "placeholder").lower()
    primary: Optional[BaseSummarizer] = None
    if provider == "openai":
        try:
            from .openai_summarizer import OpenAISummarizer
        except ImportError as exc:  # pragma: no cover - optional integration
            logger.warning("OpenAI summarizer unsupported: %s", exc)
        else:
            try:
                primary = OpenAISummarizer(config.get("openai", {}))
            except Exception as exc:  # pragma: no cover - optional integration
                logger.warning("OpenAI summarizer unavailable: %s", exc)
    elif provider == "ollama":
        try:
            from .ollama_summarizer import OllamaSummarizer  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional integration
            logger.warning("Ollama summarizer unsupported: %s", exc)
        else:
            try:
                primary = OllamaSummarizer(config.get("ollama", {}))
            except Exception as exc:  # pragma: no cover - optional integration
                logger.warning("Ollama summarizer unavailable: %s", exc)
    return SummaryEngine(primary, placeholder)
