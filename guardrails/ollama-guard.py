"""
Lightweight proxy that applies simple guardrails (or llmguard if installed)
to requests sent to an Ollama HTTP endpoint.

Usage:
  pip install fastapi uvicorn requests
  # optionally: pip install llmguard   (if you have that package)
  OLLAMA_URL=http://127.0.0.1:11434 uvicorn ollama-guard:app --host 0.0.0.0 --port 8080

Send the same JSON you would send to Ollama to this proxy's /v1/generate endpoint.
This script performs:
 - prompt pre-check (block or modify)
 - forwards to Ollama
 - output post-check (block or redact)
 - returns the final result to caller
"""

from typing import Dict, Any
import os
import re
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# Attempt to use llmguard if available (best-effort; adapt to your llmguard API)
USE_LLMGUARD = False
try:
    import llmguard  # type: ignore
    # adapt below to the actual llmguard API if different
    # e.g. guard = llmguard.Guard.from_file("policy.yaml")
    guard = None
    if hasattr(llmguard, "Guard"):
        try:
            guard = llmguard.Guard.from_file("policy.yaml")
            USE_LLMGUARD = True
        except Exception:
            # fallback to runtime-only or other initialization if needed
            USE_LLMGUARD = False
except Exception:
    USE_LLMGUARD = False

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_GENERATE_PATH = os.environ.get("OLLAMA_PATH", "/api/generate")  # adjust if your Ollama uses a different path

app = FastAPI(title="Ollama proxy with guardrails")


def simple_prompt_check(prompt: str) -> Dict[str, Any]:
    """Very small example guard: check banned words and max length."""
    banned = [r"\bterror\b", r"\bkill\b", r"\bchild(?:ren)?\b"]  # example; adjust to policy
    max_len = 20000  # characters
    for pat in banned:
        if re.search(pat, prompt, flags=re.IGNORECASE):
            return {"allow": False, "reason": f"Prompt contains banned content: {pat}"}
    if len(prompt) > max_len:
        return {"allow": False, "reason": "Prompt too long"}
    return {"allow": True}


def simple_response_check(text: str) -> Dict[str, Any]:
    """Simple post-check for disallowed content in model output."""
    banned_out = [r"\bpassword\b", r"\bsecret\b"]
    for pat in banned_out:
        if re.search(pat, text, flags=re.IGNORECASE):
            return {"allow": False, "reason": f"Output contains sensitive data: {pat}"}
    return {"allow": True}


def guard_prompt(prompt: str) -> Dict[str, Any]:
    """Try llmguard if available, otherwise fallback to simple check."""
    if USE_LLMGUARD and guard is not None:
        # Adapt this call to your installed llmguard API
        try:
            verdict = guard.evaluate_prompt(prompt)  # pseudo-call; replace as needed
            return {"allow": verdict.allow, "reason": getattr(verdict, "reason", None)}
        except Exception:
            pass
    return simple_prompt_check(prompt)


def guard_response(text: str) -> Dict[str, Any]:
    if USE_LLMGUARD and guard is not None:
        try:
            verdict = guard.evaluate_output(text)  # pseudo-call; replace as needed
            return {"allow": verdict.allow, "reason": getattr(verdict, "reason", None)}
        except Exception:
            pass
    return simple_response_check(text)


@app.post("/v1/generate")
async def proxy_generate(request: Request):
    payload = await request.json()
    # Typical Ollama payload contains "model" and "prompt" (adjust if your client differs)
    prompt = ""
    if isinstance(payload, dict):
        # try several common keys
        if "prompt" in payload:
            prompt = payload["prompt"]
        elif "input" in payload:
            prompt = payload["input"]
        else:
            # if prompt is nested or structured, convert to string for checks
            prompt = str(payload)

    # pre-check
    pre = guard_prompt(prompt)
    if not pre.get("allow", False):
        raise HTTPException(status_code=400, detail={"error": "prompt_blocked", "reason": pre.get("reason")})

    # Forward to Ollama
    url = OLLAMA_URL.rstrip("/") + OLLAMA_GENERATE_PATH
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    # if upstream returns non-200, forward status and body
    if resp.status_code != 200:
        return JSONResponse(status_code=resp.status_code, content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"error": resp.text})

    # Inspect response body
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    # Find candidate text(s) to check in the response.
    # Many Ollama responses include a "text" or "content" fields; try common places.
    combined_text = ""
    if isinstance(data, dict):
        # naive extraction: join string values
        for v in data.values():
            if isinstance(v, str):
                combined_text += v + "\n"
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        combined_text += item + "\n"
                    elif isinstance(item, dict):
                        for sv in item.values():
                            if isinstance(sv, str):
                                combined_text += sv + "\n"
    else:
        combined_text = str(data)

    post = guard_response(combined_text)
    if not post.get("allow", True):
        # block the response; return sanitized message
        return JSONResponse(status_code=403, content={"error": "response_blocked", "reason": post.get("reason")})

    # allowed -> return upstream JSON as-is
    return JSONResponse(status_code=200, content=data)