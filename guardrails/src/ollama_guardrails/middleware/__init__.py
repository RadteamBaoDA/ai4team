"""
Middleware components for request/response processing.

This package contains middleware for:
- IP whitelisting and access control
- HTTP client management
- Request/response filtering
"""

from __future__ import annotations

from .http_client import close_http_client, get_http_client
from .ip_whitelist import IPWhitelist

__all__ = [
    "IPWhitelist",
    "get_http_client", 
    "close_http_client",
]