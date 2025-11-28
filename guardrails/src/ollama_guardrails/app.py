"""
Ollama Guardrails - Main Application Module

This module contains the FastAPI application factory and main server logic.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import time
import warnings
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse

# Suppress the FutureWarning about TRANSFORMERS_CACHE being deprecated in transformers v5
# This warning comes from llm-guard dependencies, not our code
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers.utils.hub')

from .core.config import Config
from .guards.guard_manager import LLMGuardManager
from .middleware.http_client import close_http_client, get_http_client
from .utils import force_cpu_mode

# Set HF_HOME before any transformers imports to avoid TRANSFORMERS_CACHE deprecation warning
# This must be done BEFORE any imports that use transformers
if not os.environ.get('HF_HOME'):
    os.environ['HF_HOME'] = os.environ.get('HF_HOME', './models/huggingface')

# Initialize offline mode for tiktoken and Hugging Face BEFORE importing llm-guard
# (Using early initialization before logger is available)
try:
    from .utils.tiktoken_cache import setup_tiktoken_offline_mode
    from .utils.huggingface_cache import setup_huggingface_offline_mode
    
    # Setup tiktoken offline mode (also sets up HF)
    if os.environ.get('TIKTOKEN_OFFLINE_MODE', '').lower() in ('1', 'true', 'yes', 'on', ''):
        setup_tiktoken_offline_mode()
    
    # Also explicitly setup HF if requested
    if os.environ.get('HF_OFFLINE', '').lower() in ('1', 'true', 'yes', 'on'):
        setup_huggingface_offline_mode()
except (ImportError, Exception):
    # Silently fail early - will be logged after logger is initialized
    pass

# Force CPU mode if requested via environment variable
if os.environ.get('LLM_GUARD_FORCE_CPU', '').lower() in ('1', 'true', 'yes', 'on'):
    force_cpu_mode(verbose=True)
elif os.environ.get('LLM_GUARD_DEVICE', '').lower() == 'cpu':
    force_cpu_mode(verbose=False)

# Import endpoint modules
from .api.endpoints_admin import create_admin_endpoints
from .api.endpoints_ollama import create_ollama_endpoints
from .api.endpoints_openai import create_openai_endpoints

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

def _resolve_log_level(default: str = "INFO") -> int:
    env_level = os.environ.get("LOG_LEVEL", default)
    try:
        return getattr(logging, env_level.upper())
    except AttributeError:
        return getattr(logging, default.upper(), logging.INFO)

# Configure logging respecting LOG_LEVEL env (default INFO)
_LOG_LEVEL = _resolve_log_level()

# Optimize logging for performance:
# 1. Use a memory handler to buffer logs and reduce disk I/O
# 2. Flush buffer when it reaches capacity or on shutdown
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))

# Use MemoryHandler to buffer logs (flush every 100 records or 5 seconds)
_memory_handler = logging.handlers.MemoryHandler(
    capacity=100,  # Buffer up to 100 log records
    flushLevel=logging.ERROR,  # Immediately flush on ERROR or higher
    target=_log_handler,
    flushOnClose=True,
)

logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[_memory_handler],
    force=True,
)

# Silence verbose third-party loggers (llm-guard, transformers, etc.)
# These libraries output debug/info logs even when LOG_LEVEL is set higher
_third_party_log_level = max(_LOG_LEVEL, logging.WARNING)
for _lib_name in (
    "llm_guard",
    "transformers",
    "torch",
    "sentence_transformers",
    "huggingface_hub",
    "httpx",
    "httpcore",
    "urllib3",
    "filelock",
):
    logging.getLogger(_lib_name).setLevel(_third_party_log_level)

logger = logging.getLogger(__name__)
logger.setLevel(_LOG_LEVEL)


def _flush_log_buffer() -> None:
    """Flush the log memory buffer to disk."""
    _memory_handler.flush()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Application starting up...")
    
    # Log offline mode configuration (only once at startup)
    tiktoken_cache = os.environ.get('TIKTOKEN_CACHE_DIR', './models/tiktoken')
    hf_home = os.environ.get('HF_HOME', './models/huggingface')
    tiktoken_offline = os.environ.get('TIKTOKEN_OFFLINE_MODE', 'true').lower() in ('1', 'true', 'yes', 'on')
    hf_offline = os.environ.get('HF_OFFLINE', 'true').lower() in ('1', 'true', 'yes', 'on')
    
    if tiktoken_offline or hf_offline:
        logger.info("Offline mode configuration:")
        if tiktoken_offline:
            logger.info(f"  - Tiktoken cache: {tiktoken_cache}")
        if hf_offline:
            logger.info(f"  - Hugging Face cache: {hf_home}")
    
    # Initialize the HTTP client on startup
    get_http_client()
    
    config = app.state.config
    
    logger.info("Application startup complete")
    logger.info(f"Ollama URL: {config.get('ollama_url')}")
    logger.info(f"Input guard: {'enabled' if config.get_bool('enable_input_guard', True) else 'disabled'}")
    logger.info(f"Output guard: {'enabled' if config.get_bool('enable_output_guard', True) else 'disabled'}")
    
    # Flush startup logs to disk immediately
    _flush_log_buffer()
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    await close_http_client()
    logger.info("Application shutdown complete")
    
    # Ensure all logs are flushed on shutdown
    _flush_log_buffer()


def create_app(config_file: str | None = None) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Configured FastAPI application
    """
    # Initialize configuration
    config = Config(config_file or os.environ.get("CONFIG_FILE"))

    # Get individual scanner configurations from config.yaml
    # Note: Don't pass mutable defaults (like {}) to config.get() - it uses lru_cache
    input_scanners_config = config.get("input_scanners", None) or {}
    output_scanners_config = config.get("output_scanners", None) or {}

    # Initialize guard manager (scanners load at startup)
    guard_manager = LLMGuardManager(
        enable_input=config.get_bool("enable_input_guard", True),
        enable_output=config.get_bool("enable_output_guard", True),
        lazy_init=False,  # Scanners initialize at startup
        enable_input_code_scanner=config.get_bool("enable_input_code_scanner", False),
        input_scanners_config=input_scanners_config,
        output_scanners_config=output_scanners_config,
    )

    # Create FastAPI app with lifespan
    app = FastAPI(
        title="Ollama Guardrails",
        description="Advanced LLM Guard Proxy for Ollama with comprehensive security scanning",
        version="1.0.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Store components in app state
    app.state.config = config
    app.state.guard_manager = guard_manager

    # Configure CORS
    cors_allow_origins = config.get_list("cors_allow_origins") or ["*"]
    cors_allow_origin_regex = config.get_str("cors_allow_origin_regex", "")
    cors_allow_methods = config.get_list("cors_allow_methods") or ["*"]
    cors_allow_headers = config.get_list("cors_allow_headers") or ["*"]
    cors_expose_headers = config.get_list("cors_expose_headers") or []
    cors_allow_credentials = config.get_bool("cors_allow_credentials", False)
    cors_max_age = config.get_int("cors_max_age", 600)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins,
        allow_origin_regex=cors_allow_origin_regex or None,
        allow_credentials=cors_allow_credentials,
        allow_methods=cors_allow_methods,
        allow_headers=cors_allow_headers,
        expose_headers=cors_expose_headers,
        max_age=cors_max_age,
    )

    # TrustedHost middleware for reverse proxy support
    # Allows proper client IP detection from X-Forwarded-For headers
    trusted_hosts = config.get_list("trusted_hosts") or ["*"]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts + ["*"] if config.get("forwarded_allow_ips") == "*" else trusted_hosts
    )

    # Skip logging for health check endpoints to reduce I/O
    _skip_log_paths = frozenset({"/health", "/favicon.ico", "/metrics"})
    
    # Check if we should enable access logging (disabled by default for performance)
    _enable_access_log = config.get_bool("enable_access_log", False)

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        """Log requests with path and timing (optimized for performance)."""
        path = request.url.path
        
        # Skip logging for health checks and static assets to reduce I/O
        if path in _skip_log_paths or not _enable_access_log:
            return await call_next(request)
        
        # Only log at DEBUG level for regular requests to reduce disk I/O
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Request: %s %s", request.method, path)
        
        start_ts = time.time()
        try:
            response = await call_next(request)
            return response
        finally:
            # Only log timing for slow requests (>1s) or errors at INFO level
            duration_ms = int((time.time() - start_ts) * 1000)
            response_obj = locals().get("response", None)
            status_code = getattr(response_obj, "status_code", 0) if response_obj else 0
            
            # Log slow requests (>1000ms) or errors at WARNING level
            if duration_ms > 1000 or status_code >= 400:
                logger.warning("Slow/Error: %s %s -> %s (%d ms)", 
                              request.method, path, status_code, duration_ms)
            elif logger.isEnabledFor(logging.DEBUG):
                logger.debug("Response: %s (%d ms)", status_code, duration_ms)

    @app.middleware("http")
    async def handle_reverse_proxy_headers(request: Request, call_next: Any) -> Any:
        """
        Handle X-Forwarded-* headers for reverse proxy support.
        Enables proper client IP detection when behind nginx, Apache, etc.
        """
        response = await call_next(request)
        
        # Add Via header for reverse proxy chain visibility
        via = response.headers.get("Via", "")
        app_name = "Ollama-Guardrails/1.0"
        response.headers["Via"] = f"{via}, {app_name}" if via else f"1.1 {app_name}"
        
        return response

    # Create and register endpoint routers
    ollama_router = create_ollama_endpoints(
        config=config,
        guard_manager=guard_manager,
    )

    openai_router = create_openai_endpoints(
        config=config,
        guard_manager=guard_manager,
    )

    admin_router = create_admin_endpoints(
        config=config,
        guard_manager=guard_manager,
    )

    # Include routers in the app
    app.include_router(ollama_router, tags=["Ollama"])
    app.include_router(openai_router, tags=["OpenAI"])
    app.include_router(admin_router, tags=["Admin"])

    return app


# Create the default app instance
app = create_app()


def run_server() -> None:
    """
    Run the server with Uvicorn.
    
    Uses FastAPI's native async handling for concurrent requests.
    Uvicorn handles worker management automatically.
    See: https://fastapi.tiangolo.com/async/#in-a-hurry
    """
    config_file = os.environ.get("CONFIG_FILE")
    config = Config(config_file)
    
    host = config.get("proxy_host", "0.0.0.0")
    port = config.get("proxy_port", 8080)
    
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    logger.info("=" * 60)
    logger.info("Available Endpoints:")
    logger.info("  Ollama API: /api/* (12 endpoints)")
    logger.info("  OpenAI API: /v1/* (4 endpoints)")
    logger.info("  Admin API: /health, /config, /stats")
    logger.info("=" * 60)
    
    # Simple Uvicorn configuration - FastAPI handles async concurrency
    uvicorn.run(
        app,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    run_server()