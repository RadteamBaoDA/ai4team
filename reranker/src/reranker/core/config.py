"""Configuration management for the reranker service."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class RerankerConfig:
    """Holds runtime configuration for the reranker service."""

    model_name: str
    max_length: int
    max_parallel: int
    max_queue: Optional[int]
    queue_timeout: Optional[float]
    device_preference: str
    local_model_path: Optional[str]
    use_mlx: bool
    batch_size: int
    enable_distributed: bool
    worker_timeout: float
    max_retries: int
    quantization: str
    redis_enabled: bool
    redis_url: str
    micro_batch_enabled: bool

    @classmethod
    def from_env(cls) -> "RerankerConfig":
        """Construct configuration from environment variables."""
        # Auto-detect M-series Mac for MPS/MLX
        device_pref = os.environ.get("RERANKER_DEVICE", "auto").lower()
        use_mlx = os.environ.get("RERANKER_USE_MLX", "false").lower() == "true"
        
        # Auto-enable MLX on M-series Mac if available
        if device_pref == "auto" and not use_mlx:
            import platform
            if platform.system() == "Darwin" and "arm" in platform.machine().lower():
                try:
                    import mlx.core as mx
                    use_mlx = True
                    device_pref = "mlx"
                except ImportError:
                    pass
        
        return cls(
            model_name=os.environ.get("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            max_length=int(os.environ.get("RERANKER_MAX_LENGTH", "512")),
            max_parallel=int(os.environ.get("RERANKER_MAX_PARALLEL", "4")),
            max_queue=int(os.environ["RERANKER_MAX_QUEUE"]) if os.environ.get("RERANKER_MAX_QUEUE") else None,
            queue_timeout=float(os.environ["RERANKER_QUEUE_TIMEOUT"]) if os.environ.get("RERANKER_QUEUE_TIMEOUT") else None,
            device_preference=device_pref,
            local_model_path=os.environ.get("RERANKER_LOCAL_MODEL_PATH"),
            use_mlx=use_mlx,
            batch_size=int(os.environ.get("RERANKER_BATCH_SIZE", "16")),
            enable_distributed=os.environ.get("RERANKER_ENABLE_DISTRIBUTED", "false").lower() == "true",
            worker_timeout=float(os.environ.get("RERANKER_WORKER_TIMEOUT", "30")),
            max_retries=int(os.environ.get("RERANKER_MAX_RETRIES", "3")),
            quantization=os.environ.get("RERANKER_QUANTIZATION", "none"),
            redis_enabled=os.environ.get("REDIS_ENABLED", "false").lower() == "true",
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            micro_batch_enabled=os.environ.get("MICRO_BATCH_ENABLED", "false").lower() == "true",
        )