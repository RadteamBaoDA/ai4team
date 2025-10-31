"""
API endpoints and handlers.

This package contains FastAPI endpoint definitions for:
- Ollama API compatibility
- OpenAI API compatibility  
- Administrative endpoints
- Streaming response handlers
"""

from __future__ import annotations

from .endpoints_admin import create_admin_endpoints
from .endpoints_ollama import create_ollama_endpoints
from .endpoints_openai import create_openai_endpoints

# Import streaming handlers if available
try:
    from .streaming_handlers import (
        handle_ollama_stream,
        handle_openai_stream,
        stream_ollama_response,
        stream_openai_response,
    )
    
    __all__ = [
        "create_ollama_endpoints",
        "create_openai_endpoints", 
        "create_admin_endpoints",
        "handle_ollama_stream",
        "handle_openai_stream",
        "stream_ollama_response",
        "stream_openai_response",
    ]
except ImportError:
    __all__ = [
        "create_ollama_endpoints",
        "create_openai_endpoints", 
        "create_admin_endpoints",
    ]