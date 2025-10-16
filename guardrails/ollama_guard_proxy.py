"""
Ollama Proxy with LLM Guard Integration

This proxy applies LLM Guard scanners to both input prompts and model outputs.

Features:
- Input scanning (prompt injection, toxicity, secrets, etc.)
- Output scanning (toxicity, bias, malicious URLs, code generation, etc.)
- Streaming response support
- Comprehensive logging and metrics
- Configuration via YAML or environment variables

Usage:
    pip install fastapi uvicorn requests pydantic pyyaml llm-guard
    python ollama_guard_proxy.py

Or with Uvicorn directly:
    uvicorn ollama_guard_proxy:app --host 0.0.0.0 --port 8080
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import yaml

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import requests

try:
    from llm_guard.input_scanners import (
        BanSubstrings,
        PromptInjection,
        Toxicity,
        Secrets,
        Code,
        TokenLimit,
    )
    from llm_guard.output_scanners import (
        BanSubstrings as OutputBanSubstrings,
        Toxicity as OutputToxicity,
        MaliciousURLs,
        NoRefusal,
        NoCode,
    )
    from llm_guard.guard import Guard
    HAS_LLM_GUARD = True
except ImportError:
    HAS_LLM_GUARD = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the proxy."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = {}
        self.load_config(config_file)
        
    def load_config(self, config_file: Optional[str] = None):
        """Load configuration from YAML file or environment variables."""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}
        
        # Override with environment variables
        self.config['ollama_url'] = os.environ.get(
            'OLLAMA_URL',
            self.config.get('ollama_url', 'http://127.0.0.1:11434')
        )
        self.config['ollama_path'] = os.environ.get(
            'OLLAMA_PATH',
            self.config.get('ollama_path', '/api/generate')
        )
        self.config['proxy_port'] = int(os.environ.get(
            'PROXY_PORT',
            self.config.get('proxy_port', 8080)
        ))
        self.config['proxy_host'] = os.environ.get(
            'PROXY_HOST',
            self.config.get('proxy_host', '0.0.0.0')
        )
        
        # LLM Guard Settings
        self.config['enable_input_guard'] = os.environ.get(
            'ENABLE_INPUT_GUARD',
            self.config.get('enable_input_guard', True)
        )
        self.config['enable_output_guard'] = os.environ.get(
            'ENABLE_OUTPUT_GUARD',
            self.config.get('enable_output_guard', True)
        )
        self.config['block_on_guard_error'] = os.environ.get(
            'BLOCK_ON_GUARD_ERROR',
            self.config.get('block_on_guard_error', False)
        )
        
        logger.info(f"Configuration loaded: {self.config}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


class LLMGuardManager:
    """Manage LLM Guard initialization and scanning."""
    
    def __init__(self, enable_input: bool = True, enable_output: bool = True):
        self.enable_input = enable_input and HAS_LLM_GUARD
        self.enable_output = enable_output and HAS_LLM_GUARD
        self.input_guard = None
        self.output_guard = None
        
        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Install with: pip install llm-guard")
            return
        
        try:
            if self.enable_input:
                self._init_input_guard()
            if self.enable_output:
                self._init_output_guard()
        except Exception as e:
            logger.error(f"Failed to initialize LLM Guard: {e}")
    
    def _init_input_guard(self):
        """Initialize input scanners."""
        try:
            input_scanners = [
                BanSubstrings(["malicious", "dangerous"]),
                PromptInjection(),
                Toxicity(threshold=0.5),
                Secrets(),
                TokenLimit(limit=4000),
            ]
            self.input_guard = Guard(input_scanners=input_scanners)
            logger.info("Input guard initialized with scanners")
        except Exception as e:
            logger.error(f"Failed to initialize input guard: {e}")
            self.input_guard = None
    
    def _init_output_guard(self):
        """Initialize output scanners."""
        try:
            output_scanners = [
                OutputBanSubstrings(["malicious", "dangerous"]),
                OutputToxicity(threshold=0.5),
                MaliciousURLs(),
                NoRefusal(),
                NoCode(),
            ]
            self.output_guard = Guard(output_scanners=output_scanners)
            logger.info("Output guard initialized with scanners")
        except Exception as e:
            logger.error(f"Failed to initialize output guard: {e}")
            self.output_guard = None
    
    def scan_input(self, prompt: str, block_on_error: bool = False) -> Dict[str, Any]:
        """Scan input prompt."""
        if not self.enable_input or self.input_guard is None:
            return {"allowed": True, "scanners": {}}
        
        try:
            result = self.input_guard.validate(prompt)
            return {
                "allowed": result.validation_passed,
                "scanners": {
                    scanner.name: {
                        "passed": scanner.passed,
                        "reason": scanner.reason,
                    }
                    for scanner in result.scanners
                },
            }
        except Exception as e:
            logger.error(f"Error during input scanning: {e}")
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}
    
    def scan_output(self, text: str, block_on_error: bool = False) -> Dict[str, Any]:
        """Scan model output."""
        if not self.enable_output or self.output_guard is None:
            return {"allowed": True, "scanners": {}}
        
        try:
            result = self.output_guard.validate(text)
            return {
                "allowed": result.validation_passed,
                "scanners": {
                    scanner.name: {
                        "passed": scanner.passed,
                        "reason": scanner.reason,
                    }
                    for scanner in result.scanners
                },
            }
        except Exception as e:
            logger.error(f"Error during output scanning: {e}")
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}


# Initialize app and components
config = Config(os.environ.get('CONFIG_FILE'))
guard_manager = LLMGuardManager(
    enable_input=config.get('enable_input_guard', True),
    enable_output=config.get('enable_output_guard', True),
)

app = FastAPI(
    title="Ollama Proxy with LLM Guard",
    description="Secure proxy for Ollama with LLM Guard integration",
)


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
async def log_requests(request: Request, call_next):
    """Middleware to log all requests."""
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


@app.post("/api/generate")
async def proxy_generate(request: Request, background_tasks: BackgroundTasks):
    """Proxy endpoint for Ollama /api/generate."""
    # Parse request payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request JSON: {e}")
        raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(e)})
    
    # Extract prompt for scanning
    prompt = extract_text_from_payload(payload)
    
    # Scan input
    if config.get('enable_input_guard', True):
        input_result = guard_manager.scan_input(
            prompt,
            block_on_error=config.get('block_on_guard_error', False)
        )
        if not input_result['allowed']:
            logger.warning(f"Input blocked: {input_result}")
            raise HTTPException(
                status_code=400,
                detail={"error": "prompt_blocked", "details": input_result}
            )
        logger.info(f"Input passed guards: {input_result['scanners']}")
    
    # Forward to Ollama
    ollama_url = config.get('ollama_url')
    ollama_path = config.get('ollama_path')
    url = f"{ollama_url.rstrip('/')}{ollama_path}"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=300)
    except requests.RequestException as e:
        logger.error(f"Upstream error: {e}")
        raise HTTPException(
            status_code=502,
            detail={"error": "upstream_error", "message": str(e)}
        )
    
    if resp.status_code != 200:
        try:
            error_data = resp.json()
        except:
            error_data = {"error": resp.text}
        logger.error(f"Upstream returned {resp.status_code}: {error_data}")
        raise HTTPException(status_code=resp.status_code, detail=error_data)
    
    # Process streaming response
    if 'stream' in payload and payload['stream']:
        return StreamingResponse(
            stream_response_with_guard(resp),
            media_type="application/x-ndjson",
        )
    else:
        # Non-streaming response
        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"Failed to parse upstream response: {e}")
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        
        # Scan output
        if config.get('enable_output_guard', True):
            output_text = extract_text_from_response(data)
            output_result = guard_manager.scan_output(
                output_text,
                block_on_error=config.get('block_on_guard_error', False)
            )
            if not output_result['allowed']:
                logger.warning(f"Output blocked: {output_result}")
                raise HTTPException(
                    status_code=400,
                    detail={"error": "response_blocked", "details": output_result}
                )
            logger.info(f"Output passed guards: {output_result['scanners']}")
        
        return JSONResponse(status_code=200, content=data)


async def stream_response_with_guard(response):
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
                    # Send error as last chunk
                    error_chunk = {
                        "error": "response_blocked",
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
        yield (json.dumps({"error": str(e)}) + '\n').encode()


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
    
    # Scan input
    if config.get('enable_input_guard', True) and prompt:
        input_result = guard_manager.scan_input(
            prompt,
            block_on_error=config.get('block_on_guard_error', False)
        )
        if not input_result['allowed']:
            raise HTTPException(
                status_code=400,
                detail={"error": "prompt_blocked", "details": input_result}
            )
    
    # Forward to Ollama chat endpoint
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/chat"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=300)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Handle streaming or non-streaming responses
    if 'stream' in payload and payload['stream']:
        return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="text/event-stream")
    else:
        try:
            data = resp.json()
        except:
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
        
        # Scan output - Ollama chat uses 'message' field
        if config.get('enable_output_guard', True):
            output_text = ""
            if 'message' in data and isinstance(data['message'], dict):
                output_text = data['message'].get('content', '')
            
            if output_text:
                output_result = guard_manager.scan_output(output_text)
                if not output_result['allowed']:
                    raise HTTPException(
                        status_code=400,
                        detail={"error": "response_blocked", "details": output_result}
                    )
        
        return JSONResponse(status_code=200, content=data)


@app.post("/api/pull")
async def proxy_pull(request: Request):
    """Proxy endpoint for Ollama model pull."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/pull"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Stream pull response
    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.post("/api/push")
async def proxy_push(request: Request):
    """Proxy endpoint for Ollama model push."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/push"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Stream push response
    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.post("/api/create")
async def proxy_create(request: Request):
    """Proxy endpoint for Ollama model creation."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/create"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Stream create response
    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.get("/api/tags")
async def proxy_tags():
    """Proxy endpoint for Ollama list models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/tags"
    
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.post("/api/show")
async def proxy_show(request: Request):
    """Proxy endpoint for Ollama show model info."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/show"
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.delete("/api/delete")
async def proxy_delete(request: Request):
    """Proxy endpoint for Ollama delete model."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/delete"
    
    try:
        resp = requests.delete(url, json=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    return JSONResponse(status_code=200, content={})


@app.post("/api/copy")
async def proxy_copy(request: Request):
    """Proxy endpoint for Ollama copy model."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/copy"
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    return JSONResponse(status_code=200, content={})


@app.post("/api/embed")
async def proxy_embed(request: Request):
    """Proxy endpoint for Ollama generate embeddings."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/embed"
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.get("/api/ps")
async def proxy_ps():
    """Proxy endpoint for Ollama list running models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/ps"
    
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.get("/api/version")
async def proxy_version():
    """Proxy endpoint for Ollama version."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/version"
    
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "guards": {
            "input_guard": "enabled" if guard_manager.enable_input else "disabled",
            "output_guard": "enabled" if guard_manager.enable_output else "disabled",
        }
    }


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    safe_config = {k: v for k, v in config.config.items() if k not in ['secret_key']}
    return safe_config


if __name__ == "__main__":
    host = config.get('proxy_host', '0.0.0.0')
    port = config.get('proxy_port', 8080)
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    uvicorn.run(app, host=host, port=port)
