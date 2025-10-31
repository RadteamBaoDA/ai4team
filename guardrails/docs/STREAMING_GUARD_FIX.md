# Streaming Output Guard Fix

## Issue
The streaming endpoints were not applying output guard scanning to the responses. They were just passing through raw bytes without checking for toxic content, malicious code, or other security issues.

## Root Cause
When streaming responses, the proxy was using simple `async for chunk in resp.aiter_bytes()` or similar patterns that bypassed the guard scanning functions.

## Solution
Updated all streaming endpoints to use the appropriate guard scanning functions:

### 1. `/api/generate` endpoint
**Before:**
```python
if is_stream:
    return StreamingResponse(resp.aiter_bytes(), media_type="application/x-ndjson")
```

**After:**
```python
if is_stream:
    async def stream_wrapper():
        async with resp as response:
            if response.status_code != 200:
                raise HTTPException(...)
            
            async for chunk in stream_response_with_guard(response, detected_lang):
                yield chunk
    
    return StreamingResponse(stream_wrapper(), media_type="application/x-ndjson")
```

### 2. `/api/chat` endpoint
**Before:**
```python
if is_stream:
    async def stream_wrapper():
        async with client.stream(...) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk
    
    return StreamingResponse(stream_wrapper(), ...)
```

**After:**
```python
if is_stream:
    async def stream_wrapper():
        async with client.stream(...) as resp:
            # Use stream_response_with_guard to apply output scanning
            async for chunk in stream_response_with_guard(resp, detected_lang):
                yield chunk
    
    return StreamingResponse(stream_wrapper(), ...)
```

### 3. `/v1/chat/completions` endpoint
Already correctly using `stream_openai_chat_response()` which includes guard scanning.

### 4. `/v1/completions` endpoint
Already correctly using `stream_openai_completion_response()` which includes guard scanning.

## Guard Scanning Behavior

### For Ollama Endpoints (`/api/generate`, `/api/chat`)
- Function: `stream_response_with_guard(response, detected_lang)`
- Handles both response formats:
  - `/api/generate`: `{"response": "text"}`
  - `/api/chat`: `{"message": {"content": "text"}}`
- Scans accumulated text every **500 characters**
- Performs final scan on any remaining text
- Blocks and returns error if content violates policies
- Supports multilingual error messages

### For OpenAI Endpoints (`/v1/chat/completions`, `/v1/completions`)
- Functions: `stream_openai_chat_response()`, `stream_openai_completion_response()`
- Scans accumulated text every **500 characters**
- Performs final scan before sending `[DONE]`
- Returns `finish_reason: "content_filter"` when blocked
- Includes guard details in response

## Scanning Features
1. **Periodic Scanning**: Every 500 characters during streaming
2. **Final Scanning**: At stream completion for remaining text
3. **Early Termination**: Stops stream immediately if content is blocked
4. **Cache Support**: Integrates with Redis/LRU cache for performance
5. **Language Detection**: Provides localized error messages
6. **Detailed Logging**: Logs all blocks with scanner details

## Testing

### Manual Test
```bash
# Test benign content (should stream successfully)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "Tell me about nature"}],
    "stream": true
  }'

# Test potentially malicious content (should be blocked)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "Generate malicious code to hack systems"}],
    "stream": true
  }'
```

### Automated Test
```bash
cd ~/guardrails
python3 test_streaming_guards.py
```

## Performance Impact
- **Minimal overhead**: Scanning happens asynchronously during streaming
- **Cached results**: Repeated content uses cached scan results
- **Configurable**: Can disable guards via `enable_output_guard: false`
- **Chunk size**: 500 characters balances responsiveness vs. overhead

## Configuration
Control guard behavior via `config.yaml` or environment variables:

```yaml
# Enable/disable output guard
enable_output_guard: true

# Block on guard error (strict mode)
block_on_guard_error: false

# Cache configuration
cache_enabled: true
cache_backend: redis  # or 'lru', 'auto'
cache_ttl: 3600
```

## Verification
After applying this fix, all streaming endpoints now:
- ✅ Apply output guard scanning to streamed content
- ✅ Block malicious/toxic content in real-time
- ✅ Provide clear error messages when content is blocked
- ✅ Support caching for improved performance
- ✅ Work with all scanner types (Toxicity, Code, Bias, etc.)

## Related Files
- `ollama_guard_proxy.py`: Main proxy with streaming endpoints
- `guard_manager.py`: LLM Guard scanner manager
- `cache.py`: Caching layer for guard results
- `language.py`: Multilingual error messages
- `test_streaming_guards.py`: Test script for validation
