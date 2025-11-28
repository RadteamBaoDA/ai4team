"""
Ollama Guardrails - Advanced LLM Guard Proxy for Ollama

A comprehensive security proxy for Ollama that provides:
- Input/Output scanning with LLM Guard  
- Streaming response support
- OpenAI API compatibility
- Modern Python 3.9+ async architecture (FastAPI native async handling)

Usage:
    Basic server:
        from ollama_guardrails import create_app
        app = create_app()
        
    CLI usage:
        ollama-guardrails server --config config.yaml
        
    Direct import:
        from ollama_guardrails.app import app

Example:
    >>> from ollama_guardrails import create_app
    >>> app = create_app(config_file="config.yaml")
    >>> # Use with uvicorn: uvicorn main:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "AI4Team"
__email__ = "contact@ai4team.dev"
__description__ = "Advanced LLM Guard Proxy for Ollama with comprehensive security scanning"
__url__ = "https://github.com/RadteamBaoDA/ai4team"

# Import main components for easy access
from .app import app, create_app, run_server
from .core.config import Config
from .guards.guard_manager import LLMGuardManager

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__", 
    "__email__",
    "__description__",
    "__url__",
    
    # Main application components
    "app",
    "create_app",
    "run_server",
    "Config",
    "LLMGuardManager",
]


def get_version() -> str:
    """Get the package version."""
    return __version__