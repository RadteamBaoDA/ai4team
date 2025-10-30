"""Optimized HF reranker with device management and caching."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging
import os
import hashlib

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .config import RerankerConfig

logger = logging.getLogger("reranker")


class OptimizedHFReRanker:
    """Optimized wrapper around a Hugging Face cross-encoder model."""

    def __init__(self, config: RerankerConfig):
        self.config = config
        self._tokenizer, self._model, self._model_source = self._load_model_and_tokenizer()
        self._model.eval()
        self._device = self._resolve_device()
        self._model.to(self._device)
        
        # Enable inference optimizations
        self._enable_compile = os.environ.get("ENABLE_TORCH_COMPILE", "false").lower() == "true"
        if self._enable_compile and hasattr(torch, "compile") and torch.cuda.is_available():
            try:
                self._model = torch.compile(self._model)
                logger.info("Enabled torch.compile for model optimization")
            except Exception as exc:
                logger.warning("Failed to compile model: %s", exc)

        # Model caching
        self._compiled_cache = {}

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

    def _get_model_cache_key(self, query: str, documents: List[str], top_k: Optional[int]) -> str:
        """Generate a cache key for model predictions."""
        content = f"{query}:{len(documents)}:{top_k}:{hashlib.md5(''.join(documents).encode()).hexdigest()[:8]}"
        return hashlib.md5(content.encode()).hexdigest()

    def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        if not documents:
            return []
        if top_k is None or top_k <= 0 or top_k > len(documents):
            top_k = len(documents)

        # Check cache first if enabled
        if use_cache:
            cache_key = self._get_model_cache_key(query, documents, top_k)
            if cache_key in self._compiled_cache:
                logger.debug("Using cached result for query with %d documents", len(documents))
                return self._compiled_cache[cache_key][:top_k]

        # Batch processing for efficiency
        batch_size = min(len(documents), 8)  # Process in smaller batches for memory efficiency
        all_results = []

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_results = self._process_batch(query, batch_docs, i)
            all_results.extend(batch_results)

        # Sort all results together
        ranked = sorted(all_results, key=lambda item: item["score"], reverse=True)[:top_k]

        # Cache the result if cache is enabled
        if use_cache and len(documents) <= 50:  # Only cache smaller requests
            cache_key = self._get_model_cache_key(query, documents, top_k)
            self._compiled_cache[cache_key] = ranked
            # Limit cache size
            if len(self._compiled_cache) > 100:
                oldest_key = next(iter(self._compiled_cache))
                del self._compiled_cache[oldest_key]

        return ranked

    def _process_batch(self, query: str, batch_docs: List[str], start_idx: int) -> List[Dict[str, Any]]:
        """Process a batch of documents efficiently."""
        try:
            # Efficient batching - reuse query encoding
            queries = [query] * len(batch_docs)
            
            # Single tokenization call for the entire batch
            encoded = self._tokenizer(
                queries,
                batch_docs,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="pt",
                # Add num_workers for faster tokenization on multi-core systems
                num_workers=os.environ.get("TOKENIZER_WORKERS", "0")
            )
            
            # Ensure tensors are on the right device
            encoded = {key: value.to(self._device) for key, value in encoded.items()}

            # Forward pass
            with torch.no_grad():
                logits = self._model(**encoded).logits

            # Handle multi-logit outputs
            if logits.dim() > 1 and logits.size(-1) > 1:
                logits = logits[:, 0]
            logits = logits.squeeze(-1)

            # Convert to CPU and Python floats
            scores = logits.detach().cpu().tolist()

            # Build results
            results = []
            for idx, score in enumerate(scores):
                original_idx = start_idx + idx
                results.append({
                    "index": original_idx,
                    "document": batch_docs[idx],
                    "score": float(score)
                })
            
            return results
            
        except Exception as exc:
            logger.error("Error processing batch: %s", exc)
            # Return minimal results in case of error
            return [
                {"index": start_idx + i, "document": doc, "score": 0.0}
                for i, doc in enumerate(batch_docs)
            ]
        finally:
            # Clean up CUDA cache periodically to prevent memory leaks
            if self._device.type == "cuda":
                torch.cuda.empty_cache()

    def clear_cache(self):
        """Clear the prediction cache."""
        self._compiled_cache.clear()
        logger.info("Cleared model prediction cache")
