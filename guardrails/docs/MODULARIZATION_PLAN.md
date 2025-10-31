# Ollama Guard Proxy - Modularization Plan

## Overview
Splitting the 1971-line `ollama_guard_proxy.py` into maintainable, focused modules.

## Module Structure

### 1. **http_client.py** ✅ COMPLETE
- HTTP client management with connection pooling
- Singleton pattern for httpx.AsyncClient
- Request forwarding helpers
- JSON parsing utilities

### 2. **utils.py** ✅ COMPLETE
- `extract_client_ip()` - IP extraction from requests
- `extract_model_from_payload()` - Model name extraction
- `extract_text_from_payload()` - Prompt extraction
- `extract_text_from_response()` - Output extraction
- `combine_messages_text()` - Message list to string
- `build_ollama_options_from_openai_payload()` - OpenAI to Ollama mapping
- `extract_prompt_from_completion_payload()` - Completion prompt extraction

### 3. **streaming_handlers.py** ✅ COMPLETE
- `stream_response_with_guard()` - Ollama /api/generate & /api/chat streaming
- `stream_openai_chat_response()` - OpenAI chat completions streaming
- `stream_openai_completion_response()` - OpenAI text completions streaming
- `format_sse_event()` - Server-Sent Events formatting

### 4. **endpoints_ollama.py** 🔄 IN PROGRESS
Ollama-specific API endpoints:
- `/api/generate` - Text generation (streaming + non-streaming)
- `/api/chat` - Chat completions (streaming + non-streaming)
- `/api/pull` - Model pull (streaming)
- `/api/push` - Model push (streaming)
- `/api/create` - Model creation (streaming)
- `/api/tags` - List models
- `/api/show` - Show model info
- `/api/delete` - Delete model
- `/api/copy` - Copy model
- `/api/embed` - Generate embeddings
- `/api/ps` - List running models
- `/api/version` - Get Ollama version

### 5. **endpoints_openai.py** ⏳ TODO
OpenAI-compatible API endpoints:
- `/v1/chat/completions` - Chat completions (streaming + non-streaming)
- `/v1/completions` - Text completions (streaming + non-streaming)
- `/v1/embeddings` - Generate embeddings
- `/v1/models` - List models

### 6. **endpoints_admin.py** ⏳ TODO
Admin and monitoring endpoints:
- `/health` - Health check with metrics
- `/config` - Current configuration
- `/stats` - Statistics
- `/admin/cache/clear` - Clear cache
- `/admin/cache/cleanup` - Cleanup expired cache
- `/queue/stats` - Queue statistics
- `/queue/memory` - Memory information
- `/admin/queue/reset` - Reset queue stats
- `/admin/queue/update` - Update queue limits

### 7. **ollama_guard_proxy.py** (Main) ⏳ TODO - REFACTOR
After extraction, main file should contain only:
- FastAPI app initialization
- Global components (config, guard_manager, ip_whitelist, cache, concurrency_manager)
- Middleware (IP whitelist, request logging)
- Startup/shutdown handlers
- Entry point (`if __name__ == "__main__":`)
- Import routers from endpoint modules

Target: ~200-300 lines (down from 1971)

## Dependencies Between Modules

```
ollama_guard_proxy.py (main)
├── http_client.py
├── utils.py
├── streaming_handlers.py
│   ├── http_client.py
│   └── utils.py
├── endpoints_ollama.py
│   ├── http_client.py
│   ├── utils.py
│   ├── streaming_handlers.py
│   ├── guard_manager.py
│   ├── language.py
│   └── cache.py
├── endpoints_openai.py
│   ├── http_client.py
│   ├── utils.py
│   ├── streaming_handlers.py
│   ├── guard_manager.py
│   ├── language.py
│   └── cache.py
└── endpoints_admin.py
    ├── guard_manager.py
    ├── ip_whitelist.py
    ├── concurrency.py
    └── cache.py
```

## Implementation Status

| Module | Lines | Status | Progress |
|--------|-------|--------|----------|
| http_client.py | 75 | ✅ Complete | 100% |
| utils.py | 118 | ✅ Complete | 100% |
| streaming_handlers.py | 600+ | ✅ Complete | 100% |
| endpoints_ollama.py | ~600 | 🔄 In Progress | 50% |
| endpoints_openai.py | ~400 | ⏳ Not Started | 0% |
| endpoints_admin.py | ~150 | ⏳ Not Started | 0% |
| ollama_guard_proxy.py | ~250 | ⏳ Not Started | 0% |

**Overall Progress: 40%**

## Next Steps

1. Complete `endpoints_ollama.py` with all Ollama endpoints
2. Create `endpoints_openai.py` with OpenAI-compatible endpoints
3. Create `endpoints_admin.py` with admin/monitoring endpoints
4. Refactor main `ollama_guard_proxy.py` to use routers
5. Test all endpoints work correctly
6. Create architecture documentation

## Benefits

- **Maintainability**: Focused modules easier to understand and modify
- **Testability**: Can test individual modules in isolation
- **Reusability**: Modules can be reused in other projects
- **Collaboration**: Team members can work on different modules without conflicts
- **Navigation**: Easier to find specific functionality
- **Documentation**: Clearer separation of concerns

## Migration Notes

- All modules use dependency injection (pass config, guard_manager, etc. as parameters)
- Backwards compatible - same API endpoints, same behavior
- No breaking changes to external clients
- Streaming functionality preserved with immediate connection cleanup on blocking
