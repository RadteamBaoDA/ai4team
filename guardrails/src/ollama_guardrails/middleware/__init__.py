"""
Middleware components for request/response processing.

This package contains middleware for:
- HTTP client management
- Request/response filtering
"""

from __future__ import annotations

from .http_client import close_http_client, get_http_client

__all__ = [
    "get_http_client", 
    "close_http_client",
]