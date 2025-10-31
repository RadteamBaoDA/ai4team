"""
Ollama Guard Proxy - Entry Point

This is the main entry point for the Ollama Guard Proxy application.
All source code is in the src/ directory.

Usage:
    python main.py
    
Or with Uvicorn:
    uvicorn src.ollama_guard_proxy:app --host 0.0.0.0 --port 8080
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
if __name__ == "__main__":
    from src.ollama_guard_proxy import app, config, logger
    import uvicorn
    
    host = config.get('proxy_host', '0.0.0.0')
    port = config.get('proxy_port', 8080)
    
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    logger.info("=" * 60)
    logger.info("Available Endpoints:")
    logger.info("  Ollama API: /api/* (12 endpoints)")
    logger.info("  OpenAI API: /v1/* (4 endpoints)")
    logger.info("  Admin API: /health, /config, /stats, /admin/*, /queue/*")
    logger.info("=" * 60)
    
    uvicorn.run(app, host=host, port=port)
