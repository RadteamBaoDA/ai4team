"""
Utility functions and helpers.

This package contains common utility functions for:
- Request/response processing
- Text extraction and manipulation
- Language support
- Tiktoken offline mode configuration
- Hugging Face offline mode configuration
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
from .tiktoken_cache import (
    setup_tiktoken_offline_mode,
    ensure_tiktoken_cache_dir,
    download_tiktoken_encoding,
    get_tiktoken_cache_info,
    init_tiktoken_with_retry,
)
from .huggingface_cache import (
    setup_huggingface_offline_mode,
    ensure_huggingface_cache_dir,
    download_huggingface_model,
    get_huggingface_cache_info,
    init_huggingface_with_retry,
)
from .device_config import (
    force_cpu_mode,
    force_gpu_mode,
    auto_device_mode,
    get_device_config,
    print_device_config,
    is_cpu_only_mode,
    is_gpu_mode,
    setup_transformers_cpu,
    get_recommended_config,
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
    "setup_tiktoken_offline_mode",
    "ensure_tiktoken_cache_dir",
    "download_tiktoken_encoding",
    "get_tiktoken_cache_info",
    "init_tiktoken_with_retry",
    "setup_huggingface_offline_mode",
    "ensure_huggingface_cache_dir",
    "download_huggingface_model",
    "get_huggingface_cache_info",
    "init_huggingface_with_retry",
    "force_cpu_mode",
    "force_gpu_mode",
    "auto_device_mode",
    "get_device_config",
    "print_device_config",
    "is_cpu_only_mode",
    "is_gpu_mode",
    "setup_transformers_cpu",
    "get_recommended_config",
]