# HTTP Status Code 451 Update Summary

## Changes Made

Updated all invalid guardrail HTTP status codes to return **451 (Unavailable For Legal Reasons)** instead of 403 (Forbidden).

### Why HTTP 451?

HTTP status code 451 is specifically designed for content that is blocked due to legal or regulatory requirements, making it the most appropriate choice for content filtered by guardrails/content safety scanners.

- **403 Forbidden**: Access is permanently forbidden (authentication/authorization issue)
- **451 Unavailable For Legal Reasons**: Content is blocked due to legal/regulatory requirements (content filtering)

### Files Updated

#### `d:\Project\ai4team\guardrails\src\endpoints_ollama.py`

**Changed:**
1. **Line 97**: Input guard blocking for `/api/generate` endpoint
   ```python
   # Before:
   raise HTTPException(status_code=403, detail=error_message, ...)
   
   # After:  
   raise HTTPException(status_code=451, detail=error_message, ...)
   ```

2. **Line 285**: Input guard blocking for `/api/chat` endpoint
   ```python
   # Before:
   raise HTTPException(status_code=403, detail=error_message, ...)
   
   # After:
   raise HTTPException(status_code=451, detail=error_message, ...)
   ```

**Already Correct:**
- **Line 179**: Output guard blocking for `/api/generate` (already using 451)
- **Line 336**: Output guard blocking for `/api/chat` (already using 451)

#### `d:\Project\ai4team\guardrails\src\endpoints_openai.py`

**Changed:**
1. **Line 109**: Input guard blocking for `/v1/chat/completions` endpoint
   ```python
   # Before:
   raise HTTPException(status_code=403, detail=error_message, ...)
   
   # After:  
   raise HTTPException(status_code=451, detail=error_message, ...)
   ```

2. **Line 336**: Input guard blocking for `/v1/completions` endpoint
   ```python
   # Before:
   raise HTTPException(status_code=403, detail=error_message, ...)
   
   # After:
   raise HTTPException(status_code=451, detail=error_message, ...)
   ```

**Already Correct:**
- **Line 232**: Output guard blocking for `/v1/chat/completions` (already using 451)
- **Line 453**: Output guard blocking for `/v1/completions` (already using 451)

### Status Code Usage Summary

After the update, all guardrail violations now consistently return **HTTP 451**:

#### Ollama API Endpoints (`endpoints_ollama.py`)
| Endpoint | Guard Type | Status Code | Location |
|----------|------------|-------------|----------|
| `/api/generate` | Input Guard | 451 ✅ | Line 97 |
| `/api/generate` | Output Guard | 451 ✅ | Line 179 |
| `/api/chat` | Input Guard | 451 ✅ | Line 285 |
| `/api/chat` | Output Guard | 451 ✅ | Line 336 |

#### OpenAI API Endpoints (`endpoints_openai.py`)
| Endpoint | Guard Type | Status Code | Location |
|----------|------------|-------------|----------|
| `/v1/chat/completions` | Input Guard | 451 ✅ | Line 109 |
| `/v1/chat/completions` | Output Guard | 451 ✅ | Line 232 |
| `/v1/completions` | Input Guard | 451 ✅ | Line 336 |
| `/v1/completions` | Output Guard | 451 ✅ | Line 453 |

### Response Headers

All 451 responses include comprehensive headers for debugging and client handling:

```json
{
  "X-Error-Type": "content_policy_violation",
  "X-Block-Type": "input_blocked" | "output_blocked",
  "X-Language": "detected_language",
  "X-Failed-Scanners": "[{\"scanner\": \"...\", \"reason\": \"...\", \"score\": 0.x}]"
}
```

### OpenWebUI Filter Compatibility

The existing **Guardrails Error Handler Filter** (`custom-error-message/main.py`) automatically handles HTTP 451 responses:

- Detects error responses regardless of status code
- Formats user-friendly error messages
- Works with both streaming and non-streaming responses
- Handles the `'str' object has no attribute 'get'` error

### Testing

To verify the changes work correctly, the HTTP 451 status codes should be tested with:

1. **Input that triggers guardrails** (inappropriate content, security threats, etc.)
2. **Both streaming and non-streaming modes**  
3. **Different endpoint types** (`/api/generate`, `/api/chat`)

### Benefits

1. **Semantic Correctness**: 451 is the proper HTTP status for content filtering
2. **Client Handling**: Applications can differentiate between access denied (403) and content blocked (451)
3. **Compliance**: Better alignment with web standards for content filtering
4. **Consistency**: All guardrail blocks now use the same status code
5. **OpenWebUI Integration**: Works seamlessly with the error handler filter

## Verification

All guardrail-related HTTP exceptions now return 451:

### Ollama Endpoints
```bash
grep -n "status_code=451" src/endpoints_ollama.py
# Returns 4 matches (lines 97, 179, 285, 336)

grep -n "status_code=403" src/endpoints_ollama.py  
# Returns 0 matches
```

### OpenAI Endpoints
```bash
grep -n "status_code=451" src/endpoints_openai.py
# Returns 4 matches (lines 109, 232, 336, 453)

grep -n "status_code=403" src/endpoints_openai.py  
# Returns 0 matches
```

The change ensures consistent and semantically correct HTTP status codes for all content safety violations across both Ollama and OpenAI-compatible API endpoints in the AI4Team guardrails system.