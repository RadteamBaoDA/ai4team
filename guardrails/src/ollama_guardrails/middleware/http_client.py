"""
HTTP client management for Ollama Guard Proxy.

Provides singleton HTTP client with connection pooling.
"""

import json
import logging
import os
from typing import Optional, Tuple, Any

import httpx

logger = logging.getLogger(__name__)

# HTTP connection pooling for upstream Ollama
_HTTP_CLIENT: Optional[httpx.AsyncClient] = None
_TRUST_ENV_DEFAULT = False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).lower() in {"1", "true", "yes", "on"}


def _summarize_payload(payload: Any, limit: int = 512) -> str:
    """Return a trimmed, log-friendly representation of the payload."""
    if payload is None:
        return "null"
    try:
        serialized = json.dumps(payload)
    except Exception:
        serialized = str(payload)
    serialized = serialized.replace("\n", " ")
    return serialized if len(serialized) <= limit else serialized[:limit] + "(truncated)"


def get_http_client(max_pool: int = 100) -> httpx.AsyncClient:
    """
    Get or create the singleton HTTP client with production-optimized connection pooling.
    
    Configuration:
    - Connection pooling: max_pool connections
    - Keep-alive connections: max_pool
    - Timeout: 300s (read), 60s (connect)
    - Trust env: Respects HTTP_PROXY, HTTPS_PROXY variables
    - HTTP/2 support: Enabled if h2 package is available
    """
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        # Production-optimized limits
        limits = httpx.Limits(
            max_connections=max_pool,
            max_keepalive_connections=max_pool,
            keepalive_expiry=30.0  # Close idle connections after 30s
        )
        
        # Generous timeout for Ollama (large models can be slow)
        timeout = httpx.Timeout(
            300.0,           # Read timeout (for streaming responses)
            connect=60.0,    # Connection timeout
            write=60.0,      # Write timeout
            pool=60.0        # Pool timeout
        )
        
        # Trust environment proxy variables
        trust_env = _env_bool("HTTPX_TRUST_ENV", _TRUST_ENV_DEFAULT)
        
        # Check if HTTP/2 is available (h2 package)
        http2_enabled = True
        try:
            import h2  # noqa: F401
        except ImportError:
            http2_enabled = False
            logger.info("HTTP/2 support not available (h2 package not installed). Using HTTP/1.1.")
        
        # Create client with optimizations
        _HTTP_CLIENT = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            trust_env=trust_env,
            http2=http2_enabled,     # Enable HTTP/2 only if h2 is available
            follow_redirects=False,  # Let app handle redirects
            verify=True,             # Verify SSL certificates
        )
        
        http_version = "HTTP/2" if http2_enabled else "HTTP/1.1"
        logger.info(
            "HTTP client initialized (pool=%d, keep-alive=30s, %s, trust_env=%s)",
            max_pool,
            http_version,
            trust_env
        )
    return _HTTP_CLIENT


async def close_http_client():
    """Close the HTTP client on shutdown."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT:
        await _HTTP_CLIENT.aclose()
        _HTTP_CLIENT = None


async def safe_json(response: httpx.Response) -> Tuple[Optional[dict], Optional[str]]:
    """Safely parse JSON from httpx.Response.

    Returns (data, error_message). Only one of them will be non-None.
    """
    try:
        return response.json(), None
    except Exception as e:
        return None, str(e)


async def forward_request(config, path: str, payload: Any = None, stream: bool = False, timeout: int = 300):
    """
    Forward a request to the Ollama backend with reverse proxy support.

    Returns the httpx.Response and an optional error string.
    For streaming, returns the stream context manager that must be used with 'async with'.
    
    Features:
    - Connection pooling and keep-alive
    - HTTP/2 support for better performance
    - Generous timeout for large model responses
    - Proper error handling and logging
    
    Args:
        config: Configuration object
        path: API path
        payload: Request payload
        stream: Whether to stream the response
        timeout: Request timeout in seconds
    """
    ollama_url = config.get('ollama_url')
    full = f"{ollama_url.rstrip('/')}{path}"
    try:
        client = get_http_client()
        if payload is None:
            resp = await client.get(full, timeout=timeout)
        else:
            if stream:
                # For streaming, return the context manager itself
                return client.stream("POST", full, json=payload, timeout=timeout), None
            resp = await client.post(full, json=payload, timeout=timeout)
        return resp, None
    except httpx.RequestError as e:
        request = getattr(e, "request", None)
        method = request.method if request else ("GET" if payload is None else "POST")
        target_url = str(request.url) if request and request.url else full
        logger.error(
            "HTTPX request error [%s %s] (timeout=%ss): %s | payload=%s",
            method,
            target_url,
            timeout,
            repr(e),
            _summarize_payload(payload),
        )
        return None, str(e)
