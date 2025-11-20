"""
Ollama API endpoints for the guard proxy.

This module contains all Ollama-specific API endpoints including:
- Text generation (/api/generate)
- Chat completions (/api/chat)
- Model management (pull, push, create, delete, copy, tags, show, ps, version)
- Embeddings (/api/embed)
"""

import json
import logging
import uuid
import asyncio
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse

from ..middleware.http_client import forward_request, safe_json, get_http_client
from ..utils import (
    extract_model_from_payload,
    extract_text_from_payload,
    extract_text_from_response,
    inline_guard_errors_enabled,
    extract_failed_scanners,
    format_markdown_error,
)
from ..utils.language import LanguageDetector

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def create_ollama_endpoints(config, guard_manager, concurrency_manager, guard_cache, has_cache):
    """
    Create Ollama endpoints with dependency injection.
    
    Args:
        config: Configuration object
        guard_manager: LLM Guard manager instance
        concurrency_manager: Concurrency manager instance
        guard_cache: Cache instance (or None)
        has_cache: Whether cache is available
    """
    
    # Import streaming handlers
    from .streaming_handlers import create_streaming_handlers
    stream_response_with_guard = create_streaming_handlers(config, guard_manager)

    def _inline_generate_guard_response(
        model_name: Optional[str],
        markdown_message: str,
        error_message: str,
        is_stream: bool,
        guard_payload: Dict[str, Any],
    ):
        payload = {
            "model": model_name,
            "response": markdown_message,
            "done": True,
            "error": {
                "message": error_message,
                "type": guard_payload.get("type"),
                "language": guard_payload.get("language"),
            },
            "guard": guard_payload,
        }

        if is_stream:
            async def _inline_stream():
                yield json.dumps(payload) + "\n"

            return StreamingResponse(_inline_stream(), media_type="application/x-ndjson")

        return JSONResponse(status_code=200, content=payload)

    def _inline_chat_guard_response(
        model_name: Optional[str],
        markdown_message: str,
        error_message: str,
        is_stream: bool,
        guard_payload: Dict[str, Any],
    ):
        payload = {
            "model": model_name,
            "message": {"role": "assistant", "content": markdown_message},
            "done": True,
            "error": {
                "message": error_message,
                "type": guard_payload.get("type"),
                "language": guard_payload.get("language"),
            },
            "guard": guard_payload,
        }

        if is_stream:
            async def _inline_stream():
                yield json.dumps(payload) + "\n"

            return StreamingResponse(_inline_stream(), media_type="text/event-stream")

        return JSONResponse(status_code=200, content=payload)
    
    @router.post("/api/generate")
    async def proxy_generate(request: Request, background_tasks: BackgroundTasks):
        """Proxy /api/generate with input/output scanning and streaming support."""
        try:
            payload = await request.json()
        except Exception as e:
            logger.error("Failed to parse request JSON: %s", e)
            raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(e)})

        # Extract model and prompt
        model_name = extract_model_from_payload(payload)
        prompt = extract_text_from_payload(payload)
        detected_lang = LanguageDetector.detect_language(prompt)
        inline_guard = inline_guard_errors_enabled(config)
        is_stream = bool(payload.get('stream') if isinstance(payload, dict) else False)
        
        # Generate unique request ID
        request_id = f"gen-{uuid.uuid4().hex[:8]}"

        # Define the processing coroutine
        async def process_request():
            # Input guard with cache
            if config.get('enable_input_guard', True) and prompt:
                input_result = None
                if has_cache and guard_cache:
                    input_result = await guard_cache.get_input_result(prompt)
                    if input_result:
                        logger.debug("Input scan cache hit")
                if not input_result:
                    input_result = await guard_manager.scan_input(prompt, block_on_error=config.get('block_on_guard_error', False))
                    if has_cache and guard_cache:
                        try:
                            await guard_cache.set_input_result(prompt, input_result)
                        except Exception:
                            pass
                if not input_result.get('allowed', True):
                    logger.warning("Input blocked by LLM Guard: %s", input_result)
                    failed_scanners = extract_failed_scanners(input_result)
                    reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners]) if failed_scanners else None
                    error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)

                    if inline_guard:
                        markdown_message = format_markdown_error("Input blocked", error_message, failed_scanners)
                        guard_payload = {
                            "failed_scanners": failed_scanners,
                            "type": "input_blocked",
                            "language": detected_lang,
                        }
                        return _inline_generate_guard_response(model_name, markdown_message, error_message, is_stream, guard_payload)

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

            # Forward to Ollama
            path = config.get('ollama_path', '/api/generate')
            resp, err = await forward_request(config, path, payload=payload, stream=is_stream)
            if err:
                logger.error("Upstream error: %s", err)
                error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
                raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message, "details": err})

            # Stream handling
            if is_stream:
                # resp is a stream context manager for streaming requests
                async def stream_wrapper():
                    async with resp as response:
                        if response.status_code != 200:
                            data, parse_err = await safe_json(response)
                            logger.error("Upstream returned %s: %s", response.status_code, data or response.text)
                            raise HTTPException(status_code=response.status_code, detail=data or {"error": response.text})
                        
                        async for chunk in stream_response_with_guard(response, detected_lang):
                            yield chunk
                
                return StreamingResponse(stream_wrapper(), media_type="application/x-ndjson")

            if resp.status_code != 200:
                data, parse_err = await safe_json(resp)
                logger.error("Upstream returned %s: %s", resp.status_code, data or resp.text)
                raise HTTPException(status_code=resp.status_code, detail=data or {"error": resp.text})

            data, parse_err = await safe_json(resp)
            if data is None:
                logger.error("Failed to parse upstream response: %s", parse_err)
                error_message = LanguageDetector.get_error_message('server_error', detected_lang)
                raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})

            # Output guard with cache (non-streaming)
            if config.get('enable_output_guard', True):
                output_text = extract_text_from_response(data)
                output_result = None
                if output_text and has_cache and guard_cache:
                    output_result = await guard_cache.get_output_result(output_text)
                    if output_result:
                        logger.debug("Output scan cache hit")
                if output_result is None:
                    output_result = await guard_manager.scan_output(output_text, prompt=prompt, block_on_error=config.get('block_on_guard_error', False))
                    if output_text and has_cache and guard_cache:
                        try:
                            await guard_cache.set_output_result(output_text, output_result)
                        except Exception:
                            pass
                if not output_result.get('allowed', True):
                    logger.warning("Output blocked by LLM Guard: %s", output_result)
                    
                    # Explicitly close response to free resources immediately
                    try:
                        await resp.aclose()
                        logger.info("Connection closed after blocking non-streaming output")
                    except Exception as e:
                        logger.debug(f"Error closing connection: {e}")
                    
                    failed_scanners = extract_failed_scanners(output_result)
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)

                    guard_payload = {
                        "failed_scanners": failed_scanners,
                        "type": "output_blocked",
                        "language": detected_lang,
                        "scan": output_result,
                    }

                    if inline_guard:
                        markdown_message = format_markdown_error("Response blocked", error_message, failed_scanners)
                        return _inline_generate_guard_response(model_name, markdown_message, error_message, False, guard_payload)

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

            return JSONResponse(status_code=200, content=data)
        
        # Execute with concurrency control
        try:
            return await concurrency_manager.execute(
                model_name=model_name,
                request_id=request_id,
                coro=process_request(),
                timeout=config.get_int('request_timeout', 300)
            )
        except asyncio.QueueFull:
            error_message = LanguageDetector.get_error_message('server_busy', detected_lang)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "queue_full",
                    "message": error_message,
                    "model": model_name
                }
            )
        except asyncio.TimeoutError:
            error_message = LanguageDetector.get_error_message('request_timeout', detected_lang)
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "timeout",
                    "message": error_message,
                    "model": model_name
                }
            )

    @router.post("/api/chat")
    async def proxy_chat(request: Request):
        """Proxy endpoint for Ollama /api/chat."""
        try:
            payload = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})
        
        # Extract model and prompt
        model_name = extract_model_from_payload(payload)
        request_id = f"chat-{uuid.uuid4().hex[:8]}"
        
        # Extract prompt from messages
        prompt = ""
        if 'messages' in payload and isinstance(payload['messages'], list):
            for msg in payload['messages']:
                if isinstance(msg, dict) and 'content' in msg:
                    prompt += msg['content'] + "\n"
        
        # Detect language from prompt
        detected_lang = LanguageDetector.detect_language(prompt)
        inline_guard = inline_guard_errors_enabled(config)
        is_stream = bool(payload.get('stream'))
        
        # Define processing coroutine
        async def process_chat_request():
            # Scan input with cache
            if config.get('enable_input_guard', True) and prompt:
                input_result = None
                if has_cache and guard_cache:
                    input_result = await guard_cache.get_input_result(prompt)
                    if input_result:
                        logger.debug("Input scan cache hit")
                if not input_result:
                    input_result = await guard_manager.scan_input(
                        prompt,
                        block_on_error=config.get('block_on_guard_error', False)
                    )
                    if has_cache and guard_cache:
                        try:
                            await guard_cache.set_input_result(prompt, input_result)
                        except Exception:
                            pass
                if not input_result.get('allowed', True):
                    logger.warning(f"Chat input blocked by LLM Guard: {input_result}")
                    failed_scanners = extract_failed_scanners(input_result)
                    reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners]) if failed_scanners else None
                    error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)

                    if inline_guard:
                        markdown_message = format_markdown_error("Input blocked", error_message, failed_scanners)
                        guard_payload = {
                            "failed_scanners": failed_scanners,
                            "type": "input_blocked",
                            "language": detected_lang,
                        }
                        return _inline_chat_guard_response(model_name, markdown_message, error_message, is_stream, guard_payload)

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
            
            # Forward to Ollama chat endpoint
            ollama_url = config.get('ollama_url')
            url = f"{ollama_url.rstrip('/')}/api/chat"
            
            try:
                client = get_http_client()
                if is_stream:
                    # For streaming, create an async generator that properly manages the context
                    async def stream_wrapper():
                        async with client.stream("POST", url, json=payload, timeout=300) as resp:
                            if resp.status_code != 200:
                                raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
                            # Use stream_response_with_guard to apply output scanning
                            async for chunk in stream_response_with_guard(resp, detected_lang):
                                yield chunk
                    
                    return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
                else:
                    resp = await client.post(url, json=payload, timeout=300)
                    if resp.status_code != 200:
                        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
                    
                    try:
                        data = resp.json()
                    except:
                        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
                        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})
                    
                    # Scan output for non-streaming
                    if config.get('enable_output_guard', True):
                        output_text = ""
                        if 'message' in data and isinstance(data['message'], dict):
                            output_text = data['message'].get('content', '')
                        
                        if output_text:
                            output_result = await guard_manager.scan_output(output_text, prompt=prompt)
                            if not output_result.get('allowed', True):
                                logger.warning(f"Output blocked: {output_result}")
                                failed_scanners = extract_failed_scanners(output_result)
                                error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                                guard_payload = {
                                    "failed_scanners": failed_scanners,
                                    "type": "output_blocked",
                                    "language": detected_lang,
                                    "scan": output_result,
                                }

                                if inline_guard:
                                    markdown_message = format_markdown_error("Response blocked", error_message, failed_scanners)
                                    return _inline_chat_guard_response(model_name, markdown_message, error_message, False, guard_payload)

                                raise HTTPException(
                                    status_code=451,
                                    detail={
                                        "error": "response_blocked",
                                        "message": error_message,
                                        "language": detected_lang,
                                        "details": output_result
                                    }
                                )
                    
                    return JSONResponse(status_code=200, content=data)
            except Exception as e:
                logger.error(f"Upstream error: {e}")
                error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
                raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message})
        
        # Execute with concurrency control
        try:
            return await concurrency_manager.execute(
                model_name=model_name,
                request_id=request_id,
                coro=process_chat_request(),
                timeout=config.get_int('request_timeout', 300)
            )
        except asyncio.QueueFull:
            error_message = LanguageDetector.get_error_message('server_busy', detected_lang)
            raise HTTPException(status_code=429, detail={"error": "queue_full", "message": error_message, "model": model_name})
        except asyncio.TimeoutError:
            error_message = LanguageDetector.get_error_message('request_timeout', detected_lang)
            raise HTTPException(status_code=504, detail={"error": "timeout", "message": error_message, "model": model_name})

    @router.post("/api/pull")
    async def proxy_pull(request: Request):
        """Proxy endpoint for Ollama model pull."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/pull', payload=payload, stream=True, timeout=3600)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        
        async def stream_bytes():
            async with resp as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail={"error": "upstream_error"})
                async for chunk in response.aiter_bytes():
                    yield chunk
        
        return StreamingResponse(stream_bytes(), media_type="application/x-ndjson")

    @router.post("/api/push")
    async def proxy_push(request: Request):
        """Proxy endpoint for Ollama model push."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/push', payload=payload, stream=True, timeout=3600)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        
        async def stream_bytes():
            async with resp as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail={"error": "upstream_error"})
                async for chunk in response.aiter_bytes():
                    yield chunk
        
        return StreamingResponse(stream_bytes(), media_type="application/x-ndjson")

    @router.post("/api/create")
    async def proxy_create(request: Request):
        """Proxy endpoint for Ollama model creation."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/create', payload=payload, stream=True, timeout=3600)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        
        async def stream_bytes():
            async with resp as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail={"error": "upstream_error"})
                async for chunk in response.aiter_bytes():
                    yield chunk
        
        return StreamingResponse(stream_bytes(), media_type="application/x-ndjson")

    @router.get("/api/tags")
    async def proxy_tags(request: Request):
        """Proxy endpoint for Ollama list models."""
        resp, err = await forward_request(config, '/api/tags', payload=None, stream=False, timeout=10)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)

    @router.post("/api/show")
    async def proxy_show(request: Request):
        """Proxy endpoint for Ollama show model info."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/show', payload=payload, stream=False, timeout=10)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)

    @router.delete("/api/delete")
    async def proxy_delete(request: Request):
        """Proxy endpoint for Ollama delete model."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/delete', payload=payload, stream=False, timeout=10)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        return JSONResponse(status_code=200, content={})

    @router.post("/api/copy")
    async def proxy_copy(request: Request):
        """Proxy endpoint for Ollama copy model."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/copy', payload=payload, stream=False, timeout=10)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        return JSONResponse(status_code=200, content={})

    @router.post("/api/embed")
    async def proxy_embed(request: Request):
        """Proxy endpoint for Ollama generate embeddings."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_json"})

        resp, err = await forward_request(config, '/api/embed', payload=payload, stream=False, timeout=30)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)

    @router.get("/api/ps")
    async def proxy_ps(request: Request):
        """Proxy endpoint for Ollama running models (list running processes)."""
        resp, err = await forward_request(config, '/api/ps', payload=None, stream=False, timeout=10)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)

    @router.get("/api/version")
    async def proxy_version(request: Request):
        """Proxy endpoint for Ollama version."""
        resp, err = await forward_request(config, '/api/version', payload=None, stream=False, timeout=10)
        if err:
            raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
        data, parse_err = await safe_json(resp)
        if data is None:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        return JSONResponse(status_code=200, content=data)
    
    return router
