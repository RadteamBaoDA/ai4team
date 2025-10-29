"""Application factory for the reranker service."""

from __future__ import annotations

import logging
from fastapi import FastAPI

from .routes import router
from .service import config, controller, reranker

logger = logging.getLogger("reranker")

app = FastAPI(title="HF Reranker", description="Reranker service with guarded concurrency")
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    device = str(reranker.device)
    return {
        "status": "ok",
        "model": config.model_name,
        "model_source": reranker.model_source,
        "device": device,
        "max_parallel": config.max_parallel,
        "queue_limit": config.max_queue,
        "waiting": controller.waiting,
        "compatibility": ["native", "cohere", "jina"],
    }


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "Loaded reranker model %s (%s) on %s (max_parallel=%s max_queue=%s)",
        config.model_name,
        reranker.model_source,
        reranker.device,
        config.max_parallel,
        config.max_queue,
    )
