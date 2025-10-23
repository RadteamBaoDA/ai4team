# Ollama API Updates

## Summary
Updated `ollama_guard_proxy.py` to align with the official Ollama API documentation (https://docs.ollama.com/api)

## Changes Made

### 1. Endpoint Path Updates
- **`/v1/generate`** → **`/api/generate`** (Generate completions)
- **`/v1/chat/completions`** → **`/api/chat`** (Generate chat completions)

### 2. New Endpoints Added
The proxy now supports all major Ollama API endpoints:

#### Model Management
- `POST /api/pull` - Download a model from ollama library
- `POST /api/push` - Upload a model to ollama library  
- `POST /api/create` - Create a model from another model or GGUF file
- `DELETE /api/delete` - Delete a model
- `POST /api/copy` - Copy a model with a new name
- `GET /api/tags` - List all local models
- `POST /api/show` - Show model information

#### Generation & Embeddings
- `POST /api/generate` - Generate a completion (with LLM Guard)
- `POST /api/chat` - Generate a chat completion (with LLM Guard)
- `POST /api/embed` - Generate embeddings

#### System
- `GET /api/ps` - List running models
- `GET /api/version` - Get Ollama version

### 3. Response Format Updates
- **Chat endpoint**: Updated to use Ollama's native response format with `message` field instead of OpenAI's `choices` format
  - Before: `response['choices'][0]['message']['content']`
  - After: `response['message']['content']`

### 4. Documentation Updates
- Updated module docstring to remove IP filtering references
- Updated FastAPI app description
- Removed IP filter references from health check endpoint

### 5. Output Guard Integration
All endpoints maintain LLM Guard integration:
- **Input scanning**: `/api/generate` and `/api/chat` scan prompts
- **Output scanning**: `/api/generate` and `/api/chat` scan model outputs
- **NoCode scanner**: Detects and blocks code generation attempts
- **Other scanners**: Toxicity, malicious URLs, refusals, banned substrings

### 6. Streaming Support
The proxy maintains streaming support for:
- `/api/generate` - Streaming completion generation
- `/api/chat` - Streaming chat generation
- `/api/pull` - Model pull progress
- `/api/push` - Model push progress
- `/api/create` - Model creation progress

## Configuration
The proxy uses the same configuration for all endpoints:

```yaml
ollama_url: http://127.0.0.1:11434  # Ollama server URL
proxy_port: 8080                     # Proxy listening port
enable_input_guard: true             # Enable input scanning
enable_output_guard: true            # Enable output scanning
block_on_guard_error: false          # Block on guard errors
```

## Testing

### Generate Completion
```bash
curl http://localhost:8080/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### Chat Completion
```bash
curl http://localhost:8080/api/chat -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}'
```

### List Models
```bash
curl http://localhost:8080/api/tags
```

### Pull Model
```bash
curl http://localhost:8080/api/pull -d '{
  "model": "llama3.2"
}'
```

## Compatibility
- Fully compatible with Ollama API v1.0+
- All streaming and non-streaming modes supported
- Full multimodal support (images, tools, structured outputs)
- Context management and conversation memory preserved

## Security Features
✅ Input scanning for prompt injection, toxicity, secrets
✅ Output scanning for toxicity, code generation, malicious URLs
✅ Refusal detection
✅ Custom keyword filtering
✅ Streaming output scanning with periodic validation

## Statistics
- **Total endpoints**: 13 API endpoints
- **With input/output guard**: 2 (generate, chat)
- **Pass-through endpoints**: 11 (model management, embeddings, system)
- **Lines of code**: ~715
- **Output scanners**: 5 (BanSubstrings, Toxicity, MaliciousURLs, NoRefusal, NoCode)
