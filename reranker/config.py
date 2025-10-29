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

    @classmethod
    def from_env(cls) -> "RerankerConfig":
        """Construct configuration from environment variables."""
        return cls(
            model_name=os.environ.get("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            max_length=int(os.environ.get("RERANKER_MAX_LENGTH", "512")),
            max_parallel=int(os.environ.get("RERANKER_MAX_PARALLEL", "4")),
            max_queue=int(os.environ["RERANKER_MAX_QUEUE"]) if os.environ.get("RERANKER_MAX_QUEUE") else None,
            queue_timeout=float(os.environ["RERANKER_QUEUE_TIMEOUT"]) if os.environ.get("RERANKER_QUEUE_TIMEOUT") else 30.0,
            device_preference=os.environ.get("RERANKER_DEVICE", "auto").lower(),
            local_model_path=os.environ.get("RERANKER_MODEL_LOCAL_PATH"),
        )
