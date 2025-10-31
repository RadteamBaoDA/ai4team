"""Multi-backend reranker supporting PyTorch (CUDA/MPS/CPU) and MLX for Apple Silicon."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging
import os
import hashlib
import platform
from contextlib import nullcontext

from .config import RerankerConfig

logger = logging.getLogger("reranker")


class UnifiedReRanker:
    """Unified reranker supporting multiple backends: PyTorch, MLX."""

    def __init__(self, config: RerankerConfig):
        self.config = config
        self._backend = None
        self._tokenizer = None
        self._model = None
        self._model_source = None
        self._device = None
        
        # Initialize appropriate backend
        if config.use_mlx:
            self._init_mlx_backend()
        else:
            self._init_pytorch_backend()
        
        # Caching
        self._prediction_cache = {}
        self._cache_enabled = os.environ.get("ENABLE_PREDICTION_CACHE", "true").lower() == "true"

    def _init_mlx_backend(self):
        """Initialize MLX backend for Apple Silicon."""
        import importlib.util as ilu
        from transformers import AutoTokenizer

        # Detect MLX availability dynamically to avoid static import errors
        has_mlx_core = ilu.find_spec("mlx.core") is not None
        has_mlx_nn = ilu.find_spec("mlx.nn") is not None

        if not (has_mlx_core and has_mlx_nn):
            logger.warning("MLX not available, falling back to PyTorch")
            return self._init_pytorch_backend()

        try:
            logger.info("Initializing MLX backend for Apple Silicon")
            self._backend = "mlx"

            # Lazy import via importlib to keep static analyzers happy
            import importlib
            mx = importlib.import_module("mlx.core")  # noqa: F401
            nn = importlib.import_module("mlx.nn")    # noqa: F401

            # Load tokenizer
            self._tokenizer = self._load_tokenizer()

            # MLX native models are not yet fully supported in transformers for sequence classification.
            # We keep the PyTorch model but mark backend as MLX for future extension.
            from transformers import AutoModelForSequenceClassification
            model = AutoModelForSequenceClassification.from_pretrained(self.config.model_name)
            self._model = model
            self._model_source = f"mlx:{self.config.model_name}"
            self._device = "mlx"
            logger.info("MLX backend initialized (using PyTorch model until native support)")
        except Exception as exc:
            logger.warning("MLX initialization failed, falling back to PyTorch: %s", exc)
            self._init_pytorch_backend()

    def _init_pytorch_backend(self):
        """Initialize PyTorch backend with CUDA/MPS/CPU support."""
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        logger.info("Initializing PyTorch backend")
        self._backend = "pytorch"
        
        # Load tokenizer and model
        self._tokenizer, self._model, self._model_source = self._load_model_and_tokenizer()
        self._model.eval()
        
        # Resolve device
        self._device = self._resolve_pytorch_device()
        self._model.to(self._device)
        
        # Enable PyTorch optimizations
        self._enable_pytorch_optimizations()
        
        logger.info("PyTorch backend initialized on device: %s", self._device)

    def _load_tokenizer(self):
        """Load tokenizer from HuggingFace or local path."""
        from transformers import AutoTokenizer
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            return tokenizer
        except Exception:
            if self.config.local_model_path:
                return AutoTokenizer.from_pretrained(
                    self.config.local_model_path, 
                    local_files_only=True
                )
            raise

    def _load_model_and_tokenizer(self) -> Tuple:
        """Load model and tokenizer for PyTorch backend."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
        
        errors: List[str] = []
        
        # Determine quantization
        quantization = os.environ.get("QUANTIZATION", "none").lower()
        load_in_8bit = quantization == "int8"
        use_bfloat16 = quantization == "bf16"
        
        # Quantization kwargs
        kwargs = {}
        if load_in_8bit:
            # Requires bitsandbytes for 8-bit quantization
            try:
                import bitsandbytes  # noqa: F401
                kwargs["load_in_8bit"] = True
                kwargs["device_map"] = "auto"
                logger.info("Loading model with 8-bit quantization")
            except ImportError:
                logger.warning("8-bit quantization requested but bitsandbytes not installed. Loading normally.")
                load_in_8bit = False
        
        if use_bfloat16 and torch.cuda.is_available():
            kwargs["torch_dtype"] = torch.bfloat16
            logger.info("Loading model with BF16 precision")
        
        # Try remote load
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            model = AutoModelForSequenceClassification.from_pretrained(self.config.model_name, **kwargs)
            logger.info("Loaded model %s from HuggingFace", self.config.model_name)
            return tokenizer, model, f"remote:{self.config.model_name}"
        except Exception as exc:
            errors.append(f"remote: {exc}")
            logger.warning("Remote load failed: %s", exc)

        # Try local paths
        candidate_paths = []
        if self.config.local_model_path:
            candidate_paths.append(self.config.local_model_path)
        if os.path.isdir(self.config.model_name):
            candidate_paths.append(self.config.model_name)

        for path in candidate_paths:
            try:
                tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
                model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True, **kwargs)
                logger.info("Loaded model from local path: %s", path)
                return tokenizer, model, f"local:{path}"
            except Exception as exc:
                errors.append(f"{path}: {exc}")

        raise RuntimeError(f"Failed to load model. Attempts: {'; '.join(errors)}")

    def _resolve_pytorch_device(self):
        """Resolve the best available PyTorch device."""
        import torch
        
        pref = self.config.device_preference
        
        if pref == "cpu":
            return torch.device("cpu")
        
        if pref == "cuda" and torch.cuda.is_available():
            return torch.device("cuda")
        
        # MPS support for Mac M-series
        if pref in ("mps", "auto"):
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info("Using MPS (Metal Performance Shaders) for Apple Silicon")
                return torch.device("mps")
        
        # Auto-detect best device
        if pref == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
        
        return torch.device("cpu")

    def _enable_pytorch_optimizations(self):
        """Enable PyTorch-specific optimizations."""
        import torch
        
        enable_compile = os.environ.get("ENABLE_TORCH_COMPILE", "false").lower() == "true"
        # Optional mixed precision for CUDA
        self._use_mixed_precision = os.environ.get("ENABLE_MIXED_PRECISION", "false").lower() == "true"
        
        if enable_compile and hasattr(torch, "compile"):
            # Only compile on CUDA for now (MPS compilation is experimental)
            if self._device.type == "cuda":
                try:
                    self._model = torch.compile(self._model, mode="reduce-overhead")
                    logger.info("Enabled torch.compile optimization")
                except Exception as exc:
                    logger.warning("torch.compile failed: %s", exc)

        # Improve matmul precision for better performance on some backends
        try:
            torch.set_float32_matmul_precision("high")  # PyTorch 2.0+
        except Exception:
            pass

    @property
    def device(self):
        return self._device

    @property
    def model_source(self) -> str:
        return self._model_source or "unknown"

    @property
    def backend(self) -> str:
        return self._backend or "unknown"

    def _get_cache_key(self, query: str, documents: List[str], top_k: Optional[int]) -> str:
        """Generate cache key for predictions."""
        doc_hash = hashlib.md5('|'.join(documents[:50]).encode()).hexdigest()[:12]
        return f"{hashlib.md5(query.encode()).hexdigest()[:8]}:{len(documents)}:{top_k}:{doc_hash}"

    def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Rerank documents using the configured backend."""
        if not documents:
            return []
        
        if top_k is None or top_k <= 0 or top_k > len(documents):
            top_k = len(documents)

        # Check cache
        if use_cache and self._cache_enabled:
            cache_key = self._get_cache_key(query, documents, top_k)
            if cache_key in self._prediction_cache:
                logger.debug("Cache hit for query with %d documents", len(documents))
                return self._prediction_cache[cache_key][:top_k]

        # Process based on backend
        if self._backend == "mlx":
            results = self._rerank_mlx(query, documents, top_k)
        else:
            results = self._rerank_pytorch(query, documents, top_k)

        # Update cache
        if use_cache and self._cache_enabled and len(documents) <= 100:
            cache_key = self._get_cache_key(query, documents, top_k)
            self._prediction_cache[cache_key] = results
            
            # Limit cache size
            if len(self._prediction_cache) > 200:
                oldest = next(iter(self._prediction_cache))
                del self._prediction_cache[oldest]

        return results

    def _rerank_mlx(self, query: str, documents: List[str], top_k: int) -> List[Dict[str, Any]]:
        """Rerank using MLX backend."""
        # For now, fall back to CPU-based inference
        # Full MLX integration would require MLX-native model conversion
        logger.warning("Pure MLX inference not yet implemented, using PyTorch fallback")
        
        # Temporarily use PyTorch on CPU for MLX systems
        import torch
        temp_device = torch.device("cpu")
        
        return self._rerank_pytorch_internal(query, documents, top_k, temp_device)

    def _rerank_pytorch(self, query: str, documents: List[str], top_k: int) -> List[Dict[str, Any]]:
        """Rerank using PyTorch backend."""
        return self._rerank_pytorch_internal(query, documents, top_k, self._device)

    def _rerank_pytorch_internal(
        self, 
        query: str, 
        documents: List[str], 
        top_k: int,
        device
    ) -> List[Dict[str, Any]]:
        """Internal PyTorch reranking logic with batching."""
        import torch
        
        # Process in batches for memory efficiency
        batch_size = min(self.config.batch_size, len(documents))
        all_results = []

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_results = self._process_pytorch_batch(query, batch_docs, i, device)
            all_results.extend(batch_results)

        # Sort and return top-k
        ranked = sorted(all_results, key=lambda x: x["score"], reverse=True)[:top_k]
        return ranked

    def _process_pytorch_batch(
        self, 
        query: str, 
        batch_docs: List[str], 
        start_idx: int,
        device
    ) -> List[Dict[str, Any]]:
        """Process a batch of documents with PyTorch."""
        import torch
        
        try:
            # Tokenize batch
            encoded = self._tokenizer(
                [query] * len(batch_docs),
                batch_docs,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="pt",
            )
            
            # Move to device
            non_blocking = (hasattr(device, "type") and device.type == "cuda")
            encoded = {k: v.to(device, non_blocking=non_blocking) for k, v in encoded.items()}

            # Inference
            autocast_ctx = (
                torch.autocast(device_type=device.type, dtype=torch.float16)
                if hasattr(device, "type") and device.type == "cuda" and getattr(self, "_use_mixed_precision", False)
                else nullcontext()
            )
            with torch.inference_mode():
                with autocast_ctx:
                    logits = self._model(**encoded).logits

            # Handle multi-class outputs
            if logits.dim() > 1 and logits.size(-1) > 1:
                logits = logits[:, 0]
            logits = logits.squeeze(-1)

            # Convert to scores
            scores = logits.detach().cpu().tolist()

            # Build results
            results = []
            for idx, score in enumerate(scores):
                results.append({
                    "index": start_idx + idx,
                    "document": batch_docs[idx],
                    "score": float(score)
                })
            
            return results
            
        except Exception as exc:
            logger.error("Batch processing error: %s", exc)
            return [
                {"index": start_idx + i, "document": doc, "score": 0.0}
                for i, doc in enumerate(batch_docs)
            ]
        finally:
            # Cleanup GPU memory
            if hasattr(device, "type") and device.type == "cuda":
                torch.cuda.empty_cache()
            elif hasattr(device, "type") and device.type == "mps":
                # MPS cleanup (if needed in future PyTorch versions)
                pass

    def warmup(self):
        """Run a tiny forward pass to warm up kernels and caches."""
        try:
            dummy_query = "warmup"
            dummy_docs = ["doc one", "doc two", "doc three"]
            _ = self.rerank(dummy_query, dummy_docs, top_k=1, use_cache=False)
            logger.info("Model warmup completed for backend=%s", self.backend)
        except Exception as exc:
            logger.warning("Warmup failed: %s", exc)

    def clear_cache(self):
        """Clear prediction cache."""
        self._prediction_cache.clear()
        logger.info("Cleared prediction cache")
