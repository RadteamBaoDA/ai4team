from __future__ import annotations

from typing import Any

from .summarizer import BaseSummarizer


class OllamaSummarizer(BaseSummarizer):
    def __init__(self, config: dict[str, Any]) -> None:
        try:
            from ollama import Client
        except ImportError as exc:  # pragma: no cover - optional integration
            raise RuntimeError("ollama package is missing; install it to use the Ollama summarizer") from exc

        host = config.get("url") or config.get("host") or "http://localhost:11434"
        self.client = Client(host=host)
        self.model = config.get("model", "llama3-70b")
        self.temperature = float(config.get("temperature", 0.2))
        self.system_message = config.get("system_message", "Summarize code files for humans.")

    def summarize(self, rel_path: str, preview_text: str) -> str:
        prompt = (
            f"Could you please provide a summary of the {rel_path}, including all key points and supporting details? The summary should be comprehensive and accurately reflect the main message and arguments presented in the original text, while also being concise and easy to understand. To ensure accuracy, please read the text carefully and pay attention to any nuances or complexities in the language. Additionally, the summary should avoid any personal biases or interpretations and remain objective and factual throughout."
            f" Include any obvious side effects or expected inputs.\n\n{preview_text}"
        )
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": prompt},
            ],
            options=self._build_options(),
        )
        try:
            return (response.message.content or "").strip()
        except AttributeError as exc:
            raise RuntimeError("unexpected response from Ollama") from exc

    def _build_options(self) -> dict[str, Any]:
        return {"temperature": self.temperature}
