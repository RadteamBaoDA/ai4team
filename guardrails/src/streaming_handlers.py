"""
Streaming response handlers for Ollama Guard Proxy.

Contains functions for handling streaming responses with output guard scanning:
- stream_response_with_guard: Ollama format (both /api/generate and /api/chat)
- stream_openai_chat_response: OpenAI chat completions format
- stream_openai_completion_response: OpenAI text completions format
"""

import json
import logging
import time
import uuid
from typing import Dict, Any

import httpx

from .language import LanguageDetector

logger = logging.getLogger(__name__)


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
    
    try:
        async for line in response.aiter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                yield line + '\n'
                continue
            
            # Accumulate text from streaming responses
            # Handle /api/generate format: {"response": "text"}
            if 'response' in data:
                accumulated_text += data['response']
            # Handle /api/chat format: {"message": {"content": "text"}}
            elif 'message' in data and isinstance(data['message'], dict):
                content = data['message'].get('content', '')
                if content:
                    accumulated_text += content
            
            # Scan accumulated text periodically (every 500 chars)
            if len(accumulated_text) > 500 and config.get('enable_output_guard', True):
                output_result = await guard_manager.scan_output(accumulated_text)
                if not output_result['allowed']:
                    logger.warning(f"Streaming output blocked by LLM Guard: {output_result}")
                    blocked = True
                    
                    # Extract failed scanners
                    failed_scanners = []
                    for scanner_name, info in output_result.get('scanners', {}).items():
                        if not info.get('passed', True):
                            failed_scanners.append({
                                "scanner": scanner_name,
                                "reason": info.get('reason', 'Content policy violation'),
                                "score": info.get('score')
                            })
                    
                    # Get localized error message
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                    
                    # Send error as last chunk
                    error_chunk = {
                        "error": "content_policy_violation",
                        "type": "output_blocked",
                        "message": error_message,
                        "language": detected_lang,
                        "failed_scanners": failed_scanners,
                        "done": True
                    }
                    yield (json.dumps(error_chunk) + '\n')
                    
                    # Immediately close connection to stop Ollama generation
                    await response.aclose()
                    logger.info("Connection closed after blocking streaming output")
                    break
                accumulated_text = ""  # Reset for next batch
            
            yield line + '\n'
        
        # Final scan of any remaining text (only if not already blocked)
        if not blocked and accumulated_text and config.get('enable_output_guard', True):
            output_result = await guard_manager.scan_output(accumulated_text)
            if not output_result['allowed']:
                logger.warning(f"Final streaming output blocked: {output_result}")
                blocked = True
    
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        yield (json.dumps({"error": str(e), "message": error_message}) + '\n')
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
                    "error": data['error']
                }
                yield format_sse_event(error_chunk)
                yield b"data: [DONE]\n\n"
                
                # Close connection immediately on error
                await response.aclose()
                logger.info("Connection closed after upstream error")
                return

            message = data.get('message', {}) if isinstance(data, dict) else {}
            delta_text = message.get('content', '') if isinstance(message, dict) else ''

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

                if config.get('enable_output_guard', True) and len(scan_buffer) >= 500:
                    scan_result = await guard_manager.scan_output(scan_buffer, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Streaming OpenAI output blocked by LLM Guard: %s", scan_result)
                        blocked = True
                        
                        # Extract failed scanners
                        failed_scanners = []
                        for scanner_name, info in scan_result.get('scanners', {}).items():
                            if not info.get('passed', True):
                                failed_scanners.append({
                                    "scanner": scanner_name,
                                    "reason": info.get('reason', 'Content policy violation')
                                })
                        
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
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

                remaining_text = scan_buffer or (total_text if len(total_text) <= 500 else "")
                if config.get('enable_output_guard', True) and remaining_text:
                    scan_result = await guard_manager.scan_output(remaining_text, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Final OpenAI streaming output blocked: %s", scan_result)
                        blocked = True
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        block_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "content": error_message
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

                if config.get('enable_output_guard', True) and len(scan_buffer) >= 500:
                    scan_result = await guard_manager.scan_output(scan_buffer, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Streaming completion output blocked: %s", scan_result)
                        blocked = True
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        block_chunk = {
                            "id": completion_id,
                            "object": "text_completion",
                            "created": created_ts,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "text": error_message,
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

                remaining_text = scan_buffer or (total_text if len(total_text) <= 500 else "")
                if config.get('enable_output_guard', True) and remaining_text:
                    scan_result = await guard_manager.scan_output(remaining_text, block_on_error=block_on_error)
                    if not scan_result.get('allowed', True):
                        logger.warning("Final completion output blocked: %s", scan_result)
                        blocked = True
                        error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                        block_chunk = {
                            "id": completion_id,
                            "object": "text_completion",
                            "created": created_ts,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "text": error_message,
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
