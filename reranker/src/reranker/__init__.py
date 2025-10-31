"""Reranker service package - A production-ready reranking service with optimized concurrency."""

from .api.app import app
from .core.config import RerankerConfig

__version__ = "2.0.0"
__author__ = "AI4Team"
__description__ = "Production-ready reranking service with optimized concurrency and performance"

__all__ = [
    "app",
    "RerankerConfig",
]