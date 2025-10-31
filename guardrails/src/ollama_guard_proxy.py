"""
Ollama Proxy with LLM Guard Integration

This proxy applies LLM Guard scanners to both input prompts and model outputs.

Features:
- Input scanning (prompt injection, toxicity, secrets, etc.)
- Output scanning (toxicity, bias, malicious URLs, code generation, etc.)
- Streaming response support
- Comprehensive logging and metrics
- Configuration via YAML or environment variables
- IP whitelist support (restrict access to nginx only)

Usage:
    pip install fastapi uvicorn requests pydantic pyyaml llm-guard
    python ollama_guard_proxy.py

Or with Uvicorn directly:
    uvicorn ollama_guard_proxy:app --host 0.0.0.0 --port 8080

IP Whitelist (Nginx Only):
    # Via environment variable (comma-separated)
    export NGINX_WHITELIST="127.0.0.1,192.168.1.10,10.0.0.5"
    
    # Via YAML configuration file
    # nginx_whitelist:
    #   - "127.0.0.1"
    #   - "192.168.1.10"
    #   - "10.0.0.5"
"""

import os
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, ORJSONResponse
import uvicorn

from config import Config
from ip_whitelist import IPWhitelist
from guard_manager import LLMGuardManager
from concurrency import ConcurrencyManager
from http_client import get_http_client, close_http_client
from utils import extract_client_ip

# Import endpoint modules
from endpoints_ollama import create_ollama_endpoints
from endpoints_openai import create_openai_endpoints
from endpoints_admin import create_admin_endpoints

logger = logging.getLogger(__name__)

# Import caching
try:
    from cache import GuardCache
    HAS_CACHE = True
except ImportError as e:
    logger.warning(f'Cache not available: {e}')
    HAS_CACHE = False
    GuardCache = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Constants
DEFAULTS = {
    'OLLAMA_URL': 'http://127.0.0.1:11434',
    'OLLAMA_PATH': '/api/generate',
    'PROXY_PORT': 8080,
    'PROXY_HOST': '0.0.0.0',
}

# Initialize app and components
config = Config(os.environ.get('CONFIG_FILE'))

# Initialize guard manager (scanners load at startup)
guard_manager = LLMGuardManager(
    enable_input=config.get_bool('enable_input_guard', True),
    enable_output=config.get_bool('enable_output_guard', True),
    lazy_init=False  # Scanners initialize at startup
)

# Initialize IP whitelist (nginx only)
ip_whitelist = IPWhitelist(config.get_list('nginx_whitelist', []))

# Initialize concurrency manager (Ollama-style)
num_parallel = config.get('ollama_num_parallel', 'auto')
if num_parallel == 'auto':
    concurrency_manager = ConcurrencyManager(
        default_parallel=None,  # Auto-detect
        default_queue_limit=config.get_int('ollama_max_queue', 512),
        auto_detect_parallel=True
    )
else:
    concurrency_manager = ConcurrencyManager(
        default_parallel=int(num_parallel),
        default_queue_limit=config.get_int('ollama_max_queue', 512),
        auto_detect_parallel=False
    )

# Initialize cache
guard_cache = None

if HAS_CACHE:
    # Initialize cache with Redis support
    cache_enabled = config.get_bool('cache_enabled', True)
    if cache_enabled:
        guard_cache = GuardCache(
            enabled=True,
            backend=config.get_str('cache_backend', 'auto'),
            max_size=config.get_int('cache_max_size', 1000),
            ttl_seconds=config.get_int('cache_ttl', 3600),
            redis_host=config.get_str('redis_host', 'localhost'),
            redis_port=config.get_int('redis_port', 6379),
            redis_db=config.get_int('redis_db', 0),
            redis_password=config.get_str('redis_password'),
            redis_max_connections=config.get_int('redis_max_connections', 50),
            redis_timeout=config.get_int('redis_timeout', 5),
        )
        logger.info(f"Guard cache initialized: backend={guard_cache.backend}")

# Lifespan context manager for startup and shutdown events
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Application starting up...")
    
    # Initialize the HTTP client on startup
    get_http_client()
    
    # Initialize async components
    if HAS_CACHE and guard_cache:
        await guard_cache.initialize()
    
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


# Create FastAPI app with lifespan
app = FastAPI(
    title="Ollama Proxy with LLM Guard",
    description="Secure proxy for Ollama with LLM Guard integration - Modular Architecture",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


@app.middleware("http")
async def check_ip_whitelist(request: Request, call_next):
    """Middleware to check IP whitelist (nginx only)."""
    client_ip = extract_client_ip(request)
    
    # Check if client IP is whitelisted
    if not ip_whitelist.is_allowed(client_ip):
        logger.warning(f"Rejected request from non-whitelisted IP: {client_ip} {request.method} {request.url.path}")
        return JSONResponse(
            status_code=403,
            content={
                "error": "access_denied",
                "message": "Access denied. Only requests from whitelisted IPs are allowed.",
                "client_ip": client_ip
            }
        )
    
    logger.debug(f"IP whitelist check passed for {client_ip}")
    response = await call_next(request)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests with client IP and path."""
    client_ip = extract_client_ip(request)
    logger.info("Request from %s: %s %s", client_ip, request.method, request.url.path)
    start_ts = time.time()
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_ts) * 1000)
        status_code = locals().get('response', None)
        if status_code and hasattr(status_code, 'status_code'):
            logger.info("Response status: %s (%d ms)", status_code.status_code, duration_ms)
        else:
            logger.info("Response completed (%d ms)", duration_ms)


# Create and register endpoint routers
ollama_router = create_ollama_endpoints(
    config=config,
    guard_manager=guard_manager,
    concurrency_manager=concurrency_manager,
    guard_cache=guard_cache,
    HAS_CACHE=HAS_CACHE
)

openai_router = create_openai_endpoints(
    config=config,
    guard_manager=guard_manager,
    concurrency_manager=concurrency_manager,
    guard_cache=guard_cache,
    HAS_CACHE=HAS_CACHE
)

admin_router = create_admin_endpoints(
    config=config,
    guard_manager=guard_manager,
    ip_whitelist=ip_whitelist,
    concurrency_manager=concurrency_manager,
    guard_cache=guard_cache,
    HAS_CACHE=HAS_CACHE
)

# Include routers in the app
app.include_router(ollama_router, tags=["Ollama"])
app.include_router(openai_router, tags=["OpenAI"])
app.include_router(admin_router, tags=["Admin"])


if __name__ == "__main__":
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
