"""
Ollama Guardrails - Main Application Module

This module contains the FastAPI application factory and main server logic.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, ORJSONResponse

from .core.cache import GuardCache
from .core.concurrency import ConcurrencyManager
from .core.config import Config
from .guards.guard_manager import LLMGuardManager
from .middleware.http_client import close_http_client, get_http_client
from .middleware.ip_whitelist import IPWhitelist
from .utils import extract_client_ip, force_cpu_mode

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

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Check cache availability
try:
    HAS_CACHE = True
except ImportError as e:
    logger.warning(f"Cache not available: {e}")
    HAS_CACHE = False
    GuardCache = None  # type: ignore[misc,assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Application starting up...")
    
    # Log offline mode configuration
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
    
    # Initialize async components
    if HAS_CACHE and hasattr(app.state, "guard_cache") and app.state.guard_cache:
        await app.state.guard_cache.initialize()
    
    config = app.state.config
    guard_cache = getattr(app.state, "guard_cache", None)
    ip_whitelist = app.state.ip_whitelist
    
    logger.info("Application startup complete")
    logger.info(f"Ollama URL: {config.get('ollama_url')}")
    logger.info(f"Input guard: {'enabled' if config.get_bool('enable_input_guard', True) else 'disabled'}")
    logger.info(f"Output guard: {'enabled' if config.get_bool('enable_output_guard', True) else 'disabled'}")
    logger.info(f"Cache: {'enabled' if guard_cache else 'disabled'}")
    logger.info(f"IP whitelist: {'enabled' if ip_whitelist.get_stats()['enabled'] else 'disabled'}")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    await close_http_client()
    logger.info("Application shutdown complete")


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

    # Initialize guard manager (scanners load at startup)
    guard_manager = LLMGuardManager(
        enable_input=config.get_bool("enable_input_guard", True),
        enable_output=config.get_bool("enable_output_guard", True),
        lazy_init=False,  # Scanners initialize at startup
    )

    # Initialize IP whitelist (nginx only)
    ip_whitelist = IPWhitelist(config.get_list("nginx_whitelist", []))

    # Initialize concurrency manager (Ollama-style)
    num_parallel = config.get("ollama_num_parallel", "auto")
    if num_parallel == "auto":
        concurrency_manager = ConcurrencyManager(
            default_parallel=None,  # Auto-detect
            default_queue_limit=config.get_int("ollama_max_queue", 512),
            auto_detect_parallel=True,
        )
    else:
        concurrency_manager = ConcurrencyManager(
            default_parallel=int(num_parallel),
            default_queue_limit=config.get_int("ollama_max_queue", 512),
            auto_detect_parallel=False,
        )

    # Initialize cache
    guard_cache = None
    if HAS_CACHE:
        cache_enabled = config.get_bool("cache_enabled", True)
        if cache_enabled:
            guard_cache = GuardCache(
                enabled=True,
                backend=config.get_str("cache_backend", "auto"),
                max_size=config.get_int("cache_max_size", 1000),
                ttl_seconds=config.get_int("cache_ttl", 3600),
                redis_host=config.get_str("redis_host", "localhost"),
                redis_port=config.get_int("redis_port", 6379),
                redis_db=config.get_int("redis_db", 0),
                redis_password=config.get_str("redis_password"),
                redis_max_connections=config.get_int("redis_max_connections", 50),
                redis_timeout=config.get_int("redis_timeout", 5),
            )
            logger.info(f"Guard cache initialized: backend={guard_cache.backend}")

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
    app.state.ip_whitelist = ip_whitelist
    app.state.concurrency_manager = concurrency_manager
    app.state.guard_cache = guard_cache

    @app.middleware("http")
    async def check_ip_whitelist(request: Request, call_next: Any) -> Any:
        """Middleware to check IP whitelist (nginx only)."""
        client_ip = extract_client_ip(request)
        
        # Check if client IP is whitelisted
        if not ip_whitelist.is_allowed(client_ip):
            logger.warning(
                f"Rejected request from non-whitelisted IP: {client_ip} "
                f"{request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "access_denied",
                    "message": "Access denied. Only requests from whitelisted IPs are allowed.",
                    "client_ip": client_ip,
                },
            )
        
        logger.debug(f"IP whitelist check passed for {client_ip}")
        response = await call_next(request)
        return response

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        """Log requests with client IP and path."""
        client_ip = extract_client_ip(request)
        logger.info("Request from %s: %s %s", client_ip, request.method, request.url.path)
        start_ts = time.time()
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.time() - start_ts) * 1000)
            response_obj = locals().get("response", None)
            if response_obj and hasattr(response_obj, "status_code"):
                logger.info("Response status: %s (%d ms)", response_obj.status_code, duration_ms)
            else:
                logger.info("Response completed (%d ms)", duration_ms)

    # Create and register endpoint routers
    ollama_router = create_ollama_endpoints(
        config=config,
        guard_manager=guard_manager,
        concurrency_manager=concurrency_manager,
        guard_cache=guard_cache,
        has_cache=HAS_CACHE,
    )

    openai_router = create_openai_endpoints(
        config=config,
        guard_manager=guard_manager,
        concurrency_manager=concurrency_manager,
        guard_cache=guard_cache,
        has_cache=HAS_CACHE,
    )

    admin_router = create_admin_endpoints(
        config=config,
        guard_manager=guard_manager,
        ip_whitelist=ip_whitelist,
        concurrency_manager=concurrency_manager,
        guard_cache=guard_cache,
        has_cache=HAS_CACHE,
    )

    # Include routers in the app
    app.include_router(ollama_router, tags=["Ollama"])
    app.include_router(openai_router, tags=["OpenAI"])
    app.include_router(admin_router, tags=["Admin"])

    return app


# Create the default app instance
app = create_app()


def run_server() -> None:
    """Run the server with configuration from environment or config file."""
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
    logger.info("  Admin API: /health, /config, /stats, /admin/*, /queue/*")
    logger.info("=" * 60)
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()