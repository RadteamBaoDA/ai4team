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

from http_client import forward_request, safe_json, get_http_client
from utils import (
    extract_prompt_from_completion_payload, 
    extract_text_from_response,
    combine_messages_text,
    build_ollama_options_from_openai_payload
)
from language import LanguageDetector

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def create_openai_endpoints(config, guard_manager, concurrency_manager, guard_cache, HAS_CACHE):
    """
    Create OpenAI-compatible endpoints with dependency injection.
    
    Args:
        config: Configuration object
        guard_manager: LLM Guard manager instance
        concurrency_manager: Concurrency manager instance
        guard_cache: Cache instance (or None)
        HAS_CACHE: Whether cache is available
    """
    
    # Import streaming handlers
    from streaming_handlers import stream_openai_chat_response, stream_openai_completion_response
    
    @router.post("/v1/chat/completions")
    async def openai_chat_completions(request: Request):
        """OpenAI-compatible chat completions endpoint with guard integration."""
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("Invalid OpenAI request JSON: %s", exc)
            raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(exc)})

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail={"error": "invalid_payload", "message": "Expected JSON object."})

        messages = payload.get('messages')
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail={"error": "invalid_messages", "message": "messages must be a non-empty list."})

        model = payload.get('model')
        if not isinstance(model, str) or not model.strip():
            raise HTTPException(status_code=400, detail={"error": "invalid_model", "message": "model is required."})

        # Generate request ID
        request_id = f"oai-chat-{uuid.uuid4().hex[:8]}"
        
        prompt_text = combine_messages_text(messages)
        detected_lang = LanguageDetector.detect_language(prompt_text)

        # Define processing coroutine
        async def process_openai_chat():
            if config.get('enable_input_guard', True) and prompt_text:
                input_result = None
                if HAS_CACHE and guard_cache:
                    input_result = await guard_cache.get_input_result(prompt_text)
                    if input_result:
                        logger.debug("Input scan cache hit")
                if not input_result:
                    input_result = await guard_manager.scan_input(prompt_text, block_on_error=config.get('block_on_guard_error', False))
                    if HAS_CACHE and guard_cache:
                        try:
                            await guard_cache.set_input_result(prompt_text, input_result)
                        except Exception:
                            pass
                if not input_result.get('allowed', True):
                    logger.warning("OpenAI input blocked by LLM Guard: %s", input_result)
                    
                    # Extract failed scanners with details
                    failed_scanners = []
                    for scanner_name, info in input_result.get('scanners', {}).items():
                        if not info.get('passed', True):
                            failed_scanners.append({
                                "scanner": scanner_name,
                                "reason": info.get('reason', 'Content policy violation'),
                                "score": info.get('score')
                            })
                    
                    reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners])
                    error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)
                    
                    raise HTTPException(
                        status_code=403,
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

            output_text = ""
            if isinstance(data, dict):
                message = data.get('message')
                if isinstance(message, dict):
                    output_text = message.get('content', '')

            if config.get('enable_output_guard', True) and output_text:
                output_result = None
                if HAS_CACHE and guard_cache:
                    output_result = await guard_cache.get_output_result(output_text)
                    if output_result:
                        logger.debug("Output scan cache hit")
                if output_result is None:
                    output_result = await guard_manager.scan_output(output_text, prompt=prompt_text, block_on_error=config.get('block_on_guard_error', False))
                    if HAS_CACHE and guard_cache:
                        try:
                            await guard_cache.set_output_result(output_text, output_result)
                        except Exception:
                            pass
                if not output_result.get('allowed', True):
                    logger.warning("OpenAI output blocked by LLM Guard: %s", output_result)
                    
                    # Explicitly close response to free resources immediately
                    try:
                        await response.aclose()
                        logger.info("Connection closed after blocking OpenAI non-streaming output")
                    except Exception as e:
                        logger.debug(f"Error closing connection: {e}")
                    
                    # Extract failed scanners with details
                    failed_scanners = []
                    for scanner_name, info in output_result.get('scanners', {}).items():
                        if not info.get('passed', True):
                            failed_scanners.append({
                                "scanner": scanner_name,
                                "reason": info.get('reason', 'Content policy violation'),
                                "score": info.get('score')
                            })
                    
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
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
            usage = {
                "prompt_tokens": int(data.get('prompt_eval_count', 0) or 0),
                "completion_tokens": int(data.get('eval_count', 0) or 0)
            }
            usage['total_tokens'] = usage['prompt_tokens'] + usage['completion_tokens']

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

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail={"error": "invalid_payload", "message": "Expected JSON object."})

        model = payload.get('model')
        if not isinstance(model, str) or not model.strip():
            raise HTTPException(status_code=400, detail={"error": "invalid_model", "message": "model is required."})

        prompt_text = extract_prompt_from_completion_payload(payload)
        if not prompt_text:
            raise HTTPException(status_code=400, detail={"error": "invalid_prompt", "message": "prompt must be provided."})

        detected_lang = LanguageDetector.detect_language(prompt_text)

        if config.get('enable_input_guard', True) and prompt_text:
            input_result = await guard_manager.scan_input(prompt_text, block_on_error=config.get('block_on_guard_error', False))
            if not input_result.get('allowed', True):
                logger.warning("OpenAI completion input blocked by LLM Guard: %s", input_result)
                
                # Extract failed scanners with details
                failed_scanners = []
                for scanner_name, info in input_result.get('scanners', {}).items():
                    if not info.get('passed', True):
                        failed_scanners.append({
                            "scanner": scanner_name,
                            "reason": info.get('reason', 'Content policy violation'),
                            "score": info.get('score')
                        })
                
                reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners])
                error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)
                
                raise HTTPException(
                    status_code=403,
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
        is_stream = bool(payload.get('stream'))

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

        output_text = extract_text_from_response(data)

        if config.get('enable_output_guard', True) and output_text:
            output_result = None
            if HAS_CACHE and guard_cache:
                output_result = await guard_cache.get_output_result(output_text)
                if output_result:
                    logger.debug("Output scan cache hit")
            if output_result is None:
                output_result = await guard_manager.scan_output(output_text, prompt=prompt_text, block_on_error=config.get('block_on_guard_error', False))
                if HAS_CACHE and guard_cache:
                    try:
                        await guard_cache.set_output_result(output_text, output_result)
                    except Exception:
                        pass
            if not output_result.get('allowed', True):
                logger.warning("OpenAI completion output blocked by LLM Guard: %s", output_result)
                
                # Explicitly close response to free resources immediately
                try:
                    await response.aclose()
                    logger.info("Connection closed after blocking completion non-streaming output")
                except Exception as e:
                    logger.debug(f"Error closing connection: {e}")
                
                # Extract failed scanners with details
                failed_scanners = []
                for scanner_name, info in output_result.get('scanners', {}).items():
                    if not info.get('passed', True):
                        failed_scanners.append({
                            "scanner": scanner_name,
                            "reason": info.get('reason', 'Content policy violation'),
                            "score": info.get('score')
                        })
                
                error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
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
        usage = {
            "prompt_tokens": int(data.get('prompt_eval_count', 0) or 0),
            "completion_tokens": int(data.get('eval_count', 0) or 0)
        }
        usage['total_tokens'] = usage['prompt_tokens'] + usage['completion_tokens']

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
