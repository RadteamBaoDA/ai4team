"""
Utility functions and helpers.

This package contains common utility functions for:
- Request/response processing
- Text extraction and manipulation
- Language support
- Helper functions
"""

from __future__ import annotations

from .language import get_language_message
from .utils import (
    build_ollama_options_from_openai_payload,
    combine_messages_text,
    extract_client_ip,
    extract_model_from_payload,
    extract_prompt_from_completion_payload,
    extract_text_from_payload,
    extract_text_from_response,
)

__all__ = [
    "extract_client_ip",
    "extract_model_from_payload", 
    "extract_text_from_payload",
    "extract_text_from_response",
    "combine_messages_text",
    "build_ollama_options_from_openai_payload",
    "extract_prompt_from_completion_payload",
    "get_language_message",
]