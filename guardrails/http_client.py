"""
HTTP client management for Ollama Guard Proxy.

Provides singleton HTTP client with connection pooling.
"""

import logging
from typing import Optional, Tuple, Any

import httpx

logger = logging.getLogger(__name__)

# HTTP connection pooling for upstream Ollama
_HTTP_CLIENT: Optional[httpx.AsyncClient] = None


def get_http_client(max_pool: int = 100) -> httpx.AsyncClient:
    """Get or create the singleton HTTP client with connection pooling."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        limits = httpx.Limits(max_connections=max_pool, max_keepalive_connections=max_pool)
        # Set a default timeout
        timeout = httpx.Timeout(300.0, connect=60.0)
        _HTTP_CLIENT = httpx.AsyncClient(limits=limits, timeout=timeout)
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
    """Forward a request to the Ollama backend.

    Returns the httpx.Response and an optional error string.
    For streaming, returns the stream context manager that must be used with 'async with'.
    
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
        return None, str(e)
