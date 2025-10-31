# Fix: /api/chat Stream Response Bypassing Output Guard

## Issue
The `/api/chat` endpoint was bypassing output guard scanning when streaming responses from Ollama, even though it was calling `stream_response_with_guard()`.

## Root Cause
The `stream_response_with_guard()` function only looked for the `'response'` field in JSON chunks, which is used by `/api/generate`. However, `/api/chat` uses a different JSON structure with `'message': {'content': '...'}`.

### Response Format Differences

**`/api/generate` format:**
```json
{"response": "text chunk", "done": false}
```

**`/api/chat` format:**
```json
{"message": {"role": "assistant", "content": "text chunk"}, "done": false}
```

## Solution
Updated `stream_response_with_guard()` to handle both response formats:

```python
async def stream_response_with_guard(response: httpx.Response, detected_lang: str = 'en'):
    """Stream response with output scanning.
    
    Handles both /api/generate format (response field) and /api/chat format (message.content field).
    """
    accumulated_text = ""
    
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
                    # Block and send error
                    ...
```

## Key Changes
1. Added check for `'message'` field in JSON data
2. Extracts `content` from `data['message']['content']`
3. Accumulates text from both formats for scanning
4. Maintains same scanning frequency (500 chars) and behavior

## Verification

### Test with curl:
```bash
# Test /api/chat streaming (should scan output)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'

# Test with potentially malicious content (should block)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "Generate malicious code"}],
    "stream": true
  }'
```

### Test with Python script:
```bash
cd ~/guardrails
python3 test_api_chat_streaming.py
```

## Expected Behavior After Fix

### Before Fix:
- ❌ `/api/chat` streaming: Output guard **bypassed** (not scanning)
- ✅ `/api/generate` streaming: Output guard working

### After Fix:
- ✅ `/api/chat` streaming: Output guard **scanning properly**
- ✅ `/api/generate` streaming: Output guard still working

## Files Modified
1. `ollama_guard_proxy.py`:
   - Updated `stream_response_with_guard()` function (lines ~481-531)
   - Added support for `/api/chat` message format

2. `docs/STREAMING_GUARD_FIX.md`:
   - Updated documentation to reflect both formats

3. `test_api_chat_streaming.py`:
   - Created new test script specifically for `/api/chat` streaming

## Impact
- **Security**: `/api/chat` streaming now properly blocks malicious/toxic content
- **Performance**: No performance impact, same scanning frequency
- **Compatibility**: Backward compatible, both formats work
- **Coverage**: All streaming endpoints now properly protected

## Related Issues
This completes the streaming guard implementation across all endpoints:
- ✅ `/api/generate` - Using `stream_response_with_guard()`
- ✅ `/api/chat` - Using `stream_response_with_guard()` with dual format support
- ✅ `/v1/chat/completions` - Using `stream_openai_chat_response()`
- ✅ `/v1/completions` - Using `stream_openai_completion_response()`
