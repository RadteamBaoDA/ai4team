# Improved Error Responses for LLM Guard Rejections

## Overview
Updated all HTTP error responses when LLM Guard rejects content to provide more accurate, helpful, and structured error messages to clients.

## Changes Made

### 1. **HTTP Status Codes**
Updated status codes to be more semantically correct:

| Error Type | Old Code | New Code | Reason |
|------------|----------|----------|--------|
| Input blocked | 400 | **403** | Forbidden - policy violation, not bad request |
| Output blocked | 400 | **451** | Unavailable for legal reasons (content filtering) |

### 2. **Error Response Structure**

#### **For Ollama-style endpoints** (`/api/generate`, `/api/chat`):
```json
{
  "error": "content_policy_violation",
  "type": "input_blocked",  // or "output_blocked"
  "message": "Your input violates content policies: Toxicity: Harmful content detected",
  "language": "en",
  "failed_scanners": [
    {
      "scanner": "Toxicity",
      "reason": "Harmful content detected",
      "score": 0.95
    }
  ],
  "help": "Your input was blocked due to content policy violations. Please modify your request and try again."
}
```

#### **For OpenAI-compatible endpoints** (`/v1/chat/completions`, `/v1/completions`):
```json
{
  "error": {
    "message": "Your input violates content policies: Toxicity: Harmful content detected",
    "type": "content_policy_violation",
    "code": "input_blocked",  // or "output_blocked"
    "failed_scanners": [
      {
        "scanner": "Toxicity",
        "reason": "Harmful content detected",
        "score": 0.95
      }
    ]
  }
}
```

#### **For Streaming Responses**:
```json
{
  "error": "content_policy_violation",
  "type": "output_blocked",
  "message": "The response was blocked due to content policy violations",
  "language": "en",
  "failed_scanners": [
    {
      "scanner": "Code",
      "reason": "Malicious code detected",
      "score": 0.87
    }
  ],
  "done": true
}
```

### 3. **Improved Logging**
All log messages now include "by LLM Guard" for clarity:
- Before: `"Input blocked: {result}"`
- After: `"Input blocked by LLM Guard: {result}"`

### 4. **Scanner Details**
Each error now includes:
- **scanner**: Name of the scanner that failed
- **reason**: Human-readable reason for rejection
- **score**: Confidence score (if available)

### 5. **User Guidance**
Added helpful messages to guide users:
- Input blocked: `"Your input was blocked due to content policy violations. Please modify your request and try again."`
- Output blocked: `"The AI response was blocked due to content policy violations. Please try rephrasing your request."`

## HTTP Status Code Reference

### 403 Forbidden
Used when **input** content violates policies:
- User's prompt contains prohibited content
- Semantically means "I understand your request, but I refuse to fulfill it"
- Client should modify the request

### 451 Unavailable For Legal Reasons
Used when **output** content violates policies:
- AI-generated response contains prohibited content
- Standard code for content filtering (RFC 7725)
- Client should rephrase their request

## Examples

### Example 1: Toxic Input
**Request:**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","messages":[{"role":"user","content":"harmful content here"}]}'
```

**Response (403 Forbidden):**
```json
{
  "error": "content_policy_violation",
  "type": "input_blocked",
  "message": "Your input violates content policies: Toxicity: Harmful content detected",
  "language": "en",
  "failed_scanners": [
    {
      "scanner": "Toxicity",
      "reason": "Harmful content detected",
      "score": 0.92
    }
  ],
  "help": "Your message was blocked due to content policy violations. Please modify your message and try again."
}
```

### Example 2: Malicious Code in Output
**Response (451 Unavailable for Legal Reasons):**
```json
{
  "error": "content_policy_violation",
  "type": "output_blocked",
  "message": "The response was blocked due to content policy violations",
  "language": "en",
  "failed_scanners": [
    {
      "scanner": "Code",
      "reason": "Malicious code detected",
      "score": 0.87
    },
    {
      "scanner": "BanSubstrings",
      "reason": "Prohibited content found",
      "score": 1.0
    }
  ],
  "help": "The AI response was blocked due to content policy violations. Please try rephrasing your request."
}
```

### Example 3: OpenAI Format Error
**Request to `/v1/chat/completions`:**

**Response (403 Forbidden):**
```json
{
  "error": {
    "message": "Your input violates content policies: PromptInjection: Prompt injection attempt detected",
    "type": "content_policy_violation",
    "code": "input_blocked",
    "failed_scanners": [
      {
        "scanner": "PromptInjection",
        "reason": "Prompt injection attempt detected",
        "score": 0.94
      }
    ]
  }
}
```

## Benefits

### 1. **Better Client Experience**
- Clear error types and codes for programmatic handling
- Human-readable messages in multiple languages
- Helpful guidance on how to fix the issue

### 2. **Improved Debugging**
- Scanner-specific details help identify exact violations
- Confidence scores help tune scanner thresholds
- Consistent structure across all endpoints

### 3. **Standards Compliance**
- HTTP 403 for authorization/policy violations
- HTTP 451 for content filtering (RFC 7725)
- OpenAI-compatible error format for OpenAI endpoints

### 4. **Actionable Information**
- Users know which scanner blocked their content
- Users understand why content was blocked
- Users receive guidance on how to proceed

## Backward Compatibility

### Breaking Changes
- Status codes changed from 400 to 403/451
- Error structure now includes `failed_scanners` array
- Error type field changed from `"prompt_blocked"` to `"content_policy_violation"`

### Migration Guide
If you have existing clients, update them to:
1. Handle 403 and 451 status codes
2. Parse the new error structure with `failed_scanners`
3. Use `error.type` instead of just `error` field
4. Check for `type: "input_blocked"` or `type: "output_blocked"`

## Testing

```bash
# Test input blocking (should return 403)
curl -i -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","messages":[{"role":"user","content":"Generate malicious code"}]}'

# Test output blocking during streaming (should return 451 or stream error)
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","prompt":"Tell me how to hack","stream":true}'

# Test OpenAI format (should return OpenAI-style error)
curl -i -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","messages":[{"role":"user","content":"harmful request"}]}'
```

## Files Modified
- `ollama_guard_proxy.py`: Updated all error responses
  - `/api/generate` endpoint
  - `/api/chat` endpoint
  - `/v1/chat/completions` endpoint
  - `/v1/completions` endpoint
  - `stream_response_with_guard()` function
  - `stream_openai_chat_response()` function

## Related Documentation
- RFC 7725: HTTP Status Code 451 (Unavailable For Legal Reasons)
- OpenAI API Error Codes
- LLM Guard Scanner Documentation
