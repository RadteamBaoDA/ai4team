"""
title: Guardrails Error Handler Filter
author: ai4team
author_url: https://github.com/RadteamBaoDA/ai4team
funding_url: https://github.com/RadteamBaoDA/ai4team
version: 1.0.2
required_open_webui_version: 0.3.8
description: HTTP 451 content policy error handler - only processes content blocked by guardrails (stream + outlet)
"""

import json
import re
from typing import Optional, Dict, Any, Callable, AsyncGenerator
from pydantic import BaseModel, Field


class Filter:
    """HTTP 451 Content Policy Error Handler - Only processes content blocked by guardrails"""

    class Valves(BaseModel):
        """Configuration settings for the HTTP 451 error handler"""
        enabled: bool = Field(default=True, description="Enable/disable HTTP 451 error handler")
        debug_mode: bool = Field(default=False, description="Enable debug logging for HTTP 451 processing")
        error_format: str = Field(default="markdown", description="Format for error messages (markdown, html, plain)")
        only_451_errors: bool = Field(default=True, description="Only process HTTP 451 content policy violations")
        default_error_msg: str = Field(
            default="⚠️ Content Security Alert: Your request has been blocked by our content safety filters.",
            description="Default error message for HTTP 451 violations"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.error_messages = {
            "scanner_invalid": "���️ **Content Blocked**: Your message violates safety guidelines.",
            "inappropriate": "⚠️ **Inappropriate Content**: Please revise your message.",
            "threat_detected": "��� **Security Alert**: Potential threat detected.",
            "timeout": "⏱️ **Timeout Error**: Request timed out.",
            "generic": self.valves.default_error_msg
        }

    def _safe_get(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safely get attribute from object, handling both dict and string cases."""
        if obj is None:
            return default
        if hasattr(obj, 'get') and callable(getattr(obj, 'get')):
            return obj.get(key, default)
        if isinstance(obj, str):
            try:
                parsed = json.loads(obj)
                if isinstance(parsed, dict):
                    return parsed.get(key, default)
            except (json.JSONDecodeError, ValueError):
                pass
            return default
        try:
            return getattr(obj, key, default)
        except (AttributeError, TypeError):
            return default

    def _is_http_451_error(self, obj: Any) -> bool:
        """Check if the object represents an HTTP 451 error."""
        if obj is None:
            return False
        
        # Check for explicit status_code field
        status_code = self._safe_get(obj, 'status_code')
        if status_code == 451:
            return True
        
        # Check for status field
        status = self._safe_get(obj, 'status')
        if status == 451:
            return True
        
        # Check if it's a string representation of 451 error
        if isinstance(obj, str):
            # Look for "451" in the string content
            if "451" in obj and any(keyword in obj.lower() for keyword in ["unavailable", "legal", "blocked", "content policy"]):
                return True
        
        # Check for error type indicators in headers or error details
        error_type = self._safe_get(obj, 'X-Error-Type') or self._safe_get(obj, 'error_type')
        if error_type == "content_policy_violation":
            return True
        
        return False

    def _detect_error_type(self, message: str) -> str:
        """Detect error type based on message content - optimized for HTTP 451 content policy violations"""
        if not message:
            return "generic"
        message_lower = message.lower()
        
        # Check for specific HTTP 451 / content policy violation indicators
        if any(word in message_lower for word in ["content policy", "safety guidelines", "guardrails", "content blocked"]):
            return "scanner_invalid"
        if any(word in message_lower for word in ["scanner", "invalid", "block", "unsafe", "unavailable for legal reasons"]):
            return "scanner_invalid"
        if "inappropriate" in message_lower:
            return "inappropriate"
        if any(word in message_lower for word in ["threat", "security", "malicious"]):
            return "threat_detected"
        if any(word in message_lower for word in ["timeout", "timed out"]):
            return "timeout"
        return "generic"

    def _format_error_message(self, error_type: str) -> str:
        """Format error message based on configuration"""
        base_message = self.error_messages.get(error_type, self.error_messages["generic"])
        if self.valves.error_format == "html":
            return f'<div style="color: #dc3545; padding: 10px;">{base_message}</div>'
        elif self.valves.error_format == "plain":
            return f"ERROR: {base_message}"
        else:
            return f"> {base_message}"

    def outlet(self, body: dict, __user__: Optional[dict] = None, __event_emitter__: Optional[Callable] = None) -> dict:
        """Process outgoing responses to detect and format error messages - only for HTTP 451 errors"""
        if not self.valves.enabled:
            return body

        try:
            # Only process if this is specifically an HTTP 451 error
            if self._is_http_451_error(body):
                if self.valves.debug_mode and __event_emitter__:
                    __event_emitter__({"type": "status", "data": {"description": "HTTP 451 error detected in outlet"}})
                
                error_msg = self._safe_get(body, 'detail') or self._safe_get(body, 'error') or str(body)
                error_type = self._detect_error_type(str(error_msg))
                formatted_message = self._format_error_message(error_type)
                
                if 'messages' in body and isinstance(body['messages'], list) and body['messages']:
                    body['messages'][-1]['content'] = formatted_message
                elif 'content' in body:
                    body['content'] = formatted_message
                else:
                    body['messages'] = [{"role": "assistant", "content": formatted_message}]
                    
                if self.valves.debug_mode and __event_emitter__:
                    __event_emitter__({"type": "status", "data": {"description": f"Formatted HTTP 451 error as {error_type}"}})
            
        except Exception as e:
            if self.valves.debug_mode and __event_emitter__:
                __event_emitter__({"type": "status", "data": {"description": f"Error processing HTTP 451: {str(e)}"}})

        return body

    async def stream(self, event: dict) -> AsyncGenerator[dict, None]:
        """Process streaming responses to detect and handle errors - only for HTTP 451 errors"""
        if not self.valves.enabled:
            yield event
            return

        try:
            # Check if this is an HTTP 451 error event
            if event.get('type') == 'error':
                data = self._safe_get(event, 'data', event)
                if self._is_http_451_error(data):
                    if self.valves.debug_mode:
                        yield {"type": "status", "data": {"description": "HTTP 451 error detected in stream"}}
                    
                    error_msg = self._safe_get(data, 'error') or self._safe_get(data, 'detail') or str(data)
                    error_type = self._detect_error_type(str(error_msg))
                    formatted_message = self._format_error_message(error_type)
                    
                    yield {
                        "type": "message",
                        "data": {
                            "content": formatted_message,
                            "role": "assistant",
                            "done": True
                        }
                    }
                    return
            
            # Check for HTTP 451 errors in message content
            elif event.get('type') == 'message':
                data = self._safe_get(event, 'data', {})
                content = self._safe_get(data, 'content', '')
                
                # Only process if the content suggests an HTTP 451 error
                if content and "451" in content and any(word in content.lower() for word in ['unavailable', 'blocked', 'legal', 'content policy']):
                    error_type = self._detect_error_type(content)
                    formatted_message = self._format_error_message(error_type)
                    
                    if self.valves.debug_mode:
                        yield {"type": "status", "data": {"description": f"HTTP 451 content detected, formatted as {error_type}"}}
                    
                    yield {
                        "type": "message", 
                        "data": {
                            "content": formatted_message,
                            "role": "assistant",
                            "done": self._safe_get(data, 'done', False)
                        }
                    }
                    return
                    
        except Exception as e:
            if self.valves.debug_mode:
                yield {"type": "status", "data": {"description": f"Stream HTTP 451 processing error: {str(e)}"}}

        # Pass through all non-451 events unchanged
        yield event
