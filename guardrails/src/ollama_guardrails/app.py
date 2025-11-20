"""
Ollama Guardrails - Main Application Module

This module contains the FastAPI application factory and main server logic.
"""

from __future__ import annotations

import logging
import os
import time
import multiprocessing
import warnings
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse

# Suppress the FutureWarning about TRANSFORMERS_CACHE being deprecated in transformers v5
# This warning comes from llm-guard dependencies, not our code
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers.utils.hub')

from .core.cache import GuardCache
from .core.concurrency import ConcurrencyManager
from .core.config import Config
from .guards.guard_manager import LLMGuardManager
from .middleware.http_client import close_http_client, get_http_client
from .middleware.ip_whitelist import IPWhitelist
from .utils import extract_client_ip, force_cpu_mode

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
        enable_input_code_scanner=config.get_bool("enable_input_code_scanner", False),
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

    @app.middleware("http")
    async def request_queue_status(request: Request, call_next: Any) -> Any:
        """
        Add request queue information to response headers.
        When workers are busy, requests are queued by OS/Uvicorn.
        """
        response = await call_next(request)
        
        # Get current concurrency stats
        try:
            stats = await concurrency_manager.get_stats()
            total_active = sum(
                model_stats.get("active_requests", 0)
                for model_stats in stats.get("models", {}).values()
            )
            total_queued = sum(
                model_stats.get("queued_requests", 0)
                for model_stats in stats.get("models", {}).values()
            )
            
            response.headers["X-Queue-Status"] = "active" if total_queued > 0 else "idle"
            response.headers["X-Active-Requests"] = str(total_active)
            response.headers["X-Queued-Requests"] = str(total_queued)
        except Exception as e:
            logger.debug(f"Could not get queue stats: {e}")
        
        return response

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
    """Run the server with production-optimized Uvicorn configuration."""
    config_file = os.environ.get("CONFIG_FILE")
    config = Config(config_file)
    
    host = config.get("proxy_host", "0.0.0.0")
    port = config.get("proxy_port", 8080)
    
    # Get worker count from config (default to CPU core count)
    workers_config = config.get("workers", "auto")
    if workers_config == "auto":
        workers = multiprocessing.cpu_count()
    else:
        try:
            workers = int(workers_config)
        except (ValueError, TypeError):
            workers = multiprocessing.cpu_count()
    
    # Get request queue configuration
    queue_size = config.get_int("queue_size", 1024)
    queue_timeout = config.get_int("queue_timeout", 30)
    
    # Production Uvicorn settings
    access_log = config.get_bool("access_log", False)
    timeout_keep_alive = config.get_int("timeout_keep_alive", 65)
    limit_max_requests = config.get_int("limit_max_requests", 1000)
    
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    logger.info(f"Worker threads: {workers} (one request per thread, based on CPU cores)")
    logger.info(f"Request queue: {queue_size} max requests (timeout: {queue_timeout}s)")
    logger.info("=" * 60)
    logger.info("Production Configuration:")
    logger.info(f"  - Access log: {'enabled' if access_log else 'disabled'}")
    logger.info(f"  - Keep-alive timeout: {timeout_keep_alive}s")
    logger.info(f"  - Max requests per worker: {limit_max_requests}")
    logger.info(f"  - Reverse proxy mode: enabled (X-Forwarded-* headers supported)")
    logger.info("=" * 60)
    logger.info("Available Endpoints:")
    logger.info("  Ollama API: /api/* (12 endpoints)")
    logger.info("  OpenAI API: /v1/* (4 endpoints)")
    logger.info("  Admin API: /health, /config, /stats, /admin/*, /queue/*")
    logger.info("=" * 60)
    logger.info("When workers are busy: requests will queue up to %d slots", queue_size)
    logger.info("=" * 60)
    
    # Production-optimized Uvicorn configuration
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers,
        backlog=queue_size,                    # TCP accept queue size
        timeout_keep_alive=timeout_keep_alive,  # Connection keep-alive timeout
        limit_max_requests=limit_max_requests,  # Restart worker after N requests (memory leak prevention)
        limit_concurrency=None,                 # Let OS handle concurrency
        access_log=access_log,                  # Disable for high-traffic environments
        interface="asgi3",                      # Use ASGI3 interface
        loop="auto",                            # Auto-detect best event loop
        http="auto",                            # Auto-detect HTTP server (httptools > h11)
        log_config={                            # Custom log config
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "access": {
                    "format": '%(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s %(message)s',
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": "INFO",
                },
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": "INFO" if access_log else "CRITICAL",
                    "propagate": False,
                },
            },
        },
    )


if __name__ == "__main__":
    run_server()