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
 
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
 

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import requests

from config import Config
from ip_whitelist import IPWhitelist
from language import LanguageDetector
from guard_manager import LLMGuardManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULTS = {
    'OLLAMA_URL': 'http://127.0.0.1:11434',
    'OLLAMA_PATH': '/api/generate',
    'PROXY_PORT': 8080,
    'PROXY_HOST': '0.0.0.0',
}




# The IPWhitelist, LanguageDetector, Config, and LLMGuardManager
# implementations have been moved to their own modules under the
# guardrails package. Import them from the package to keep this file
# focused on the FastAPI app and routing.


# Initialize app and components
config = Config(os.environ.get('CONFIG_FILE'))
guard_manager = LLMGuardManager(
    enable_input=config.get('enable_input_guard', True),
    enable_output=config.get('enable_output_guard', True),
)

# Initialize IP whitelist (nginx only)
ip_whitelist = IPWhitelist(config.get('nginx_whitelist', []))

app = FastAPI(
    title="Ollama Proxy with LLM Guard",
    description="Secure proxy for Ollama with LLM Guard integration",
)


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
    response = await call_next(request)
    logger.info("Response status: %s", response.status_code)
    return response


def safe_json(response: requests.Response) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Safely parse JSON from requests.Response.

    Returns (data, error_message). Only one of them will be non-None.
    """
    try:
        return response.json(), None
    except Exception as e:
        return None, str(e)


def forward_request(path: str, payload: Any = None, stream: bool = False, timeout: int = 300) -> Tuple[requests.Response, Optional[str]]:
    """Forward a request to the Ollama backend.

    Returns the requests.Response and an optional error string.
    """
    ollama_url = config.get('ollama_url')
    full = f"{ollama_url.rstrip('/')}{path}"
    try:
        if payload is None:
            resp = requests.get(full, timeout=timeout)
        else:
            resp = requests.post(full, json=payload, stream=stream, timeout=timeout)
        return resp, None
    except requests.RequestException as e:
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

    prompt = extract_text_from_payload(payload)
    detected_lang = LanguageDetector.detect_language(prompt)

    # Input guard
    if config.get('enable_input_guard', True) and prompt:
        input_result = guard_manager.scan_input(prompt, block_on_error=config.get('block_on_guard_error', False))
        if not input_result.get('allowed', True):
            logger.warning("Input blocked: %s", input_result)
            reason = ', '.join([
                f"{name}: {info.get('reason', 'Unknown')}"
                for name, info in input_result.get('scanners', {}).items()
                if not info.get('passed', True)
            ])
            error_message = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason)
            raise HTTPException(status_code=400, detail={
                "error": "prompt_blocked",
                "message": error_message,
                "language": detected_lang,
                "details": input_result
            })

    # Forward to Ollama
    path = config.get('ollama_path', '/api/generate')
    resp, err = forward_request(path, payload=payload, stream=bool(payload.get('stream') if isinstance(payload, dict) else False))
    if err:
        logger.error("Upstream error: %s", err)
        error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message, "details": err})

    if resp.status_code != 200:
        data, parse_err = safe_json(resp)
        logger.error("Upstream returned %s: %s", resp.status_code, data or resp.text)
        raise HTTPException(status_code=resp.status_code, detail=data or {"error": resp.text})

    # Stream handling
    if isinstance(payload, dict) and payload.get('stream'):
        return StreamingResponse(stream_response_with_guard(resp, detected_lang), media_type="application/x-ndjson")

    data, parse_err = safe_json(resp)
    if data is None:
        logger.error("Failed to parse upstream response: %s", parse_err)
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})

    # Output guard
    if config.get('enable_output_guard', True):
        output_text = extract_text_from_response(data)
        output_result = guard_manager.scan_output(output_text, block_on_error=config.get('block_on_guard_error', False))
        if not output_result.get('allowed', True):
            logger.warning("Output blocked: %s", output_result)
            error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
            raise HTTPException(status_code=400, detail={
                "error": "response_blocked",
                "message": error_message,
                "language": detected_lang,
                "details": output_result
            })

    return JSONResponse(status_code=200, content=data)


async def stream_response_with_guard(response, detected_lang: str = 'en'):
    """Stream response with output scanning."""
    accumulated_text = ""
    
    try:
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                yield line + b'\n'
                continue
            
            # Accumulate text from streaming responses
            if 'response' in data:
                accumulated_text += data['response']
            
            # Scan accumulated text periodically (every 500 chars)
            if len(accumulated_text) > 500 and config.get('enable_output_guard', True):
                output_result = guard_manager.scan_output(accumulated_text)
                if not output_result['allowed']:
                    logger.warning(f"Streaming output blocked: {output_result}")
                    
                    # Get localized error message
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                    
                    # Send error as last chunk
                    error_chunk = {
                        "error": "response_blocked",
                        "message": error_message,
                        "language": detected_lang,
                        "reason": output_result.get('scanners', {})
                    }
                    yield (json.dumps(error_chunk) + '\n').encode()
                    break
                accumulated_text = ""  # Reset for next batch
            
            yield line + b'\n'
        
        # Final scan of any remaining text
        if accumulated_text and config.get('enable_output_guard', True):
            output_result = guard_manager.scan_output(accumulated_text)
            if not output_result['allowed']:
                logger.warning(f"Final streaming output blocked: {output_result}")
    
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        yield (json.dumps({"error": str(e), "message": error_message}) + '\n').encode()


@app.post("/api/chat")
async def proxy_chat(request: Request):
    """Proxy endpoint for Ollama /api/chat."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    # Extract prompt from messages
    prompt = ""
    if 'messages' in payload and isinstance(payload['messages'], list):
        for msg in payload['messages']:
            if isinstance(msg, dict) and 'content' in msg:
                prompt += msg['content'] + "\n"
    
    # Detect language from prompt
    detected_lang = LanguageDetector.detect_language(prompt)
    
    # Scan input
    if config.get('enable_input_guard', True) and prompt:
        input_result = guard_manager.scan_input(
            prompt,
            block_on_error=config.get('block_on_guard_error', False)
        )
        if not input_result['allowed']:
            logger.warning(f"Input blocked: {input_result}")
            
            # Get scanner reason
            reason = ', '.join([
                f"{scanner_name}: {info.get('reason', 'Unknown')}"
                for scanner_name, info in input_result.get('scanners', {}).items()
                if not info.get('passed', True)
            ])
            
            # Get localized error message
            error_message = LanguageDetector.get_error_message(
                'prompt_blocked',
                detected_lang,
                reason
            )
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "prompt_blocked",
                    "message": error_message,
                    "language": detected_lang,
                    "details": input_result
                }
            )
    
    # Forward to Ollama chat endpoint
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/chat"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=300)
    except requests.RequestException as e:
        logger.error(f"Upstream error: {e}")
        error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Handle streaming or non-streaming responses
    if 'stream' in payload and payload['stream']:
        return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="text/event-stream")
    else:
        try:
            data = resp.json()
        except:
            error_message = LanguageDetector.get_error_message('server_error', detected_lang)
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})
        
        # Scan output - Ollama chat uses 'message' field
        if config.get('enable_output_guard', True):
            output_text = ""
            if 'message' in data and isinstance(data['message'], dict):
                output_text = data['message'].get('content', '')
            
            if output_text:
                output_result = guard_manager.scan_output(output_text)
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


@app.post("/api/pull")
async def proxy_pull(request: Request):
    """Proxy endpoint for Ollama model pull."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = forward_request('/api/pull', payload=payload, stream=True, timeout=3600)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})

    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.post("/api/push")
async def proxy_push(request: Request):
    """Proxy endpoint for Ollama model push."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = forward_request('/api/push', payload=payload, stream=True, timeout=3600)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})

    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.post("/api/create")
async def proxy_create(request: Request):
    """Proxy endpoint for Ollama model creation."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    resp, err = forward_request('/api/create', payload=payload, stream=True, timeout=3600)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})

    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.get("/api/tags")
async def proxy_tags():
    """Proxy endpoint for Ollama list models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/tags"
    
    resp, err = forward_request('/api/tags', payload=None, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = safe_json(resp)
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

    resp, err = forward_request('/api/show', payload=payload, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = safe_json(resp)
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

    resp, err = forward_request('/api/delete', payload=payload, stream=False, timeout=10)
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

    resp, err = forward_request('/api/copy', payload=payload, stream=False, timeout=10)
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

    resp, err = forward_request('/api/embed', payload=payload, stream=False, timeout=30)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.get("/api/ps")
async def proxy_ps():
    """Proxy endpoint for Ollama list running models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/ps"
    
    resp, err = forward_request('/api/ps', payload=None, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.get("/api/version")
async def proxy_version():
    """Proxy endpoint for Ollama version."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/version"
    
    resp, err = forward_request('/api/version', payload=None, stream=False, timeout=10)
    if err:
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "details": err})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    data, parse_err = safe_json(resp)
    if data is None:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    return JSONResponse(status_code=200, content=data)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "guards": {
            "input_guard": "enabled" if getattr(guard_manager, 'enable_input', False) else "disabled",
            "output_guard": "enabled" if getattr(guard_manager, 'enable_output', False) else "disabled",
        },
        "whitelist": ip_whitelist.get_stats()
    }


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
    return safe_config


if __name__ == "__main__":
    host = config.get('proxy_host', '0.0.0.0')
    port = config.get('proxy_port', 8080)
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    uvicorn.run(app, host=host, port=port)
