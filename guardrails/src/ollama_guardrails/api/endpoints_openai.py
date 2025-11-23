"""
OpenAI-compatible API endpoints for the guard proxy.

This module contains OpenAI API-compatible endpoints:
- Chat completions (/v1/chat/completions)
- Text completions (/v1/completions)
- Embeddings (/v1/embeddings)
- Models (/v1/models)
"""

import json
import logging
import time
import uuid
import asyncio
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..middleware.http_client import forward_request, safe_json, get_http_client
from ..utils import (
    extract_prompt_from_completion_payload, 
    extract_text_from_response,
    combine_messages_text,
    build_ollama_options_from_openai_payload,
    inline_guard_errors_enabled,
    extract_failed_scanners,
    format_markdown_error,
)
from ..utils.language import LanguageDetector

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def create_openai_endpoints(config, guard_manager, concurrency_manager):
    """
    Create OpenAI-compatible endpoints with dependency injection.
    
    Args:
        config: Configuration object
        guard_manager: LLM Guard manager instance
        concurrency_manager: Concurrency manager instance
    """
    
    # Import streaming handlers
    from .streaming_handlers import (
        stream_openai_chat_response,
        stream_openai_completion_response,
        format_sse_event,
    )

    def _zero_usage() -> Dict[str, int]:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _inline_chat_guard_response(model: str, markdown_message: str, is_stream: bool, guard_payload: Dict[str, Any]):
        usage = guard_payload.get("usage") if guard_payload else None
        if not usage:
            usage = _zero_usage()

        if is_stream:
            async def _chat_error_stream():
                completion_id = f"chatcmpl-{uuid.uuid4().hex}"
                created_ts = int(time.time())
                role_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None,
                        }
                    ],
                }
                yield format_sse_event(role_chunk)

                content_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": markdown_message},
                            "finish_reason": "content_filter",
                        }
                    ],
                    "guard": guard_payload,
                }
                yield format_sse_event(content_chunk)
                yield b"data: [DONE]\n\n"

            return StreamingResponse(_chat_error_stream(), media_type="text/event-stream")

        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created_ts = int(time.time())
        result = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created_ts,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": markdown_message},
                    "finish_reason": "content_filter",
                }
            ],
            "usage": usage,
        }
        if guard_payload:
            result["guard"] = guard_payload
        return JSONResponse(status_code=200, content=result)

    def _inline_completion_guard_response(model: str, markdown_message: str, is_stream: bool, guard_payload: Dict[str, Any]):
        usage = guard_payload.get("usage") if guard_payload else None
        if not usage:
            usage = _zero_usage()

        if is_stream:
            async def _completion_error_stream():
                completion_id = f"cmpl-{uuid.uuid4().hex}"
                created_ts = int(time.time())
                chunk = {
                    "id": completion_id,
                    "object": "text_completion",
                    "created": created_ts,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "text": markdown_message,
                            "logprobs": None,
                            "finish_reason": "content_filter",
                        }
                    ],
                    "guard": guard_payload,
                }
                yield format_sse_event(chunk)
                yield b"data: [DONE]\n\n"

            return StreamingResponse(_completion_error_stream(), media_type="text/event-stream")

        completion_id = f"cmpl-{uuid.uuid4().hex}"
        created_ts = int(time.time())
        result = {
            "id": completion_id,
            "object": "text_completion",
            "created": created_ts,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "text": markdown_message,
                    "logprobs": None,
                    "finish_reason": "content_filter",
                }
            ],
            "usage": usage,
        }
        if guard_payload:
            result["guard"] = guard_payload
        return JSONResponse(status_code=200, content=result)

    
    @router.post("/v1/chat/completions")
    async def openai_chat_completions(request: Request):
        """OpenAI-compatible chat completions endpoint with guard integration."""
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("Invalid OpenAI request JSON: %s", exc)
            raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(exc)})
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Incoming /v1/chat/completions payload: %s", payload)

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail={"error": "invalid_payload", "message": "Expected JSON object."})

        messages = payload.get('messages')
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail={"error": "invalid_messages", "message": "messages must be a non-empty list."})

        model = payload.get('model')
        if not isinstance(model, str) or not model.strip():
            raise HTTPException(status_code=400, detail={"error": "invalid_model", "message": "model is required."})

        is_stream = bool(payload.get('stream', False))
        inline_guard = inline_guard_errors_enabled(config)

        # Generate request ID
        request_id = f"oai-chat-{uuid.uuid4().hex[:8]}"
        
        prompt_text = combine_messages_text(messages, roles=('user',), latest_only=True)
        detected_lang = LanguageDetector.detect_language(prompt_text)

        # Define processing coroutine
        async def process_openai_chat():
            if config.get('enable_input_guard', True) and prompt_text:
                input_result = await guard_manager.scan_input(
                    prompt_text,
                    block_on_error=config.get('block_on_guard_error', False)
                )
                if not input_result.get('allowed', True):
                    logger.warning("OpenAI input blocked by LLM Guard: %s", input_result)

                    failed_scanners = extract_failed_scanners(input_result)
                    reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners]) if failed_scanners else None
                    error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)

                    if inline_guard:
                        markdown_message = format_markdown_error("Input blocked", error_message, failed_scanners)
                        guard_payload = {
                            "failed_scanners": failed_scanners,
                            "type": "input_blocked",
                            "language": detected_lang,
                            "usage": _zero_usage(),
                        }
                        return _inline_chat_guard_response(model, markdown_message, is_stream, guard_payload)

                    raise HTTPException(
                        status_code=451,
                        detail=error_message,
                        headers={
                            "X-Error-Type": "content_policy_violation",
                            "X-Block-Type": "input_blocked",
                            "X-Language": detected_lang,
                            "X-Failed-Scanners": json.dumps(failed_scanners)
                        }
                    )

            ollama_payload: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": bool(payload.get('stream', False))
            }

            options = build_ollama_options_from_openai_payload(payload)
            if options:
                ollama_payload['options'] = options

            if isinstance(payload.get('tools'), list):
                ollama_payload['tools'] = payload['tools']
            if isinstance(payload.get('functions'), list):
                ollama_payload['functions'] = payload['functions']

            ollama_url = config.get('ollama_url')
            url = f"{ollama_url.rstrip('/')}/api/chat"
            is_stream = bool(payload.get('stream'))

            try:
                client = get_http_client()
                timeout = config.get('openai_timeout', 300)
                if is_stream:
                    # For streaming, pass the stream directly to the handler
                    async def stream_wrapper():
                        async with client.stream("POST", url, json=ollama_payload, timeout=timeout) as response:
                            if response.status_code != 200:
                                logger.error("OpenAI upstream returned %s", response.status_code)
                                try:
                                    upstream_detail = response.json()
                                except Exception:
                                    upstream_detail = {"error": response.text}
                                raise HTTPException(status_code=response.status_code, detail=upstream_detail)
                            
                            async for chunk in stream_openai_chat_response(response, guard_manager, config, model, detected_lang):
                                yield chunk
                    
                    return StreamingResponse(
                        stream_wrapper(),
                        media_type="text/event-stream"
                    )
                else:
                    response = await client.post(url, json=ollama_payload, timeout=timeout)
                    
                    if response.status_code != 200:
                        logger.error("OpenAI upstream returned %s", response.status_code)
                        try:
                            upstream_detail = response.json()
                        except Exception:
                            upstream_detail = {"error": response.text}
                        raise HTTPException(status_code=response.status_code, detail=upstream_detail)
            except Exception as exc:
                logger.error("OpenAI upstream error: %s", exc)
                error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
                raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message})

            if is_stream:
                # This shouldn't be reached due to early return above
                pass

            try:
                data = response.json()
            except Exception as exc:
                logger.error("Failed to parse OpenAI upstream response: %s", exc)
                error_message = LanguageDetector.get_error_message('server_error', detected_lang)
                # Close connection before raising exception
                try:
                    await response.aclose()
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})

            usage = _zero_usage()
            output_text = ""
            if isinstance(data, dict):
                usage = {
                    "prompt_tokens": int(data.get('prompt_eval_count', 0) or 0),
                    "completion_tokens": int(data.get('eval_count', 0) or 0)
                }
                usage['total_tokens'] = usage['prompt_tokens'] + usage['completion_tokens']

                message = data.get('message')
                if isinstance(message, dict):
                    output_text = message.get('content', '')

            if config.get('enable_output_guard', True) and output_text:
                output_result = await guard_manager.scan_output(
                    output_text,
                    prompt=prompt_text,
                    block_on_error=config.get('block_on_guard_error', False)
                )

                if not output_result.get('allowed', True):
                    logger.warning("OpenAI output blocked by LLM Guard: %s", output_result)

                    # Explicitly close response to free resources immediately
                    try:
                        await response.aclose()
                        logger.info("Connection closed after blocking OpenAI non-streaming output")
                    except Exception as e:
                        logger.debug(f"Error closing connection: {e}")

                    failed_scanners = extract_failed_scanners(output_result)
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)

                    guard_payload = {
                        "failed_scanners": failed_scanners,
                        "type": "output_blocked",
                        "language": detected_lang,
                        "usage": usage,
                    }

                    if inline_guard:
                        markdown_message = format_markdown_error("Response blocked", error_message, failed_scanners)
                        return _inline_chat_guard_response(model, markdown_message, False, guard_payload)

                    raise HTTPException(
                        status_code=451,
                        detail=error_message,
                        headers={
                            "X-Error-Type": "content_policy_violation",
                            "X-Block-Type": "output_blocked",
                            "X-Language": detected_lang,
                            "X-Failed-Scanners": json.dumps(failed_scanners)
                        }
                    )
            
            # Close connection after successful processing
            try:
                await response.aclose()
                logger.debug("Connection closed after OpenAI chat processing")
            except Exception:
                pass

            completion_id = f"chatcmpl-{uuid.uuid4().hex}"
            created_ts = int(time.time())

            result = {
                "id": completion_id,
                "object": "chat.completion",
                "created": created_ts,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": output_text
                        },
                        "finish_reason": "stop" if data.get('done', True) else None
                    }
                ],
                "usage": usage
            }

            if 'system_fingerprint' in data:
                result['system_fingerprint'] = data['system_fingerprint']

            return JSONResponse(status_code=200, content=result)
        
        # Execute with concurrency control
        try:
            return await concurrency_manager.execute(
                model_name=model,
                request_id=request_id,
                coro=process_openai_chat(),
                timeout=config.get_int('request_timeout', 300)
            )
        except asyncio.QueueFull:
            error_message = LanguageDetector.get_error_message('server_busy', detected_lang)
            raise HTTPException(status_code=429, detail={"error": "queue_full", "message": error_message, "model": model})
        except asyncio.TimeoutError:
            error_message = LanguageDetector.get_error_message('request_timeout', detected_lang)
            raise HTTPException(status_code=504, detail={"error": "timeout", "message": error_message, "model": model})

    @router.post("/v1/completions")
    async def openai_completions(request: Request):
        """OpenAI-compatible text completions endpoint with guard integration."""
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("Invalid OpenAI completion JSON: %s", exc)
            raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(exc)})
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Incoming /v1/completions payload: %s", payload)

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail={"error": "invalid_payload", "message": "Expected JSON object."})

        model = payload.get('model')
        if not isinstance(model, str) or not model.strip():
            raise HTTPException(status_code=400, detail={"error": "invalid_model", "message": "model is required."})

        prompt_text = extract_prompt_from_completion_payload(payload)
        if not prompt_text:
            raise HTTPException(status_code=400, detail={"error": "invalid_prompt", "message": "prompt must be provided."})

        detected_lang = LanguageDetector.detect_language(prompt_text)
        is_stream = bool(payload.get('stream', False))
        inline_guard = inline_guard_errors_enabled(config)

        if config.get('enable_input_guard', True) and prompt_text:
            input_result = await guard_manager.scan_input(prompt_text, block_on_error=config.get('block_on_guard_error', False))
            if not input_result.get('allowed', True):
                logger.warning("OpenAI completion input blocked by LLM Guard: %s", input_result)

                failed_scanners = extract_failed_scanners(input_result)
                reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners]) if failed_scanners else None
                error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)

                if inline_guard:
                    markdown_message = format_markdown_error("Input blocked", error_message, failed_scanners)
                    guard_payload = {
                        "failed_scanners": failed_scanners,
                        "type": "input_blocked",
                        "language": detected_lang,
                        "usage": _zero_usage(),
                    }
                    return _inline_completion_guard_response(model, markdown_message, is_stream, guard_payload)

                raise HTTPException(
                    status_code=451,
                    detail=error_message,
                    headers={
                        "X-Error-Type": "content_policy_violation",
                        "X-Block-Type": "input_blocked",
                        "X-Language": detected_lang,
                        "X-Failed-Scanners": json.dumps(failed_scanners)
                    }
                )

        ollama_payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt_text,
            "stream": bool(payload.get('stream', False))
        }

        options = build_ollama_options_from_openai_payload(payload)
        if options:
            ollama_payload['options'] = options

        if isinstance(payload.get('images'), list):
            ollama_payload['images'] = payload['images']

        ollama_url = config.get('ollama_url')
        url = f"{ollama_url.rstrip('/')}/api/generate"

        try:
            client = get_http_client()
            timeout = config.get('openai_timeout', 300)
            if is_stream:
                # For streaming, wrap in an async generator that manages the context
                async def stream_wrapper():
                    async with client.stream("POST", url, json=ollama_payload, timeout=timeout) as response:
                        if response.status_code != 200:
                            logger.error("OpenAI completion upstream returned %s", response.status_code)
                            try:
                                upstream_detail = response.json()
                            except Exception:
                                upstream_detail = {"error": response.text}
                            raise HTTPException(status_code=response.status_code, detail=upstream_detail)
                        
                        async for chunk in stream_openai_completion_response(response, guard_manager, config, model, detected_lang):
                            yield chunk
                
                return StreamingResponse(
                    stream_wrapper(),
                    media_type="text/event-stream"
                )
            else:
                response = await client.post(url, json=ollama_payload, timeout=timeout)
                
                if response.status_code != 200:
                    logger.error("OpenAI completion upstream returned %s", response.status_code)
                    try:
                        upstream_detail = response.json()
                    except Exception:
                        upstream_detail = {"error": response.text}
                    raise HTTPException(status_code=response.status_code, detail=upstream_detail)
        except Exception as exc:
            logger.error("OpenAI completion upstream error: %s", exc)
            error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message})

        if is_stream:
            # This shouldn't be reached due to early return above
            pass

        try:
            data = response.json()
        except Exception as exc:
            logger.error("Failed to parse completion upstream response: %s", exc)
            error_message = LanguageDetector.get_error_message('server_error', detected_lang)
            # Close connection before raising exception
            try:
                await response.aclose()
            except Exception:
                pass
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})

        usage = _zero_usage()
        if isinstance(data, dict):
            usage = {
                "prompt_tokens": int(data.get('prompt_eval_count', 0) or 0),
                "completion_tokens": int(data.get('eval_count', 0) or 0)
            }
            usage['total_tokens'] = usage['prompt_tokens'] + usage['completion_tokens']

        output_text = extract_text_from_response(data)

        if config.get('enable_output_guard', True) and output_text:
            output_result = await guard_manager.scan_output(
                output_text,
                prompt=prompt_text,
                block_on_error=config.get('block_on_guard_error', False)
            )
            if not output_result.get('allowed', True):
                logger.warning("OpenAI completion output blocked by LLM Guard: %s", output_result)
                
                # Explicitly close response to free resources immediately
                try:
                    await response.aclose()
                    logger.info("Connection closed after blocking completion non-streaming output")
                except Exception as e:
                    logger.debug(f"Error closing connection: {e}")
                
                failed_scanners = extract_failed_scanners(output_result)
                error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)

                guard_payload = {
                    "failed_scanners": failed_scanners,
                    "type": "output_blocked",
                    "language": detected_lang,
                    "usage": usage,
                }

                if inline_guard:
                    markdown_message = format_markdown_error("Response blocked", error_message, failed_scanners)
                    return _inline_completion_guard_response(model, markdown_message, False, guard_payload)

                raise HTTPException(
                    status_code=451,
                    detail=error_message,
                    headers={
                        "X-Error-Type": "content_policy_violation",
                        "X-Block-Type": "output_blocked",
                        "X-Language": detected_lang,
                        "X-Failed-Scanners": json.dumps(failed_scanners)
                    }
                )
        
        # Close connection after successful processing
        try:
            await response.aclose()
            logger.debug("Connection closed after completion processing")
        except Exception:
            pass

        completion_id = f"cmpl-{uuid.uuid4().hex}"
        created_ts = int(time.time())

        result = {
            "id": completion_id,
            "object": "text_completion",
            "created": created_ts,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "text": output_text,
                    "logprobs": None,
                    "finish_reason": "stop" if data.get('done', True) else None
                }
            ],
            "usage": usage
        }

        if 'system_fingerprint' in data:
            result['system_fingerprint'] = data['system_fingerprint']

        return JSONResponse(status_code=200, content=result)

    @router.post("/v1/embeddings")
    async def proxy_openai_embed(request: Request):
        """Proxy endpoint for OpenAI-compatible embeddings."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Incoming /v1/embeddings payload: %s", payload)

        resp, err = await forward_request(config, '/v1/embeddings', payload=payload, stream=False, timeout=30)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)

    @router.post("/v1/models")
    async def proxy_openai_models(request: Request):
        """Proxy endpoint for OpenAI-compatible models list."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Incoming /v1/models payload: %s", payload)

        resp, err = await forward_request(config, '/v1/models', payload=payload, stream=False, timeout=30)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)
    
    return router
