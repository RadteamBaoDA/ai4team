"""Application factory for the reranker service."""

from __future__ import annotations

import logging
from fastapi import FastAPI

from .routes import router
from .service import config, controller, get_service_stats, reranker

logger = logging.getLogger("reranker")

app = FastAPI(
    title="HF Reranker", 
    description="Optimized reranker service with enhanced concurrency and caching"
)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    device = str(reranker.device)
    stats = await get_service_stats()
    return {
        "status": "ok",
        "model": config.model_name,
        "model_source": reranker.model_source,
        "device": device,
        "max_parallel": config.max_parallel,
        "queue_limit": config.max_queue,
        "waiting": stats["controller"]["waiting"],
        "active": stats["controller"]["active"],
        "available_slots": stats["controller"]["available_slots"],
        "cache_enabled": stats["model"]["cache_enabled"],
        "cache_size": stats["model"].get("cache_size", 0),
        "compatibility": ["native", "cohere", "jina"],
    }


@app.get("/metrics")
async def metrics_endpoint() -> dict:
    """Get detailed performance metrics."""
    return await get_service_stats()


@app.lifespan("startup")
async def on_startup() -> None:
    logger.info(
        "Loaded optimized reranker model %s (%s) on %s (max_parallel=%s max_queue=%s)",
        config.model_name,
        reranker.model_source,
        reranker.device,
        config.max_parallel,
        config.max_queue,
    )
