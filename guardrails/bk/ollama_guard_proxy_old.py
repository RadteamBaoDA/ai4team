"""
Ollama Proxy with LLM Guard Integration

This proxy applies LLM Guard scanners to both input prompts and model outputs.

Features:
- Input scanning (prompt injection, toxicity, secrets, etc.)
- Output scanning (toxicity, bias, malicious URLs, code generation, etc.)
- Streaming response support
- Comprehensive logging and metrics
- Configuration via YAML or environment variables
- IP whitelist support (restrict access to nginx only)

Usage:
    pip install fastapi uvicorn requests pydantic pyyaml llm-guard
    python ollama_guard_proxy.py

Or with Uvicorn directly:
    uvicorn ollama_guard_proxy:app --host 0.0.0.0 --port 8080

IP Whitelist (Nginx Only):
    # Via environment variable (comma-separated)
    export NGINX_WHITELIST="127.0.0.1,192.168.1.10,10.0.0.5"
    
    # Via YAML configuration file
    # nginx_whitelist:
    #   - "127.0.0.1"
    #   - "192.168.1.10"
    #   - "10.0.0.5"
"""

import os
import json
import logging
import re
import time
import uuid
import asyncio

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, ORJSONResponse
import uvicorn
import httpx

from config import Config
from ip_whitelist import IPWhitelist
from language import LanguageDetector
from guard_manager import LLMGuardManager
from concurrency import ConcurrencyManager
logger = logging.getLogger(__name__)

# Import caching
try:
    from cache import GuardCache
    HAS_CACHE = True
except ImportError as e:
    logger.warning(f'Cache not available: {e}')
    HAS_CACHE = False
    GuardCache = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Constants
DEFAULTS = {
    'OLLAMA_URL': 'http://127.0.0.1:11434',
    'OLLAMA_PATH': '/api/generate',
    'PROXY_PORT': 8080,
    'PROXY_HOST': '0.0.0.0',
}

# HTTP connection pooling for upstream Ollama
_HTTP_CLIENT: Optional[httpx.AsyncClient] = None

def get_http_client(max_pool: int = 100) -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        limits = httpx.Limits(max_connections=max_pool, max_keepalive_connections=max_pool)
        # Set a default timeout
        timeout = httpx.Timeout(300.0, connect=60.0)
        _HTTP_CLIENT = httpx.AsyncClient(limits=limits, timeout=timeout)
    return _HTTP_CLIENT

# Initialize app and components
config = Config(os.environ.get('CONFIG_FILE'))

# Initialize guard manager (scanners load at startup)
guard_manager = LLMGuardManager(
    enable_input=config.get_bool('enable_input_guard', True),
    enable_output=config.get_bool('enable_output_guard', True),
    lazy_init=False  # Scanners initialize at startup
)

# Initialize IP whitelist (nginx only)
ip_whitelist = IPWhitelist(config.get_list('nginx_whitelist', []))

# Initialize concurrency manager (Ollama-style)
num_parallel = config.get('ollama_num_parallel', 'auto')
if num_parallel == 'auto':
    concurrency_manager = ConcurrencyManager(
        default_parallel=None,  # Auto-detect
        default_queue_limit=config.get_int('ollama_max_queue', 512),
        auto_detect_parallel=True
    )
else:
    concurrency_manager = ConcurrencyManager(
        default_parallel=int(num_parallel),
        default_queue_limit=config.get_int('ollama_max_queue', 512),
        auto_detect_parallel=False
    )

# Initialize cache
guard_cache = None

if HAS_CACHE:
    # Initialize cache with Redis support
    cache_enabled = config.get_bool('cache_enabled', True)
    if cache_enabled:
        guard_cache = GuardCache(
            enabled=True,
            backend=config.get_str('cache_backend', 'auto'),
            max_size=config.get_int('cache_max_size', 1000),
            ttl_seconds=config.get_int('cache_ttl', 3600),
            redis_host=config.get_str('redis_host', 'localhost'),
            redis_port=config.get_int('redis_port', 6379),
            redis_db=config.get_int('redis_db', 0),
            redis_password=config.get_str('redis_password'),
            redis_max_connections=config.get_int('redis_max_connections', 50),
            redis_timeout=config.get_int('redis_timeout', 5),
        )
        logger.info(f"Guard cache initialized: backend={guard_cache.backend}")

app = FastAPI(
    title="Ollama Proxy with LLM Guard",
    description="Secure proxy for Ollama with LLM Guard integration - Optimized for Apple Silicon",
    default_response_class=ORJSONResponse,
)

@app.on_event("startup")
async def startup_event():
    # Initialize the client on startup
    get_http_client()
    # Initialize async components
    if HAS_CACHE and guard_cache:
        await guard_cache.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    client = get_http_client()
    if client:
        await client.aclose()


def extract_client_ip(request: Request) -> str:
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


def combine_messages_text(messages: List[Dict[str, Any]]) -> str:
    """Combine message contents into a single string for guard scanning."""
    if not isinstance(messages, list):
        return ""

    combined: List[str] = []
    for msg in messages:
        if isinstance(msg, dict) and isinstance(msg.get('content'), str):
            combined.append(msg['content'])
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


def format_sse_event(data: Dict[str, Any]) -> bytes:
    """Serialize a chunk for Server-Sent Events streaming."""
    return f"data: {json.dumps(data)}\n\n".encode()


def extract_prompt_from_completion_payload(payload: Dict[str, Any]) -> str:
    """Extract prompt text for OpenAI completion payloads."""
    prompt = payload.get('prompt')
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        return "\n".join(str(item) for item in prompt if isinstance(item, (str, int, float)))
    return str(prompt) if prompt is not None else ""


@app.middleware("http")
async def check_ip_whitelist(request: Request, call_next):
    """Middleware to check IP whitelist (nginx only)."""
    client_ip = extract_client_ip(request)
    
    # Check if client IP is whitelisted
    if not ip_whitelist.is_allowed(client_ip):
        logger.warning(f"Rejected request from non-whitelisted IP: {client_ip} {request.method} {request.url.path}")
        return JSONResponse(
            status_code=403,
            content={
                "error": "access_denied",
                "message": "Access denied. Only requests from whitelisted IPs are allowed.",
                "client_ip": client_ip
            }
        )
    
    logger.debug(f"IP whitelist check passed for {client_ip}")
    response = await call_next(request)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests with client IP and path."""
    client_ip = extract_client_ip(request)
    logger.info("Request from %s: %s %s", client_ip, request.method, request.url.path)
    start_ts = time.time()
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_ts) * 1000)
        logger.info("Response status: %s (%d ms)", locals().get('response', None).status_code if 'response' in locals() else 'n/a', duration_ms)


async def safe_json(response: httpx.Response) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Safely parse JSON from httpx.Response.

    Returns (data, error_message). Only one of them will be non-None.
    """
    try:
        return response.json(), None
    except Exception as e:
        return None, str(e)


async def forward_request(path: str, payload: Any = None, stream: bool = False, timeout: int = 300):
    """Forward a request to the Ollama backend.

    Returns the httpx.Response and an optional error string.
    For streaming, returns the stream context manager that must be used with 'async with'.
    """
    ollama_url = config.get('ollama_url')
    full = f"{ollama_url.rstrip('/')}{path}"
    try:
        client = get_http_client()
        if payload is None:
            resp = await client.get(full, timeout=timeout)
        else:
            if stream:
                # For streaming, return the context manager itself
                return client.stream("POST", full, json=payload, timeout=timeout), None
            resp = await client.post(full, json=payload, timeout=timeout)
        return resp, None
    except httpx.RequestError as e:
        return None, str(e)


@app.post("/api/generate")
async def proxy_generate(request: Request, background_tasks: BackgroundTasks):
    """Proxy /api/generate with input/output scanning and streaming support.

    The function delegates upstream calls to `forward_request` and uses
    `safe_json` to parse responses. Behavior remains compatible with previous version.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse request JSON: %s", e)
        raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(e)})

    # Extract model and prompt
    model_name = extract_model_from_payload(payload)
    prompt = extract_text_from_payload(payload)
    detected_lang = LanguageDetector.detect_language(prompt)
    
    # Generate unique request ID
    request_id = f"gen-{uuid.uuid4().hex[:8]}"

    # Define the processing coroutine
    async def process_request():
        # Input guard with cache
        if config.get('enable_input_guard', True) and prompt:
            input_result = None
            if HAS_CACHE and guard_cache:
                input_result = await guard_cache.get_input_result(prompt)
                if input_result:
                    logger.debug("Input scan cache hit")
            if not input_result:
                input_result = await guard_manager.scan_input(prompt, block_on_error=config.get('block_on_guard_error', False))
                if HAS_CACHE and guard_cache:
                    try:
                        await guard_cache.set_input_result(prompt, input_result)
                    except Exception:
                        pass
            if not input_result.get('allowed', True):
                logger.warning("Input blocked by LLM Guard: %s", input_result)
                
                # Extract failed scanners with details
                failed_scanners = []
                for scanner_name, info in input_result.get('scanners', {}).items():
                    if not info.get('passed', True):
                        failed_scanners.append({
                            "scanner": scanner_name,
                            "reason": info.get('reason', 'Content policy violation'),
                            "score": info.get('score')
                        })
                
                # Build user-friendly reason
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

        # Forward to Ollama
        path = config.get('ollama_path', '/api/generate')
        is_stream = bool(payload.get('stream') if isinstance(payload, dict) else False)
        resp, err = await forward_request(path, payload=payload, stream=is_stream)
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
            if output_text and HAS_CACHE and guard_cache:
                output_result = await guard_cache.get_output_result(output_text)
                if output_result:
                    logger.debug("Output scan cache hit")
            if output_result is None:
                output_result = await guard_manager.scan_output(output_text, block_on_error=config.get('block_on_guard_error', False))
                if output_text and HAS_CACHE and guard_cache:
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


async def stream_response_with_guard(response: httpx.Response, detected_lang: str = 'en'):
    """Stream response with output scanning.
    
    Handles both /api/generate format (response field) and /api/chat format (message.content field).
    Ensures proper connection cleanup and resource freeing when output is blocked.
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


async def stream_openai_chat_response(response: httpx.Response, model: str, detected_lang: str = 'en'):
    """Stream OpenAI-compatible chat completions with guard scanning.
    
    Ensures proper connection cleanup and resource freeing when output is blocked.
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


async def stream_openai_completion_response(response: httpx.Response, model: str, detected_lang: str = 'en'):
    """Stream OpenAI-compatible text completions with guard scanning.
    
    Ensures proper connection cleanup and resource freeing when output is blocked.
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


@app.post("/api/chat")
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
    
    # Define processing coroutine
    async def process_chat_request():
        # Scan input with cache
        if config.get('enable_input_guard', True) and prompt:
            input_result = None
            if HAS_CACHE and guard_cache:
                input_result = await guard_cache.get_input_result(prompt)
                if input_result:
                    logger.debug("Input scan cache hit")
            if not input_result:
                input_result = await guard_manager.scan_input(
                    prompt,
                    block_on_error=config.get('block_on_guard_error', False)
                )
                if HAS_CACHE and guard_cache:
                    try:
                        await guard_cache.set_input_result(prompt, input_result)
                    except Exception:
                        pass
            if not input_result['allowed']:
                logger.warning(f"Chat input blocked by LLM Guard: {input_result}")
                
                # Extract failed scanners with details
                failed_scanners = []
                for scanner_name, info in input_result.get('scanners', {}).items():
                    if not info.get('passed', True):
                        failed_scanners.append({
                            "scanner": scanner_name,
                            "reason": info.get('reason', 'Content policy violation'),
                            "score": info.get('score')
                        })
                
                # Build reason string
                reason = ', '.join([f"{s['scanner']}: {s['reason']}" for s in failed_scanners])
                
                # Get localized error message
                error_message = LanguageDetector.get_error_message(
                    'prompt_blocked',
                    detected_lang,
                    reason
                )
                
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
        
        # Forward to Ollama chat endpoint
        ollama_url = config.get('ollama_url')
        url = f"{ollama_url.rstrip('/')}/api/chat"
        is_stream = 'stream' in payload and payload['stream']
        
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
                return JSONResponse(status_code=200, content=data)
        except httpx.RequestError as e:
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
        
        # Scan output - Ollama chat uses 'message' field
        if config.get('enable_output_guard', True):
            output_text = ""
            if 'message' in data and isinstance(data['message'], dict):
                output_text = data['message'].get('content', '')
            
            if output_text:
                output_result = await guard_manager.scan_output(output_text)
                if not output_result['allowed']:
                    logger.warning(f"Output blocked: {output_result}")
                    
                    # Get localized error message
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                    
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "response_blocked",
                            "message": error_message,
                            "language": detected_lang,
                            "details": output_result
                        }
                    )
        
        return JSONResponse(status_code=200, content=data)


@app.post("/v1/chat/completions")
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
                        
                        async for chunk in stream_openai_chat_response(response, model, detected_lang):
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
        except httpx.RequestError as exc:
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
                output_result = await guard_manager.scan_output(output_text, block_on_error=config.get('block_on_guard_error', False))
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


@app.post("/v1/completions")
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
                    
                    async for chunk in stream_openai_completion_response(response, model, detected_lang):
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
    except httpx.RequestError as exc:
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
            output_result = await guard_manager.scan_output(output_text, block_on_error=config.get('block_on_guard_error', False))
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


@app.post("/api/pull")
async def proxy_pull(request: Request):
    """Proxy endpoint for Ollama model pull."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/pull', payload=payload, stream=True, timeout=3600)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})

    return StreamingResponse(resp.aiter_bytes(), media_type="application/x-ndjson")


@app.post("/api/push")
async def proxy_push(request: Request):
    """Proxy endpoint for Ollama model push."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/push', payload=payload, stream=True, timeout=3600)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})

    return StreamingResponse(resp.aiter_bytes(), media_type="application/x-ndjson")


@app.post("/api/create")
async def proxy_create(request: Request):
    """Proxy endpoint for Ollama model creation."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/create', payload=payload, stream=True, timeout=3600)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})

    return StreamingResponse(resp.aiter_bytes(), media_type="application/x-ndjson")


@app.get("/api/tags")
async def proxy_tags():
    """Proxy endpoint for Ollama list models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/tags"
    
    resp, err = await forward_request('/api/tags', payload=None, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.post("/api/show")
async def proxy_show(request: Request):
    """Proxy endpoint for Ollama show model info."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/show', payload=payload, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.delete("/api/delete")
async def proxy_delete(request: Request):
    """Proxy endpoint for Ollama delete model."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/delete', payload=payload, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    return JSONResponse(status_code=200, content={})


@app.post("/api/copy")
async def proxy_copy(request: Request):
    """Proxy endpoint for Ollama copy model."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/copy', payload=payload, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    return JSONResponse(status_code=200, content={})


@app.post("/api/embed")
async def proxy_embed(request: Request):
    """Proxy endpoint for Ollama generate embeddings."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/api/embed', payload=payload, stream=False, timeout=30)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)

@app.post("/v1/embeddings")
async def proxy_openai_embed(request: Request):
    """Proxy endpoint for Ollama generate embeddings."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/v1/embeddings', payload=payload, stream=False, timeout=30)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)

@app.post("/v1/models")
async def proxy_openai_models(request: Request):
    """Proxy endpoint for Ollama generate models."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = await forward_request('/v1/models', payload=payload, stream=False, timeout=30)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.get("/api/ps")
async def proxy_ps():
    """Proxy endpoint for Ollama list running models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/ps"
    
    resp, err = await forward_request('/api/ps', payload=None, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.get("/api/version")
async def proxy_version():
    """Proxy endpoint for Ollama version."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/version"
    
    resp, err = await forward_request('/api/version', payload=None, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = await safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.get("/health")
async def health_check():
    """Health check endpoint with performance metrics."""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "guards": {
            "input_guard": "enabled" if getattr(guard_manager, 'enable_input', False) else "disabled",
            "output_guard": "enabled" if getattr(guard_manager, 'enable_output', False) else "disabled",
        },
        "whitelist": ip_whitelist.get_stats(),
    }
    
    # Add concurrency info
    queue_stats = await concurrency_manager.get_stats()
    health_data['concurrency'] = {
        "default_parallel": queue_stats.get('default_parallel'),
        "default_queue_limit": queue_stats.get('default_queue_limit'),
        "total_models": queue_stats.get('total_models', 0),
        "memory": concurrency_manager.get_memory_info()
    }
    
    # Add device information
    if hasattr(guard_manager, 'device'):
        health_data['device'] = guard_manager.device
    
    # Add cache stats if available
    if HAS_CACHE and guard_cache:
        health_data['cache'] = await guard_cache.get_stats()
    
    return health_data


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    # Build a minimal, non-sensitive view of the configuration
    safe_config = {
        'ollama_url': config.get('ollama_url'),
        'ollama_path': config.get('ollama_path'),
        'proxy_host': config.get('proxy_host'),
        'proxy_port': config.get('proxy_port'),
        'enable_input_guard': config.get('enable_input_guard'),
        'enable_output_guard': config.get('enable_output_guard'),
        'block_on_guard_error': config.get('block_on_guard_error'),
    }
    
    # Show whitelist summary (enabled, count) but not the raw IPs
    wl = ip_whitelist.get_stats()
    safe_config['nginx_whitelist'] = {'enabled': wl['enabled'], 'count': wl['count']}
    
    # Add optimization status
    if HAS_CACHE:
        safe_config['optimizations'] = {
            'cache_enabled': guard_cache is not None and guard_cache.enabled,
        }
        
        # Add device info
        if hasattr(guard_manager, 'device'):
            safe_config['device'] = guard_manager.device
    
    return safe_config


@app.get("/stats")
async def get_stats():
    """Get comprehensive statistics."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "guards": {
            "input_enabled": getattr(guard_manager, 'enable_input', False),
            "output_enabled": getattr(guard_manager, 'enable_output', False),
            "device": getattr(guard_manager, 'device', 'unknown'),
        },
        "whitelist": ip_whitelist.get_stats(),
    }
    
    if HAS_CACHE:
        # Cache stats
        if guard_cache:
            stats['cache'] = await guard_cache.get_stats()
    
    return stats


@app.post("/admin/cache/clear")
async def clear_cache():
    """Clear the cache (admin endpoint)."""
    if not HAS_CACHE or not guard_cache:
        return {"error": "Cache not available"}
    
    await guard_cache.clear()
    return {"status": "success", "message": "Cache cleared"}


@app.post("/admin/cache/cleanup")
async def cleanup_cache():
    """Clean up expired cache entries."""
    if not HAS_CACHE or not guard_cache:
        return {"error": "Cache not available"}
    
    removed = await guard_cache.cleanup_expired()
    return {"status": "success", "removed": removed}


@app.get("/queue/stats")
async def get_queue_stats(model: Optional[str] = None):
    """Get queue statistics for all models or a specific model."""
    stats = await concurrency_manager.get_stats(model_name=model)
    return stats


@app.get("/queue/memory")
async def get_memory_info():
    """Get current memory information and recommended parallel limit."""
    return concurrency_manager.get_memory_info()


@app.post("/admin/queue/reset")
async def reset_queue_stats(model: Optional[str] = None):
    """Reset queue statistics (admin endpoint)."""
    await concurrency_manager.reset_stats(model_name=model)
    return {
        "status": "success",
        "message": f"Statistics reset for {'all models' if not model else f'model {model}'}"
    }


@app.post("/admin/queue/update")
async def update_queue_limits(
    model: str,
    parallel_limit: Optional[int] = None,
    queue_limit: Optional[int] = None
):
    """Update queue limits for a specific model (admin endpoint)."""
    result = await concurrency_manager.update_limits(
        model_name=model,
        parallel_limit=parallel_limit,
        queue_limit=queue_limit
    )
    return result


if __name__ == "__main__":
    host = config.get('proxy_host', '0.0.0.0')
    port = config.get('proxy_port', 8080)
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    uvicorn.run(app, host=host, port=port)
