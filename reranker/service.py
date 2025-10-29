"""Core service components for the reranker application."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import List, Optional, Tuple

from .config import RerankerConfig
from .concurrency import ConcurrencyController, QueueFullError, QueueTimeoutError
from .hf_model import HFReRanker

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger("reranker")

config = RerankerConfig.from_env()
controller = ConcurrencyController(
    max_parallel=config.max_parallel,
    max_queue=config.max_queue,
    queue_timeout=config.queue_timeout,
)
reranker = HFReRanker(config)


async def rerank_with_queue(query: str, documents: List[str], top_k: Optional[int]) -> Tuple[List[dict], float]:
    """Execute the reranker respecting concurrency limits."""
    start = time.perf_counter()
    await controller.acquire()
    try:
        ranked = await asyncio.to_thread(reranker.rerank, query, documents, top_k)
    finally:
        controller.release()
    took_ms = (time.perf_counter() - start) * 1000.0
    return ranked, took_ms


__all__ = [
    "config",
    "controller",
    "reranker",
    "rerank_with_queue",
    "QueueFullError",
    "QueueTimeoutError",
]
