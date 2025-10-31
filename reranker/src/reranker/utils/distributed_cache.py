"""Redis-based distributed cache for multi-server deployments."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("reranker")


class RedisCache:
    """Distributed cache using Redis for multi-server coordination."""

    def __init__(self, redis_url: str, ttl_seconds: int = 300, enabled: bool = True):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self._client = None
        self._connected = False

        if self.enabled:
            self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection with optional dependency."""
        try:
            import redis.asyncio as redis_async
            
            self._client = redis_async.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            self._connected = True
            logger.info("Redis cache initialized: %s", self.redis_url)
        except ImportError:
            logger.warning("Redis not available (install: pip install redis). Distributed cache disabled.")
            self.enabled = False
            self._connected = False
        except Exception as exc:
            logger.error("Failed to connect to Redis: %s", exc)
            self.enabled = False
            self._connected = False

    def _make_cache_key(self, query: str, documents: List[str], top_k: Optional[int]) -> str:
        """Generate cache key from query and documents."""
        # Use first 50 docs for hash to keep key size reasonable
        doc_sample = documents[:50]
        doc_hash = hashlib.md5("|".join(doc_sample).encode()).hexdigest()[:12]
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"rerank:{query_hash}:{len(documents)}:{top_k}:{doc_hash}"

    async def get(self, query: str, documents: List[str], top_k: Optional[int]) -> Optional[List[Dict[str, Any]]]:
        """Get cached reranking results."""
        if not self.enabled or not self._connected or not self._client:
            return None

        try:
            key = self._make_cache_key(query, documents, top_k)
            cached = await self._client.get(key)
            
            if cached:
                logger.debug("Redis cache HIT for key: %s", key[:40])
                return json.loads(cached)
            
            logger.debug("Redis cache MISS for key: %s", key[:40])
            return None
            
        except Exception as exc:
            logger.warning("Redis get error: %s", exc)
            return None

    async def set(self, query: str, documents: List[str], top_k: Optional[int], results: List[Dict[str, Any]]):
        """Cache reranking results with TTL."""
        if not self.enabled or not self._connected or not self._client:
            return

        try:
            key = self._make_cache_key(query, documents, top_k)
            value = json.dumps(results)
            
            await self._client.setex(key, self.ttl_seconds, value)
            logger.debug("Redis cache SET for key: %s (TTL: %ds)", key[:40], self.ttl_seconds)
            
        except Exception as exc:
            logger.warning("Redis set error: %s", exc)

    async def deduplicate_request(self, query: str, documents: List[str], top_k: Optional[int], timeout: float = 10.0) -> Optional[List[Dict[str, Any]]]:
        """
        Deduplicate concurrent identical requests across servers.
        
        If another server is processing the same request, wait for its result.
        Otherwise, mark this request as in-progress.
        
        Returns cached result if available, None if this request should proceed.
        """
        if not self.enabled or not self._connected or not self._client:
            return None

        try:
            key = self._make_cache_key(query, documents, top_k)
            lock_key = f"{key}:lock"
            
            # Check if result is already cached
            cached = await self.get(query, documents, top_k)
            if cached:
                return cached
            
            # Try to acquire lock (mark as in-progress)
            acquired = await self._client.set(lock_key, "1", nx=True, ex=int(timeout))
            
            if acquired:
                # This request should process
                logger.debug("Request dedup: acquired lock for %s", key[:40])
                return None
            
            # Another server is processing, wait for result
            logger.debug("Request dedup: waiting for result from another server for %s", key[:40])
            
            # Poll for result with exponential backoff
            wait_time = 0.0
            backoff = 0.05  # Start with 50ms
            
            while wait_time < timeout:
                await asyncio.sleep(backoff)
                wait_time += backoff
                
                # Check if result is ready
                cached = await self.get(query, documents, top_k)
                if cached:
                    logger.debug("Request dedup: got result from another server after %.2fs", wait_time)
                    return cached
                
                # Exponential backoff up to 500ms
                backoff = min(backoff * 1.5, 0.5)
            
            # Timeout waiting for other server, proceed anyway
            logger.warning("Request dedup: timeout waiting for other server, proceeding")
            return None
            
        except Exception as exc:
            logger.warning("Request deduplication error: %s", exc)
            return None

    async def release_lock(self, query: str, documents: List[str], top_k: Optional[int]):
        """Release request lock after processing."""
        if not self.enabled or not self._connected or not self._client:
            return

        try:
            key = self._make_cache_key(query, documents, top_k)
            lock_key = f"{key}:lock"
            await self._client.delete(lock_key)
            logger.debug("Released lock for %s", key[:40])
        except Exception as exc:
            logger.warning("Release lock error: %s", exc)

    async def clear_all(self):
        """Clear all reranker cache entries (for maintenance)."""
        if not self.enabled or not self._connected or not self._client:
            return

        try:
            # Find all rerank keys
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self._client.scan(cursor, match="rerank:*", count=100)
                if keys:
                    await self._client.delete(*keys)
                    deleted += len(keys)
                
                if cursor == 0:
                    break
            
            logger.info("Cleared %d cache entries from Redis", deleted)
            
        except Exception as exc:
            logger.error("Clear cache error: %s", exc)

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or not self._connected or not self._client:
            return {"enabled": False, "connected": False}

        try:
            # Count rerank keys
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self._client.scan(cursor, match="rerank:*", count=100)
                count += len(keys)
                if cursor == 0:
                    break
            
            # Get Redis info
            info = await self._client.info("stats")
            
            return {
                "enabled": True,
                "connected": True,
                "cached_entries": count,
                "total_connections": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
            
        except Exception as exc:
            logger.warning("Get stats error: %s", exc)
            return {"enabled": True, "connected": False, "error": str(exc)}

    async def close(self):
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.close()
                logger.info("Redis connection closed")
            except Exception as exc:
                logger.warning("Error closing Redis: %s", exc)


# Singleton instance
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> Optional[RedisCache]:
    """Get or create Redis cache instance."""
    global _redis_cache
    
    if _redis_cache is None:
        redis_enabled = os.environ.get("REDIS_ENABLED", "false").lower() == "true"
        
        if not redis_enabled:
            logger.info("Redis distributed cache is disabled")
            return None
        
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_ttl = int(os.environ.get("REDIS_TTL_SECONDS", "600"))  # 10 min default
        
        _redis_cache = RedisCache(redis_url, redis_ttl, enabled=True)
        
        if not _redis_cache.enabled:
            _redis_cache = None
    
    return _redis_cache


async def initialize_redis_cache():
    """Initialize Redis cache on startup."""
    cache = get_redis_cache()
    if cache and cache.enabled:
        logger.info("Redis distributed cache ready")
    return cache
