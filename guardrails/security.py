"""
Security hardening utilities for Ollama Guard Proxy
Includes rate limiting, input validation, and security headers
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
import asyncio
from functools import wraps

from fastapi import Request, HTTPException
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter with per-IP tracking."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute per IP
            requests_per_hour: Max requests per hour per IP
            burst_size: Allow burst of requests
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # Per-IP request tracking
        self.minute_buckets: Dict[str, deque] = defaultdict(deque)
        self.hour_buckets: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
        
        logger.info(
            f'Rate limiter initialized: {requests_per_minute}/min, '
            f'{requests_per_hour}/hour, burst={burst_size}'
        )
    
    def _cleanup_old_requests(self, bucket: deque, window_seconds: int) -> None:
        """Remove requests older than the time window."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        while bucket and bucket[0] < cutoff_time:
            bucket.popleft()
    
    async def is_allowed(self, client_ip: str) -> tuple[bool, Optional[str]]:
        """
        Check if request from client IP is allowed.
        
        Returns:
            (allowed, reason) - reason is set if not allowed
        """
        current_time = time.time()
        
        async with self.lock:
            # Get buckets for this IP
            minute_bucket = self.minute_buckets[client_ip]
            hour_bucket = self.hour_buckets[client_ip]
            
            # Cleanup old requests
            self._cleanup_old_requests(minute_bucket, 60)
            self._cleanup_old_requests(hour_bucket, 3600)
            
            # Check minute limit
            if len(minute_bucket) >= self.requests_per_minute:
                return False, f'Rate limit exceeded: {self.requests_per_minute} requests per minute'
            
            # Check hour limit
            if len(hour_bucket) >= self.requests_per_hour:
                return False, f'Rate limit exceeded: {self.requests_per_hour} requests per hour'
            
            # Check burst limit
            recent_requests = sum(1 for t in minute_bucket if current_time - t < 1.0)
            if recent_requests >= self.burst_size:
                return False, f'Burst limit exceeded: {self.burst_size} requests per second'
            
            # Add current request
            minute_bucket.append(current_time)
            hour_bucket.append(current_time)
            
            return True, None
    
    async def get_stats(self, client_ip: str) -> Dict[str, Any]:
        """Get rate limit stats for a client IP."""
        async with self.lock:
            minute_bucket = self.minute_buckets.get(client_ip, deque())
            hour_bucket = self.hour_buckets.get(client_ip, deque())
            
            self._cleanup_old_requests(minute_bucket, 60)
            self._cleanup_old_requests(hour_bucket, 3600)
            
            return {
                'requests_last_minute': len(minute_bucket),
                'requests_last_hour': len(hour_bucket),
                'minute_limit': self.requests_per_minute,
                'hour_limit': self.requests_per_hour,
                'burst_limit': self.burst_size,
            }
    
    async def reset_ip(self, client_ip: str) -> None:
        """Reset rate limits for a specific IP."""
        async with self.lock:
            if client_ip in self.minute_buckets:
                del self.minute_buckets[client_ip]
            if client_ip in self.hour_buckets:
                del self.hour_buckets[client_ip]
            logger.info(f'Reset rate limits for IP: {client_ip}')


class InputValidator:
    """Validate and sanitize input requests."""
    
    # Maximum sizes to prevent DoS
    MAX_PROMPT_LENGTH = 100000  # 100KB
    MAX_MESSAGE_COUNT = 100
    MAX_MESSAGE_LENGTH = 50000  # 50KB
    
    # Dangerous patterns
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS attempts
        r'javascript:',                 # JavaScript protocol
        r'on\w+\s*=',                   # Event handlers
        r'eval\s*\(',                   # Eval attempts
        r'__import__',                  # Python imports
        r'subprocess',                  # Subprocess execution
        r'os\.system',                  # OS commands
    ]
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> tuple[bool, Optional[str]]:
        """Validate prompt input."""
        if not isinstance(prompt, str):
            return False, 'Prompt must be a string'
        
        if not prompt.strip():
            return False, 'Prompt cannot be empty'
        
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            return False, f'Prompt exceeds maximum length of {cls.MAX_PROMPT_LENGTH} characters'
        
        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f'Suspicious pattern detected in prompt: {pattern}')
                # Don't block, but log it - let LLM Guard handle the actual filtering
        
        return True, None
    
    @classmethod
    def validate_messages(cls, messages: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """Validate chat messages."""
        if not isinstance(messages, list):
            return False, 'Messages must be a list'
        
        if not messages:
            return False, 'Messages list cannot be empty'
        
        if len(messages) > cls.MAX_MESSAGE_COUNT:
            return False, f'Too many messages: maximum {cls.MAX_MESSAGE_COUNT}'
        
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return False, f'Message {idx} must be a dictionary'
            
            if 'content' not in msg:
                return False, f'Message {idx} missing "content" field'
            
            content = msg['content']
            if not isinstance(content, str):
                return False, f'Message {idx} content must be a string'
            
            if len(content) > cls.MAX_MESSAGE_LENGTH:
                return False, f'Message {idx} exceeds maximum length of {cls.MAX_MESSAGE_LENGTH}'
        
        return True, None
    
    @classmethod
    def validate_model_name(cls, model: str) -> tuple[bool, Optional[str]]:
        """Validate model name to prevent path traversal."""
        if not isinstance(model, str):
            return False, 'Model must be a string'
        
        if not model.strip():
            return False, 'Model name cannot be empty'
        
        # Check for path traversal attempts
        if '..' in model or '/' in model or '\\' in model:
            return False, 'Invalid model name: path traversal detected'
        
        # Check for suspicious characters
        if not re.match(r'^[a-zA-Z0-9._:-]+$', model):
            return False, 'Invalid model name: contains illegal characters'
        
        return True, None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server identification
        if 'Server' in response.headers:
            response.headers['Server'] = 'Ollama-Guard-Proxy'
        
        return response


def rate_limit_middleware(rate_limiter: RateLimiter):
    """Create rate limiting middleware."""
    
    async def middleware(request: Request, call_next):
        # Extract client IP
        client_ip = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
        if not client_ip:
            client_ip = request.headers.get('x-real-ip', '')
        if not client_ip:
            client_ip = request.client.host if request.client else '0.0.0.0'
        
        # Check rate limit
        allowed, reason = await rate_limiter.is_allowed(client_ip)
        
        if not allowed:
            logger.warning(f'Rate limit exceeded for IP {client_ip}: {reason}')
            raise HTTPException(
                status_code=429,
                detail={
                    'error': 'rate_limit_exceeded',
                    'message': reason,
                    'client_ip': client_ip
                }
            )
        
        # Add rate limit info to response headers
        response = await call_next(request)
        stats = await rate_limiter.get_stats(client_ip)
        
        response.headers['X-RateLimit-Limit-Minute'] = str(rate_limiter.requests_per_minute)
        response.headers['X-RateLimit-Remaining-Minute'] = str(
            rate_limiter.requests_per_minute - stats['requests_last_minute']
        )
        response.headers['X-RateLimit-Limit-Hour'] = str(rate_limiter.requests_per_hour)
        response.headers['X-RateLimit-Remaining-Hour'] = str(
            rate_limiter.requests_per_hour - stats['requests_last_hour']
        )
        
        return response
    
    return middleware
