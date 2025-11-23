from __future__ import annotations

import os
from typing import Any

from .summarizer import BaseSummarizer


class OpenAISummarizer(BaseSummarizer):
    def __init__(self, config: dict[str, Any]) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional integration
            raise RuntimeError("openai package is missing; install it to use the OpenAI summarizer") from exc

        api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        api_key = config.get("api_key") or os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"Environment variable {api_key_env} is required for OpenAI summarizer")

        client_kwargs: dict[str, Any] = {}
        if base_url := config.get("base_url"):
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(api_key=api_key, **client_kwargs)
        self.model = config.get("model", "gpt-4o-mini")
        self.temperature = float(config.get("temperature", 0.2))
        self.system_message = config.get(
            "system_message", "Summarize code files for humans."
        )

    def summarize(self, rel_path: str, preview_text: str) -> str:
        prompt = (
            f"Summarize the intent and structure of {rel_path}."
            f" Include any obvious side effects or expected inputs.\n\n{preview_text}"
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
        )
        try:
            return response.choices[0].message.content.strip()
        except (IndexError, AttributeError) as exc:
            raise RuntimeError("unexpected response from OpenAI") from exc
