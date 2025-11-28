"""
Admin endpoints for the guard proxy.

This module contains administrative endpoints:
- Health check (/health)
- Configuration (/config)
- Statistics (/stats)
"""

from datetime import datetime

from fastapi import APIRouter

# Create router
router = APIRouter()


def create_admin_endpoints(config, guard_manager):
    """
    Create admin endpoints with dependency injection.
    
    Args:
        config: Configuration object
        guard_manager: LLM Guard manager instance
    """
    
    @router.get("/health")
    async def health_check():
        """Health check endpoint."""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "guards": {
                "input_guard": "enabled" if getattr(guard_manager, 'enable_input', False) else "disabled",
                "output_guard": "enabled" if getattr(guard_manager, 'enable_output', False) else "disabled",
            },
        }
        
        # Add device information
        if hasattr(guard_manager, 'device'):
            health_data['device'] = guard_manager.device
        
        return health_data

    @router.get("/config")
    async def get_config():
        """Get current configuration (non-sensitive)."""
        safe_config = {
            'ollama_url': config.get('ollama_url'),
            'ollama_path': config.get('ollama_path'),
            'proxy_host': config.get('proxy_host'),
            'proxy_port': config.get('proxy_port'),
            'enable_input_guard': config.get('enable_input_guard'),
            'enable_output_guard': config.get('enable_output_guard'),
            'block_on_guard_error': config.get('block_on_guard_error'),
        }
        
        # Add device info
        if hasattr(guard_manager, 'device'):
            safe_config['device'] = guard_manager.device
        
        return safe_config

    @router.get("/stats")
    async def get_stats():
        """Get guard statistics."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "guards": {
                "input_enabled": getattr(guard_manager, 'enable_input', False),
                "output_enabled": getattr(guard_manager, 'enable_output', False),
                "device": getattr(guard_manager, 'device', 'unknown'),
            },
        }
        
        return stats
    
    return router
