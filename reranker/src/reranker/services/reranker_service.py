"""Core service components for the reranker application."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import List, Optional, Tuple

from ..core.config import RerankerConfig
from ..core.concurrency import ConcurrencyMetrics, OptimizedConcurrencyController, QueueFullError, QueueTimeoutError
from ..core.unified_reranker import UnifiedReRanker
from ..utils.distributed_cache import get_redis_cache
from ..utils.micro_batcher import create_micro_batcher

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger("reranker")

# Configuration
config = RerankerConfig.from_env()
controller = OptimizedConcurrencyController(
    max_parallel=config.max_parallel,
    max_queue=config.max_queue,
    queue_timeout=config.queue_timeout,
)
reranker = UnifiedReRanker(config)
metrics = ConcurrencyMetrics()

# Enhanced service configuration
ENABLE_CACHE = os.environ.get("ENABLE_PREDICTION_CACHE", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))  # 5 minutes default
CLEAR_CACHE_INTERVAL = int(os.environ.get("CLEAR_CACHE_INTERVAL", "3600"))  # 1 hour

# Distributed cache (optional)
redis_cache = get_redis_cache()

# Micro-batcher for GPU efficiency (optional)
def _rerank_fn(query: str, documents: List[str], top_k: Optional[int]):
    """Reranking function for micro-batcher."""
    return reranker.rerank(query, documents, top_k, use_cache=ENABLE_CACHE)

micro_batcher = create_micro_batcher(_rerank_fn) if config.micro_batch_enabled else None


async def rerank_with_queue(query: str, documents: List[str], top_k: Optional[int]) -> Tuple[List[dict], float]:
    """Execute the reranker respecting concurrency limits with metrics tracking."""
    wait_start = time.perf_counter()
    
    # Check Redis distributed cache first
    if redis_cache:
        try:
            # Try request deduplication
            cached = await redis_cache.deduplicate_request(query, documents, top_k, timeout=5.0)
            if cached:
                logger.debug("Redis deduplication: using result from another server")
                total_time = (time.perf_counter() - wait_start) * 1000.0
                await metrics.record_request(0.0, total_time / 1000.0, True)
                return cached, total_time
        except Exception as exc:
            logger.warning("Redis deduplication error: %s", exc)
    
    try:
        await controller.acquire()
    except QueueFullError:
        await metrics.record_request(time.perf_counter() - wait_start, 0.0, False)
        raise
    
    process_start = time.perf_counter()
    try:
        # Use micro-batcher if enabled, otherwise direct call
        if micro_batcher:
            ranked = await micro_batcher.submit(query, documents, top_k)
        else:
            ranked = await asyncio.to_thread(
                reranker.rerank, 
                query, 
                documents, 
                top_k,
                use_cache=ENABLE_CACHE
            )
        
        # Store in Redis cache
        if redis_cache and ranked:
            try:
                await redis_cache.set(query, documents, top_k, ranked)
            except Exception as exc:
                logger.warning("Redis cache set error: %s", exc)
        
        success = True
    except Exception as exc:
        logger.error("Error during reranking: %s", exc)
        ranked = []
        success = False
    finally:
        controller.release()
        
        # Release Redis lock if we acquired it
        if redis_cache:
            try:
                await redis_cache.release_lock(query, documents, top_k)
            except Exception:
                pass
    
    process_time = time.perf_counter() - process_start
    wait_time = time.perf_counter() - wait_start
    await metrics.record_request(wait_time, process_time, success)
    
    total_time = (time.perf_counter() - wait_start) * 1000.0
    return ranked, total_time


async def clear_cache_periodically():
    """Periodically clear cache to prevent memory leaks."""
    while True:
        await asyncio.sleep(CLEAR_CACHE_INTERVAL)
        if ENABLE_CACHE:
            reranker.clear_cache()
            logger.info("Periodic cache clear completed")


# Background tasks will be started during app startup
_background_tasks_started = False

async def start_background_tasks():
    """Start background tasks - called during app startup."""
    global _background_tasks_started
    if _background_tasks_started:
        return
        
    if ENABLE_CACHE:
        asyncio.create_task(clear_cache_periodically())
    
    # Optional model warmup to reduce first-request latency
    if os.environ.get("WARMUP_ON_START", "true").lower() == "true":
        try:
            # Run warmup in a thread to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, reranker.warmup)
        except Exception as exc:
            logger.warning("Warmup failed: %s", exc)
    
    _background_tasks_started = True


async def get_service_stats():
    """Get comprehensive service statistics."""
    stats = {
        'controller': {
            'waiting': controller.waiting,
            'active': controller.active,
            'available_slots': controller.available_slots,
            'max_parallel': config.max_parallel,
            'max_queue': config.max_queue,
        },
        'model': {
            'backend': reranker.backend,
            'source': reranker.model_source,
            'device': str(reranker.device),
            'cache_enabled': ENABLE_CACHE,
            'batch_size': getattr(config, 'batch_size', None),
            'quantization': config.quantization,
        },
        'metrics': metrics.get_stats(),
    }
    
    # Add local cache stats if available
    if hasattr(reranker, '_prediction_cache'):
        stats['model']['local_cache_size'] = len(reranker._prediction_cache)
    
    # Add Redis cache stats
    if redis_cache:
        try:
            redis_stats = await redis_cache.get_stats()
            stats['distributed_cache'] = redis_stats
        except Exception as exc:
            stats['distributed_cache'] = {'error': str(exc)}
    else:
        stats['distributed_cache'] = {'enabled': False}
    
    # Add micro-batcher stats
    if micro_batcher:
        stats['micro_batcher'] = micro_batcher.get_stats()
    else:
        stats['micro_batcher'] = {'enabled': False}
    
    return stats


__all__ = [
    "config",
    "controller",
    "reranker",
    "rerank_with_queue",
    "get_service_stats",
    "start_background_tasks",
    "QueueFullError",
    "QueueTimeoutError",
]