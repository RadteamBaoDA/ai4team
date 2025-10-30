"""
Caching layer for LLM Guard scan results with Redis support
Reduces redundant ML model inference for frequently seen content

Supports:
- Redis backend (recommended for production)
- In-memory LRU cache (fallback for development)
- Automatic failover from Redis to in-memory
"""

import hashlib
import logging
import time
import json
import os
from typing import Dict, Any, Optional, Tuple, Union
from collections import OrderedDict
import asyncio

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis.asyncio as redis
    from redis.asyncio.connection import ConnectionPool
    HAS_REDIS = True
    logger.info('Async Redis library available')
except ImportError:
    HAS_REDIS = False
    redis = None
    logger.warning('Async Redis library not available, using in-memory cache only')


class LRUCache:
    """Async-compatible LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to cache
            ttl_seconds: Time-to-live for cached items in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
        
        logger.info(f'LRU Cache initialized: max_size={max_size}, ttl={ttl_seconds}s')
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if cached item has expired."""
        return (time.time() - timestamp) > self.ttl_seconds
    
    def _make_key(self, text: str, scan_type: str = 'input') -> str:
        """Generate cache key from text and scan type."""
        # Use SHA256 for security and collision resistance
        content = f"{scan_type}:{text}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    async def get(self, text: str, scan_type: str = 'input') -> Optional[Dict[str, Any]]:
        """
        Get cached scan result.
        
        Args:
            text: Text to look up
            scan_type: Type of scan ('input' or 'output')
        
        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(text, scan_type)
        
        async with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            value, timestamp = self.cache[key]
            
            # Check if expired
            if self._is_expired(timestamp):
                del self.cache[key]
                self.misses += 1
                logger.debug(f'Cache expired for key: {key[:16]}...')
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            
            logger.debug(f'Cache hit for key: {key[:16]}...')
            return value
    
    async def set(self, text: str, result: Dict[str, Any], scan_type: str = 'input') -> None:
        """
        Store scan result in cache.
        
        Args:
            text: Text being cached
            result: Scan result to cache
            scan_type: Type of scan ('input' or 'output')
        """
        key = self._make_key(text, scan_type)
        timestamp = time.time()
        
        async with self.lock:
            # Remove oldest item if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f'Cache full, evicted: {oldest_key[:16]}...')
            
            self.cache[key] = (result, timestamp)
            self.cache.move_to_end(key)
            
            logger.debug(f'Cached result for key: {key[:16]}...')
    
    async def clear(self) -> None:
        """Clear all cached items."""
        async with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info('Cache cleared')
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'ttl_seconds': self.ttl_seconds,
            }
    
    async def cleanup_expired(self) -> int:
        """Remove all expired items from cache."""
        removed_count = 0
        current_time = time.time()
        
        async with self.lock:
            # Create list of expired keys
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if (current_time - timestamp) > self.ttl_seconds
            ]
            
            # Remove expired items
            for key in expired_keys:
                del self.cache[key]
                removed_count += 1
            
            if removed_count > 0:
                logger.info(f'Cleaned up {removed_count} expired cache entries')
        
        return removed_count


class RedisCache:
    """Async Redis-based cache with automatic failover to in-memory cache."""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        ttl_seconds: int = 3600,
        key_prefix: str = 'llmguard:',
        fallback_enabled: bool = True,
        fallback_max_size: int = 1000
    ):
        """
        Initialize Redis cache with fallback.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            ttl_seconds: Default TTL for cached items
            key_prefix: Prefix for all cache keys
            fallback_enabled: Enable fallback to in-memory cache
            fallback_max_size: Max size for fallback cache
        """
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.redis_client: Optional[redis.Redis] = None
        self.fallback_cache: Optional[LRUCache] = None
        self.using_fallback = False
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.lock = asyncio.Lock()
        
        # Store connection params for async initialization
        self._conn_params = {
            'host': host, 'port': port, 'db': db, 'password': password,
            'max_connections': max_connections, 'socket_timeout': socket_timeout
        }
        self._fallback_enabled = fallback_enabled
        self._fallback_max_size = fallback_max_size
        self._ttl_seconds = ttl_seconds

    async def initialize(self):
        """Asynchronously initialize the Redis connection."""
        if HAS_REDIS:
            try:
                pool = ConnectionPool(
                    decode_responses=True, **self._conn_params
                )
                self.redis_client = redis.Redis(connection_pool=pool)
                await self.redis_client.ping()
                logger.info(f'Async Redis cache initialized: {self._conn_params["host"]}:{self._conn_params["port"]}')
            except Exception as e:
                logger.error(f'Failed to connect to async Redis: {e}')
                self.redis_client = None
                if self._fallback_enabled:
                    logger.warning('Falling back to in-memory cache')
                    self.fallback_cache = LRUCache(max_size=self._fallback_max_size, ttl_seconds=self._ttl_seconds)
                    self.using_fallback = True
        else:
            if self._fallback_enabled:
                logger.info('Using in-memory cache')
                self.fallback_cache = LRUCache(max_size=self._fallback_max_size, ttl_seconds=self._ttl_seconds)
                self.using_fallback = True
    
    def _make_key(self, text: str, scan_type: str = 'input') -> str:
        """Generate cache key from text and scan type."""
        content = f"{scan_type}:{text}".encode('utf-8')
        hash_key = hashlib.sha256(content).hexdigest()
        return f"{self.key_prefix}{scan_type}:{hash_key}"
    
    def _serialize(self, data: Dict[str, Any]) -> str:
        """Serialize data to JSON string."""
        return json.dumps(data)
    
    def _deserialize(self, data: str) -> Dict[str, Any]:
        """Deserialize JSON string to dict."""
        return json.loads(data)
    
    async def get(self, text: str, scan_type: str = 'input') -> Optional[Dict[str, Any]]:
        """
        Get cached scan result.
        
        Args:
            text: Text to look up
            scan_type: Type of scan ('input' or 'output')
        
        Returns:
            Cached result or None if not found
        """
        if self.using_fallback and self.fallback_cache:
            return await self.fallback_cache.get(text, scan_type)
        
        if not self.redis_client:
            async with self.lock:
                self.misses += 1
            return None
        
        key = self._make_key(text, scan_type)
        
        try:
            data = await self.redis_client.get(key)
            
            async with self.lock:
                if data is None:
                    self.misses += 1
                    return None
                
                self.hits += 1
            
            result = self._deserialize(data)
            logger.debug(f'Redis cache hit for key: {key[:32]}...')
            return result
            
        except Exception as e:
            logger.error(f'Redis get error: {e}')
            async with self.lock:
                self.errors += 1
                self.misses += 1
            
            if self.fallback_cache:
                logger.debug('Using fallback cache due to Redis error')
                return await self.fallback_cache.get(text, scan_type)
            
            return None
    
    async def set(self, text: str, result: Dict[str, Any], scan_type: str = 'input', ttl: Optional[int] = None) -> bool:
        """
        Store scan result in cache.
        
        Args:
            text: Text being cached
            result: Scan result to cache
            scan_type: Type of scan ('input' or 'output')
            ttl: Optional TTL override
        
        Returns:
            True if stored successfully
        """
        if self.using_fallback and self.fallback_cache:
            await self.fallback_cache.set(text, result, scan_type)
            return True
        
        if not self.redis_client:
            return False
        
        key = self._make_key(text, scan_type)
        ttl = ttl or self.ttl_seconds
        
        try:
            data = self._serialize(result)
            await self.redis_client.setex(key, ttl, data)
            
            logger.debug(f'Cached result in Redis: {key[:32]}... (TTL: {ttl}s)')
            return True
            
        except Exception as e:
            logger.error(f'Redis set error: {e}')
            async with self.lock:
                self.errors += 1
            
            if self.fallback_cache:
                logger.debug('Using fallback cache due to Redis error')
                await self.fallback_cache.set(text, result, scan_type)
            
            return False
    
    async def delete(self, text: str, scan_type: str = 'input') -> bool:
        """Delete a cached item."""
        if self.using_fallback and self.fallback_cache:
            return True
        
        if not self.redis_client:
            return False
        
        key = self._make_key(text, scan_type)
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f'Redis delete error: {e}')
            return False
    
    async def clear(self) -> None:
        """Clear all cached items with the key prefix."""
        if self.using_fallback and self.fallback_cache:
            await self.fallback_cache.clear()
            return
        
        if not self.redis_client:
            return
        
        try:
            pattern = f"{self.key_prefix}*"
            deleted = 0
            
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                await self.redis_client.delete(key)
                deleted += 1
            
            logger.info(f'Cleared {deleted} items from Redis cache')
            
            async with self.lock:
                self.hits = 0
                self.misses = 0
                self.errors = 0
                
        except Exception as e:
            logger.error(f'Redis clear error: {e}')
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0
            
            stats = {
                'backend': 'redis' if not self.using_fallback else 'memory',
                'hits': self.hits,
                'misses': self.misses,
                'errors': self.errors,
                'hit_rate': round(hit_rate, 2),
                'ttl_seconds': self.ttl_seconds,
            }
            
            if self.redis_client and not self.using_fallback:
                try:
                    info = await self.redis_client.info('stats')
                    stats['redis_connected_clients'] = info.get('connected_clients', 0)
                    stats['redis_total_commands'] = info.get('total_commands_processed', 0)
                    
                    memory_info = await self.redis_client.info('memory')
                    stats['redis_memory_used_mb'] = round(memory_info.get('used_memory', 0) / (1024**2), 2)
                except Exception as e:
                    logger.debug(f'Could not get Redis stats: {e}')
            
            if self.fallback_cache:
                fallback_stats = await self.fallback_cache.get_stats()
                stats['fallback'] = fallback_stats
            
            return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        health = {
            'healthy': False,
            'backend': 'redis' if not self.using_fallback else 'memory',
            'using_fallback': self.using_fallback,
        }
        
        if self.redis_client and not self.using_fallback:
            try:
                await self.redis_client.ping()
                health['healthy'] = True
                health['latency_ms'] = await self._measure_latency()
            except Exception as e:
                health['error'] = str(e)
                health['healthy'] = False
        elif self.fallback_cache:
            health['healthy'] = True
        
        return health
    
    async def _measure_latency(self) -> float:
        """Measure Redis latency."""
        if not self.redis_client:
            return 0.0
        
        try:
            start = time.time()
            await self.redis_client.ping()
            return round((time.time() - start) * 1000, 2)
        except Exception:
            return 0.0
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info('Redis connection closed')
            except Exception as e:
                logger.error(f'Error closing Redis connection: {e}')


class GuardCache:
    """Async cache manager for LLM Guard scan results."""
    
    def __init__(
        self,
        enabled: bool = True,
        backend: str = 'auto',
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        redis_max_connections: int = 50,
        redis_timeout: int = 5,
    ):
        self.enabled = enabled
        self.backend = backend
        self.cache: Optional[Union[RedisCache, LRUCache]] = None
        
        if not enabled:
            logger.info('Guard caching disabled')
            return
        
        if backend == 'auto':
            backend = 'redis' if HAS_REDIS else 'memory'
        
        if backend == 'redis':
            self.cache = RedisCache(
                host=redis_host, port=redis_port, db=redis_db, password=redis_password,
                max_connections=redis_max_connections, socket_timeout=redis_timeout,
                ttl_seconds=ttl_seconds, fallback_enabled=True, fallback_max_size=max_size
            )
        else:
            self.cache = LRUCache(max_size=max_size, ttl_seconds=ttl_seconds)
            
        logger.info(f'Guard caching configured with {backend} backend')

    async def initialize(self):
        """Initialize the cache backend."""
        if self.cache and hasattr(self.cache, 'initialize'):
            await self.cache.initialize()

    async def get_input_result(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Get cached input scan result."""
        if not self.enabled or not self.cache:
            return None
        return await self.cache.get(prompt, scan_type='input')
    
    async def set_input_result(self, prompt: str, result: Dict[str, Any]) -> None:
        """Cache input scan result."""
        if self.enabled and self.cache:
            await self.cache.set(prompt, result, scan_type='input')
    
    async def get_output_result(self, text: str) -> Optional[Dict[str, Any]]:
        """Get cached output scan result."""
        if not self.enabled or not self.cache:
            return None
        return await self.cache.get(text, scan_type='output')
    
    async def set_output_result(self, text: str, result: Dict[str, Any]) -> None:
        """Cache output scan result."""
        if self.enabled and self.cache:
            await self.cache.set(text, result, scan_type='output')
    
    async def clear(self) -> None:
        """Clear cache."""
        if self.enabled and self.cache:
            await self.cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or not self.cache:
            return {'enabled': False}
        
        stats = await self.cache.get_stats()
        stats['enabled'] = True
        return stats
    
    async def cleanup_expired(self) -> int:
        """Remove expired items."""
        if self.enabled and self.cache and hasattr(self.cache, 'cleanup_expired'):
            return await self.cache.cleanup_expired()
        return 0
