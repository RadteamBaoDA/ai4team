"""HTTP client management for Ollama Guard Proxy with tuning helpers."""

import importlib
import json
import logging
import os
from typing import Any, AsyncIterator, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# HTTP connection pooling for upstream Ollama
_HTTP_CLIENT: Optional[httpx.AsyncClient] = None
_TRUST_ENV_DEFAULT = False

_DEFAULT_MAX_CONNECTIONS = 200
_DEFAULT_KEEPALIVE_EXPIRY = 45.0
_DEFAULT_READ_TIMEOUT = 1_200.0
_DEFAULT_WRITE_TIMEOUT = 120.0
_DEFAULT_CONNECT_TIMEOUT = 60.0
_DEFAULT_POOL_TIMEOUT = 60.0
_DEFAULT_RETRIES = 2
_STREAM_THRESHOLD = int(os.environ.get("OLLAMA_HTTP_STREAM_THRESHOLD", 512 * 1024))
_JSON_CHUNK_SIZE = max(64 * 1024, int(os.environ.get("OLLAMA_HTTP_JSON_CHUNK_SIZE", 256 * 1024)))


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


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


def _estimate_payload_size(obj: Any, depth: int = 0) -> int:
    if depth > 8 or obj is None:
        return 0
    if isinstance(obj, (bytes, bytearray)):
        return len(obj)
    if isinstance(obj, str):
        return len(obj.encode("utf-8"))
    if isinstance(obj, (int, float)):
        return len(str(obj))
    if isinstance(obj, bool):
        return 4
    if isinstance(obj, dict):
        total = 2
        for key, value in obj.items():
            total += _estimate_payload_size(key, depth + 1)
            total += _estimate_payload_size(value, depth + 1)
        return total
    if isinstance(obj, (list, tuple, set)):
        total = 2
        for item in obj:
            total += _estimate_payload_size(item, depth + 1)
        return total
    return len(str(obj))


def _json_stream(payload: Any, chunk_size: int) -> AsyncIterator[bytes]:
    async def _generator() -> AsyncIterator[bytes]:
        encoder = json.JSONEncoder(separators=(",", ":"), ensure_ascii=False)
        buffer: list[bytes] = []
        size = 0
        for piece in encoder.iterencode(payload):
            data = piece.encode("utf-8")
            buffer.append(data)
            size += len(data)
            if size >= chunk_size:
                yield b"".join(buffer)
                buffer = []
                size = 0
        if buffer:
            yield b"".join(buffer)

    return _generator()


def _prepare_payload(payload: Any) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    if payload is None:
        return {"headers": headers, "json": None, "content": None}
    headers["Content-Type"] = "application/json"
    try:
        estimated = _estimate_payload_size(payload)
    except Exception:
        estimated = 0

    if estimated >= _STREAM_THRESHOLD:
        return {
            "headers": headers,
            "json": None,
            "content": _json_stream(payload, _JSON_CHUNK_SIZE),
        }

    return {"headers": headers, "json": payload, "content": None}


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
        max_connections = _env_int("OLLAMA_HTTP_MAX_CONNECTIONS", max_pool or _DEFAULT_MAX_CONNECTIONS)
        max_keepalive = _env_int("OLLAMA_HTTP_MAX_KEEPALIVE", max_connections)
        keepalive_expiry = _env_float("OLLAMA_HTTP_KEEPALIVE_EXPIRY", _DEFAULT_KEEPALIVE_EXPIRY)

        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
            keepalive_expiry=keepalive_expiry,
        )

        read_timeout = _env_float("OLLAMA_HTTP_READ_TIMEOUT", _DEFAULT_READ_TIMEOUT)
        connect_timeout = _env_float("OLLAMA_HTTP_CONNECT_TIMEOUT", _DEFAULT_CONNECT_TIMEOUT)
        write_timeout = _env_float("OLLAMA_HTTP_WRITE_TIMEOUT", _DEFAULT_WRITE_TIMEOUT)
        pool_timeout = _env_float("OLLAMA_HTTP_POOL_TIMEOUT", _DEFAULT_POOL_TIMEOUT)

        timeout = httpx.Timeout(
            read=read_timeout,
            connect=connect_timeout,
            write=write_timeout,
            pool=pool_timeout,
        )
        
        # Trust environment proxy variables
        trust_env = _env_bool("HTTPX_TRUST_ENV", _TRUST_ENV_DEFAULT)
        
        http2_enabled = True
        try:  # pragma: no cover - best effort capability check
            importlib.import_module("h2")
        except ImportError:
            http2_enabled = False
            logger.info("HTTP/2 support not available (h2 package not installed). Using HTTP/1.1.")
        
        retries = max(0, _env_int("OLLAMA_HTTP_RETRIES", _DEFAULT_RETRIES))
        transport = httpx.AsyncHTTPTransport(retries=retries, http2=http2_enabled)

        _HTTP_CLIENT = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            trust_env=trust_env,
            transport=transport,
            follow_redirects=False,
            verify=True,
        )
        
        http_version = "HTTP/2" if http2_enabled else "HTTP/1.1"
        logger.info(
            "HTTP client initialized (pool=%d, keep-alive=%ss, %s, retries=%d, trust_env=%s)",
            max_connections,
            keepalive_expiry,
            http_version,
            retries,
            trust_env,
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
    payload_plan = _prepare_payload(payload)
    headers = payload_plan["headers"]

    try:
        client = get_http_client()
        if payload is None:
            resp = await client.get(full, headers=headers, timeout=timeout)
            return resp, None

        request_kwargs = {
            "headers": headers,
            "timeout": timeout,
            "json": payload_plan["json"],
            "content": payload_plan["content"],
        }

        if stream:
            return client.stream("POST", full, **request_kwargs), None

        resp = await client.post(full, **request_kwargs)
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
