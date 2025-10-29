"""Hugging Face based reranker implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging
import os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .config import RerankerConfig

logger = logging.getLogger("reranker")


class HFReRanker:
    """Wrapper around a Hugging Face cross-encoder model."""

    def __init__(self, config: RerankerConfig):
        self.config = config
        self._tokenizer, self._model, self._model_source = self._load_model_and_tokenizer()
        self._model.eval()
        self._device = self._resolve_device()
        self._model.to(self._device)

    @property
    def device(self) -> torch.device:
        return self._device

    @property
    def model_source(self) -> str:
        return self._model_source

    def _load_model_and_tokenizer(self) -> Tuple[AutoTokenizer, AutoModelForSequenceClassification, str]:
        errors: List[str] = []
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            model = AutoModelForSequenceClassification.from_pretrained(self.config.model_name)
            logger.info("Loaded reranker model %s from Hugging Face hub", self.config.model_name)
            return tokenizer, model, f"remote:{self.config.model_name}"
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(f"remote load failed: {exc}")
            logger.warning("Failed to download model %s from Hugging Face hub: %s", self.config.model_name, exc)

        candidate_paths: List[str] = []
        if self.config.local_model_path:
            candidate_paths.append(self.config.local_model_path)
        if os.path.isdir(self.config.model_name):
            candidate_paths.append(self.config.model_name)

        for path in candidate_paths:
            try:
                tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
                model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True)
                logger.info("Loaded reranker model from local path %s", path)
                return tokenizer, model, f"local:{path}"
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"local load failed for {path}: {exc}")
                logger.warning("Failed to load local model from %s: %s", path, exc)

        error_text = "; ".join(errors)
        raise RuntimeError(f"Unable to load reranker model. Attempts: {error_text}")

    def _resolve_device(self) -> torch.device:
        preference = self.config.device_preference
        if preference == "cpu":
            return torch.device("cpu")
        if preference == "cuda" and torch.cuda.is_available():
            return torch.device("cuda")
        if preference == "mps" and torch.backends.mps.is_available():  # type: ignore[attr-defined]
            return torch.device("mps")
        if preference == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if torch.backends.mps.is_available():  # type: ignore[attr-defined]
                return torch.device("mps")
        return torch.device("cpu")

    def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        if not documents:
            return []
        if top_k is None or top_k <= 0 or top_k > len(documents):
            top_k = len(documents)

        encoded = self._tokenizer(
            [query] * len(documents),
            documents,
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}

        with torch.no_grad():
            logits = self._model(**encoded).logits

        if logits.dim() > 1 and logits.size(-1) > 1:
            logits = logits[:, 0]
        logits = logits.squeeze(-1)

        scores = logits.detach().cpu().tolist()
        ranked = sorted(
            (
                {
                    "index": idx,
                    "document": documents[idx],
                    "score": float(scores[idx]),
                }
                for idx in range(len(documents))
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        return ranked[:top_k]
