"""
Utility functions for Ollama Guard Proxy.

Contains helper functions for request/response processing:
- Text extraction from payloads and responses
- Client IP extraction
- Message text combining
- OpenAI to Ollama parameter mapping
"""

import logging
from typing import Dict, Any, Iterable, List, Optional


def extract_client_ip(request) -> str:
    """Extract client IP from request, preferring X-Forwarded-For then X-Real-IP.

    Returns a string IP (or '0.0.0.0' if unknown).
    """
    xfwd = request.headers.get('x-forwarded-for')
    if xfwd:
        # X-Forwarded-For may contain a list of IPs: client, proxy1, proxy2
        return xfwd.split(',')[0].strip()

    xreal = request.headers.get('x-real-ip')
    if xreal:
        return xreal.strip()

    return request.client.host if request.client else '0.0.0.0'


def extract_model_from_payload(payload: Dict[str, Any]) -> str:
    """Extract model name from payload."""
    if isinstance(payload, dict):
        model = payload.get('model', 'default')
        return str(model) if model else 'default'
    return 'default'


def extract_text_from_payload(payload: Dict[str, Any]) -> str:
    """Extract text from Ollama request payload."""
    if isinstance(payload, dict):
        if 'prompt' in payload:
            return payload['prompt']
        if 'input' in payload:
            return payload['input']
    return str(payload)


def extract_text_from_response(data: Any) -> str:
    """Extract text from Ollama response."""
    if isinstance(data, dict):
        if 'response' in data:
            return data['response']
        if 'text' in data:
            return data['text']
        if 'output' in data:
            return data['output']
        # Combine all string values
        text = ' '.join([str(v) for v in data.values() if isinstance(v, str)])
        if text:
            return text
    return str(data)


def combine_messages_text(
    messages: List[Dict[str, Any]],
    roles: Optional[Iterable[str]] = None,
    latest_only: bool = False,
) -> str:
    """Combine selected message contents into a single string for guard scanning.

    Args:
        messages: List of chat messages.
        roles: Optional iterable of roles to include (case-insensitive).
        latest_only: When True, return only the most recent matching message's content.
    """
    if not isinstance(messages, list):
        return ""

    normalized_roles = None
    if roles is not None:
        normalized_roles = {role.lower() for role in roles}

    def _matches(msg: Dict[str, Any]) -> bool:
        if not isinstance(msg, dict):
            return False
        if not normalized_roles:
            return True
        role = str(msg.get('role', '')).lower()
        return role in normalized_roles

    if latest_only:
        for msg in reversed(messages):
            if not _matches(msg):
                continue
            content = msg.get('content')
            if isinstance(content, str) and content.strip():
                return content
        return ""

    combined: List[str] = []
    for msg in messages:
        if not _matches(msg):
            continue
        content = msg.get('content')
        if isinstance(content, str) and content.strip():
            combined.append(content)
    return "\n".join(combined)


def build_ollama_options_from_openai_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map relevant OpenAI parameters to Ollama options."""
    if not isinstance(payload, dict):
        return {}

    option_keys = {
        'temperature': 'temperature',
        'top_p': 'top_p',
        'top_k': 'top_k',
        'repeat_penalty': 'repeat_penalty',
        'num_ctx': 'num_ctx',
        'seed': 'seed',
        'stop': 'stop',
        'presence_penalty': 'presence_penalty',
        'frequency_penalty': 'frequency_penalty',
    }

    options: Dict[str, Any] = dict(payload.get('options', {})) if isinstance(payload.get('options'), dict) else {}

    for openai_key, ollama_key in option_keys.items():
        if openai_key in payload and payload[openai_key] is not None:
            options[ollama_key] = payload[openai_key]

    max_tokens = payload.get('max_tokens')
    if isinstance(max_tokens, int) and max_tokens > 0:
        options['num_predict'] = max_tokens

    return options


def extract_prompt_from_completion_payload(payload: Dict[str, Any]) -> str:
    """Extract prompt text for OpenAI completion payloads."""
    prompt = payload.get('prompt')
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        return "\n".join(str(item) for item in prompt if isinstance(item, (str, int, float)))
    return str(prompt) if prompt is not None else ""

