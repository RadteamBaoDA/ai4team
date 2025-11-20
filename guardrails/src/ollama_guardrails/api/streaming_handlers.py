"""
Streaming response handlers for Ollama Guard Proxy.

Contains functions for handling streaming responses with output guard scanning:
- stream_response_with_guard: Ollama format (both /api/generate and /api/chat)
- stream_openai_chat_response: OpenAI chat completions format
- stream_openai_completion_response: OpenAI text completions format
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import httpx

from ..utils.language import LanguageDetector
from ..utils import (
    inline_guard_errors_enabled,
    extract_failed_scanners,
    format_markdown_error,
)

logger = logging.getLogger(__name__)
min_output_length = 50

def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_guard_block_chunk(model_name: str | None,
                             message_content: str,
                             detected_lang: str,
                             guard_payload: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure markdown content has spacing before and after for clean rendering
    if message_content:
        if not message_content.endswith("\n"):
            message_content = message_content + "\n"
        if not message_content.startswith("\n\n\n"):
            # Prepend three blank lines to visually separate error messages
            message_content = "\n\n\n" + message_content

    return {
        "model": model_name,
        "created_at": _now_ts(),
        "message": {
            "role": "assistant",
            "content": message_content,
        },
        "done": True,
        "done_reason": "guard_blocked",
        "guard": guard_payload,
        "error": {
            "type": "content_policy_violation",
            "message": guard_payload.get("message"),
            "language": detected_lang,
            "failed_scanners": guard_payload.get("failed_scanners", []),
        },
    }


async def stream_response_with_guard(response: httpx.Response, guard_manager, config, detected_lang: str = 'en'):
    """Stream response with output scanning.
    
    Handles both /api/generate format (response field) and /api/chat format (message.content field).
    Ensures proper connection cleanup and resource freeing when output is blocked.
    
    Args:
        response: The httpx streaming response
        guard_manager: LLMGuardManager instance for scanning
        config: Configuration object
        detected_lang: Detected language code for error messages
    """
    accumulated_text = ""
    blocked = False
    last_model = None
    
    # Ensure response is an httpx.Response object
    if not isinstance(response, httpx.Response):
        logger.error(f"Invalid response type: {type(response)}. Expected httpx.Response")
        raise TypeError(f"Expected httpx.Response, got {type(response).__name__}")
    
    inline_guard = inline_guard_errors_enabled(config)

    try:
        async for line in response.aiter_lines():
            if not line or not isinstance(line, str):
                if line:
                    logger.debug(f"Skipping non-string line: {type(line)}")
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.debug(f"Skipping non-JSON line: {line[:100]}")
                yield line + '\n'
                continue
            
            # Ensure data is a dictionary
            if not isinstance(data, dict):
                logger.debug(f"Skipping non-dict JSON: {type(data)}")
                yield line + '\n'
                continue
            
            # Track model if present
            if isinstance(data, dict) and data.get('model'):
                last_model = data.get('model')

            # Accumulate text from streaming responses
            # Handle /api/generate format: {"response": "text"}
            if 'response' in data:
                response_text = data.get('response', '')
                if isinstance(response_text, str):
                    accumulated_text += response_text
                else:
                    logger.debug(f"Non-string response field: {type(response_text)}")
            # Handle /api/chat format: {"message": {"content": "text"}}
            elif 'message' in data:
                message = data.get('message')
                if isinstance(message, dict):
                    content = message.get('content', '')
                    if isinstance(content, str):
                        accumulated_text += content
                    else:
                        logger.debug(f"Non-string message.content: {type(content)}")
            
            # Scan accumulated text periodically (every min_output_length chars)
            if len(accumulated_text) > min_output_length and config.get('enable_output_guard', True):
                output_result = await guard_manager.scan_output(accumulated_text)
                if not output_result.get('allowed', True):
                    logger.warning(f"Streaming output blocked by LLM Guard: {output_result}")
                    blocked = True
                    failed_scanners = extract_failed_scanners(output_result)
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                    guard_payload = {
                        "failed_scanners": failed_scanners,
                        "type": "output_blocked",
                        "language": detected_lang,
                        "scan": output_result,
                        "message": error_message,
                    }
                    message_content = format_markdown_error("Response blocked", error_message, failed_scanners) if inline_guard else error_message
                    block_chunk = _build_guard_block_chunk(last_model, message_content, detected_lang, guard_payload)
                    yield (json.dumps(block_chunk) + '\n')
                    
                    # Immediately close connection to stop Ollama generation
                    await response.aclose()
                    logger.info("Connection closed after blocking streaming output")
                    break
                accumulated_text = ""  # Reset for next batch
            
            yield line + '\n'
        
        # Final scan of any remaining text (only if not already blocked)
        if not blocked and accumulated_text and config.get('enable_output_guard', True):
            output_result = await guard_manager.scan_output(accumulated_text)
            if not output_result.get('allowed', True):
                logger.warning(f"Final streaming output blocked: {output_result}")
                blocked = True
                failed_scanners = extract_failed_scanners(output_result)
                error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                guard_payload = {
                    "failed_scanners": failed_scanners,
                    "type": "output_blocked",
                    "language": detected_lang,
                    "scan": output_result,
                    "message": error_message,
                }
                message_content = format_markdown_error("Response blocked", error_message, failed_scanners) if inline_guard else error_message
                block_chunk = _build_guard_block_chunk(last_model, message_content, detected_lang, guard_payload)
                yield (json.dumps(block_chunk) + '\n')
    
    except Exception as e:
        logger.error(f"Error during streaming: {e}", exc_info=True)
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        guard_payload = {
            "failed_scanners": [],
            "type": "server_error",
            "language": detected_lang,
            "message": error_message,
        }
        fallback_chunk = _build_guard_block_chunk(last_model, error_message, detected_lang, guard_payload)
        yield (json.dumps(fallback_chunk) + '\n')
    finally:
        # Ensure connection is always closed
        if not blocked:  # Only close if not already closed in the block above
            try:
                await response.aclose()
                logger.debug("Connection closed after streaming completed")
            except Exception as e:
                logger.debug(f"Connection already closed: {e}")


def format_sse_event(data: Dict[str, Any]) -> bytes:
    """Serialize a chunk for Server-Sent Events streaming."""
    return f"data: {json.dumps(data)}\n\n".encode()


async def stream_openai_chat_response(response: httpx.Response, guard_manager, config, model: str, detected_lang: str = 'en'):
    """Stream OpenAI-compatible chat completions with guard scanning.
    
    Ensures proper connection cleanup and resource freeing when output is blocked.
    
    Args:
        response: The httpx streaming response
        guard_manager: LLMGuardManager instance for scanning
        config: Configuration object
        model: Model name
        detected_lang: Detected language code for error messages
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_ts = int(time.time())
    total_text = ""
    scan_buffer = ""
    sent_role_chunk = False
    block_on_error = config.get('block_on_guard_error', False)
    blocked = False
    inline_guard = inline_guard_errors_enabled(config)

    try:
        async for raw_line in response.aiter_lines():
            if not raw_line:
                continue

            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON streaming chunk: %s", raw_line)
                continue

            if isinstance(data, dict) and data.get('error'):
                error_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "error"
                        }
                    ],
                    "error": data.get('error')
                }
                yield format_sse_event(error_chunk)
                yield b"data: [DONE]\n\n"
                
                # Close connection immediately on error
                await response.aclose()
                logger.info("Connection closed after upstream error")
                return

            if not isinstance(data, dict):
                logger.debug(f"Skipping non-dict response in OpenAI chat: {type(data)}")
                continue
            
            message = data.get('message', {})
            if not isinstance(message, dict):
                logger.debug(f"Invalid message type in OpenAI chat: {type(message)}")
                continue
            
            delta_text = message.get('content', '')
            if not isinstance(delta_text, str):
                logger.debug(f"Invalid content type in OpenAI chat: {type(delta_text)}")
                delta_text = str(delta_text) if delta_text else ''

            if delta_text:
                if not sent_role_chunk:
                    role_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "role": "assistant"
                                },
                                "finish_reason": None
                            }
                        ]
                    }
                    yield format_sse_event(role_chunk)
                    sent_role_chunk = True

                total_text += delta_text
                scan_buffer += delta_text

                if config.get('enable_output_guard', True) and len(scan_buffer) >= min_output_length:
                    scan_result = await guard_manager.scan_output(scan_buffer, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Streaming OpenAI output blocked by LLM Guard: %s", scan_result)
                        blocked = True
                        failed_scanners = extract_failed_scanners(scan_result)
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        markdown_body = format_markdown_error("Content policy violation", error_message, failed_scanners)

                        if inline_guard:
                            block_chunk = {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created_ts,
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "content": markdown_body
                                        },
                                        "finish_reason": "content_filter"
                                    }
                                ],
                                "guard": scan_result
                            }
                        else:
                            block_chunk = {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created_ts,
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": "content_filter"
                                    }
                                ],
                                "error": {
                                    "message": error_message,
                                    "type": "content_policy_violation",
                                    "code": "output_blocked",
                                    "failed_scanners": failed_scanners
                                }
                            }
                        yield format_sse_event(block_chunk)
                        yield b"data: [DONE]\n\n"
                        
                        # Immediately close connection to stop Ollama generation
                        await response.aclose()
                        logger.info("Connection closed after blocking OpenAI chat output")
                        return
                    scan_buffer = ""

                content_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": delta_text
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield format_sse_event(content_chunk)

            if data.get('done'):
                usage = {
                    "prompt_tokens": int(data.get('prompt_eval_count', 0) or 0),
                    "completion_tokens": int(data.get('eval_count', 0) or 0),
                }
                usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

                remaining_text = scan_buffer or (total_text if len(total_text) <= min_output_length else "")
                if config.get('enable_output_guard', True) and remaining_text:
                    scan_result = await guard_manager.scan_output(remaining_text, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Final OpenAI streaming output blocked: %s", scan_result)
                        blocked = True
                        failed_scanners = extract_failed_scanners(scan_result)
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        markdown_body = format_markdown_error("Content policy violation", error_message, failed_scanners)
                        delta_content = markdown_body if inline_guard else error_message
                        block_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "content": delta_content
                                    },
                                    "finish_reason": "content_filter"
                                }
                            ],
                            "guard": scan_result,
                            "usage": usage
                        }
                        yield format_sse_event(block_chunk)
                        yield b"data: [DONE]\n\n"
                        
                        # Close connection after final block
                        await response.aclose()
                        logger.info("Connection closed after blocking final OpenAI chat output")
                        return

                final_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": usage
                }
                yield format_sse_event(final_chunk)
                yield b"data: [DONE]\n\n"
                return

    except Exception as exc:
        logger.error("Error during OpenAI streaming: %s", exc)
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        error_chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": error_message
                    },
                    "finish_reason": "error"
                }
            ]
        }
        yield format_sse_event(error_chunk)
        yield b"data: [DONE]\n\n"
    finally:
        # Ensure connection is always closed
        if not blocked:  # Only close if not already closed above
            try:
                await response.aclose()
                logger.debug("Connection closed after OpenAI chat streaming completed")
            except Exception as e:
                logger.debug(f"Connection already closed: {e}")


async def stream_openai_completion_response(response: httpx.Response, guard_manager, config, model: str, detected_lang: str = 'en'):
    """Stream OpenAI-compatible text completions with guard scanning.
    
    Ensures proper connection cleanup and resource freeing when output is blocked.
    
    Args:
        response: The httpx streaming response
        guard_manager: LLMGuardManager instance for scanning
        config: Configuration object
        model: Model name
        detected_lang: Detected language code for error messages
    """
    completion_id = f"cmpl-{uuid.uuid4().hex}"
    created_ts = int(time.time())
    total_text = ""
    scan_buffer = ""
    block_on_error = config.get('block_on_guard_error', False)
    blocked = False
    inline_guard = inline_guard_errors_enabled(config)

    try:
        async for raw_line in response.aiter_lines():
            if not raw_line:
                continue

            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON completion chunk: %s", raw_line)
                continue

            if isinstance(data, dict) and data.get('error'):
                error_chunk = {
                    "id": completion_id,
                    "object": "text_completion",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "text": "",
                            "logprobs": None,
                            "finish_reason": "error"
                        }
                    ],
                    "error": data['error']
                }
                yield format_sse_event(error_chunk)
                yield b"data: [DONE]\n\n"
                
                # Close connection immediately on error
                await response.aclose()
                logger.info("Connection closed after upstream completion error")
                return

            delta_text = data.get('response', '') if isinstance(data, dict) else ''

            if delta_text:
                total_text += delta_text
                scan_buffer += delta_text

                if config.get('enable_output_guard', True) and len(scan_buffer) >= min_output_length:
                    scan_result = await guard_manager.scan_output(scan_buffer, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Streaming completion output blocked: %s", scan_result)
                        blocked = True
                        failed_scanners = extract_failed_scanners(scan_result)
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        markdown_body = format_markdown_error("Content policy violation", error_message, failed_scanners)
                        block_text = markdown_body if inline_guard else error_message
                        block_chunk = {
                            "id": completion_id,
                            "object": "text_completion",
                            "created": created_ts,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "text": block_text,
                                    "logprobs": None,
                                    "finish_reason": "content_filter"
                                }
                            ],
                            "guard": scan_result
                        }
                        yield format_sse_event(block_chunk)
                        yield b"data: [DONE]\n\n"
                        
                        # Immediately close connection to stop Ollama generation
                        await response.aclose()
                        logger.info("Connection closed after blocking completion output")
                        return
                    scan_buffer = ""

                chunk = {
                    "id": completion_id,
                    "object": "text_completion",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "text": delta_text,
                            "logprobs": None,
                            "finish_reason": None
                        }
                    ]
                }
                yield format_sse_event(chunk)

            if data.get('done'):
                usage = {
                    "prompt_tokens": int(data.get('prompt_eval_count', 0) or 0),
                    "completion_tokens": int(data.get('eval_count', 0) or 0)
                }
                usage['total_tokens'] = usage['prompt_tokens'] + usage['completion_tokens']

                remaining_text = scan_buffer or (total_text if len(total_text) <= min_output_length else "")
                if config.get('enable_output_guard', True) and remaining_text:
                    scan_result = await guard_manager.scan_output(remaining_text, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Final completion output blocked: %s", scan_result)
                        blocked = True
                        failed_scanners = extract_failed_scanners(scan_result)
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        markdown_body = format_markdown_error("Content policy violation", error_message, failed_scanners)
                        block_text = markdown_body if inline_guard else error_message
                        block_chunk = {
                            "id": completion_id,
                            "object": "text_completion",
                            "created": created_ts,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "text": block_text,
                                    "logprobs": None,
                                    "finish_reason": "content_filter"
                                }
                            ],
                            "guard": scan_result,
                            "usage": usage
                        }
                        yield format_sse_event(block_chunk)
                        yield b"data: [DONE]\n\n"
                        
                        # Close connection after final block
                        await response.aclose()
                        logger.info("Connection closed after blocking final completion output")
                        return

                final_chunk = {
                    "id": completion_id,
                    "object": "text_completion",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "text": "",
                            "logprobs": None,
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": usage
                }
                yield format_sse_event(final_chunk)
                yield b"data: [DONE]\n\n"
                return

    except Exception as exc:
        logger.error("Error during OpenAI completion streaming: %s", exc)
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        error_chunk = {
            "id": f"cmpl-{uuid.uuid4().hex}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "text": error_message,
                    "logprobs": None,
                    "finish_reason": "error"
                }
            ]
        }
        yield format_sse_event(error_chunk)
        yield b"data: [DONE]\n\n"
    finally:
        # Ensure connection is always closed
        if not blocked:  # Only close if not already closed above
            try:
                await response.aclose()
                logger.debug("Connection closed after completion streaming completed")
            except Exception as e:
                logger.debug(f"Connection already closed: {e}")


def create_streaming_handlers(config, guard_manager):
    """
    Factory function to create streaming handlers with dependency injection.
    
    Returns a function that can be used for streaming responses.
    
    Args:
        config: Configuration object
        guard_manager: LLMGuardManager instance
        
    Returns:
        Streaming handler function
    """
    async def stream_with_guard(response: httpx.Response, detected_lang: str = 'en'):
        """Wrapper function that injects dependencies into stream_response_with_guard."""
        async for chunk in stream_response_with_guard(response, guard_manager, config, detected_lang):
            yield chunk
    
    return stream_with_guard
