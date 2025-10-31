"""
Admin and monitoring endpoints for the guard proxy.

This module contains administrative and monitoring endpoints:
- Health check (/health)
- Configuration (/config)
- Statistics (/stats)
- Cache management (/admin/cache/*)
- Queue management (/queue/*, /admin/queue/*)
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def create_admin_endpoints(config, guard_manager, ip_whitelist, concurrency_manager, guard_cache, has_cache):
    """
    Create admin and monitoring endpoints with dependency injection.
    
    Args:
        config: Configuration object
        guard_manager: LLM Guard manager instance
        ip_whitelist: IP whitelist manager
        concurrency_manager: Concurrency manager instance
        guard_cache: Cache instance (or None)
        has_cache: Whether cache is available
    """
    
    @router.get("/health")
    async def health_check():
        """Health check endpoint with performance metrics."""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "guards": {
                "input_guard": "enabled" if getattr(guard_manager, 'enable_input', False) else "disabled",
                "output_guard": "enabled" if getattr(guard_manager, 'enable_output', False) else "disabled",
            },
            "whitelist": ip_whitelist.get_stats(),
        }
        
        # Add concurrency info
        queue_stats = await concurrency_manager.get_stats()
        health_data['concurrency'] = {
            "default_parallel": queue_stats.get('default_parallel'),
            "default_queue_limit": queue_stats.get('default_queue_limit'),
            "total_models": queue_stats.get('total_models', 0),
            "memory": concurrency_manager.get_memory_info()
        }
        
        # Add device information
        if hasattr(guard_manager, 'device'):
            health_data['device'] = guard_manager.device
        
        # Add cache stats if available
        if has_cache and guard_cache:
            health_data['cache'] = await guard_cache.get_stats()
        
        return health_data

    @router.get("/config")
    async def get_config():
        """Get current configuration (non-sensitive)."""
        # Build a minimal, non-sensitive view of the configuration
        safe_config = {
            'ollama_url': config.get('ollama_url'),
            'ollama_path': config.get('ollama_path'),
            'proxy_host': config.get('proxy_host'),
            'proxy_port': config.get('proxy_port'),
            'enable_input_guard': config.get('enable_input_guard'),
            'enable_output_guard': config.get('enable_output_guard'),
            'block_on_guard_error': config.get('block_on_guard_error'),
        }
        
        # Show whitelist summary (enabled, count) but not the raw IPs
        wl = ip_whitelist.get_stats()
        safe_config['nginx_whitelist'] = {'enabled': wl['enabled'], 'count': wl['count']}
        
        # Add optimization status
        if has_cache:
            safe_config['optimizations'] = {
                'cache_enabled': guard_cache is not None and guard_cache.enabled,
            }
            
            # Add device info
            if hasattr(guard_manager, 'device'):
                safe_config['device'] = guard_manager.device
        
        return safe_config

    @router.get("/stats")
    async def get_stats():
        """Get comprehensive statistics."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "guards": {
                "input_enabled": getattr(guard_manager, 'enable_input', False),
                "output_enabled": getattr(guard_manager, 'enable_output', False),
                "device": getattr(guard_manager, 'device', 'unknown'),
            },
            "whitelist": ip_whitelist.get_stats(),
        }
        
        if has_cache:
            # Cache stats
            if guard_cache:
                stats['cache'] = await guard_cache.get_stats()
        
        return stats

    @router.post("/admin/cache/clear")
    async def clear_cache():
        """Clear the cache (admin endpoint)."""
        if not has_cache or not guard_cache:
            return {"error": "Cache not available"}
        
        await guard_cache.clear()
        return {"status": "success", "message": "Cache cleared"}

    @router.post("/admin/cache/cleanup")
    async def cleanup_cache():
        """Clean up expired cache entries."""
        if not has_cache or not guard_cache:
            return {"error": "Cache not available"}
        
        removed = await guard_cache.cleanup_expired()
        return {"status": "success", "removed": removed}

    @router.get("/queue/stats")
    async def get_queue_stats(model: Optional[str] = None):
        """Get queue statistics for all models or a specific model."""
        stats = await concurrency_manager.get_stats(model_name=model)
        return stats

    @router.get("/queue/memory")
    async def get_memory_info():
        """Get current memory information and recommended parallel limit."""
        return concurrency_manager.get_memory_info()

    @router.post("/admin/queue/reset")
    async def reset_queue_stats(model: Optional[str] = None):
        """Reset queue statistics (admin endpoint)."""
        await concurrency_manager.reset_stats(model_name=model)
        return {
            "status": "success",
            "message": f"Statistics reset for {'all models' if not model else f'model {model}'}"
        }

    @router.post("/admin/queue/update")
    async def update_queue_limits(
        model: str,
        parallel_limit: Optional[int] = None,
        queue_limit: Optional[int] = None
    ):
        """Update queue limits for a specific model (admin endpoint)."""
        result = await concurrency_manager.update_limits(
            model_name=model,
            parallel_limit=parallel_limit,
            queue_limit=queue_limit
        )
        return result
    
    return router
