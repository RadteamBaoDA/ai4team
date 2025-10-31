# Ollama Guard Proxy - Module Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ollama_guard_proxy.py                        │
│                         (Main Entry)                             │
│  - FastAPI App Initialization                                    │
│  - Global Components (Config, Guards, Cache, etc.)              │
│  - Middleware (IP Whitelist, Logging)                           │
│  - Router Registration                                           │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ├─────────────┬─────────────┬─────────────┬───────────┐
            │             │             │             │           │
            ▼             ▼             ▼             ▼           ▼
    ┌──────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────┐  ┌────────┐
    │  Ollama  │  │   OpenAI    │  │  Admin   │  │ Stream  │  │ Utils  │
    │Endpoints │  │ Endpoints   │  │Endpoints │  │Handlers │  │        │
    │ (12 API) │  │  (4 API)    │  │ (9 API)  │  │         │  │        │
    └────┬─────┘  └──────┬──────┘  └────┬─────┘  └────┬────┘  └───┬────┘
         │               │               │             │           │
         └───────────────┴───────────────┴─────────────┴───────────┤
                                                                    │
                                                                    ▼
                                                            ┌──────────────┐
                                                            │ HTTP Client  │
                                                            │ (Connection  │
                                                            │   Pooling)   │
                                                            └──────────────┘
```

## Module Dependencies

```
┌─────────────────┐
│ ollama_guard    │
│   _proxy.py     │
│                 │
│ • FastAPI app   │
│ • Middleware    │
│ • Startup/      │
│   Shutdown      │
└────────┬────────┘
         │ imports & initializes
         │
         ├──────────────────────┬─────────────────────┬───────────────────┐
         │                      │                     │                   │
         ▼                      ▼                     ▼                   ▼
┌────────────────┐     ┌────────────────┐   ┌────────────────┐  ┌──────────────┐
│ endpoints_     │     │ endpoints_     │   │ endpoints_     │  │ streaming_   │
│   ollama.py    │     │   openai.py    │   │   admin.py     │  │   handlers.py│
├────────────────┤     ├────────────────┤   ├────────────────┤  ├──────────────┤
│ Factory Fn:    │     │ Factory Fn:    │   │ Factory Fn:    │  │ • stream_    │
│ create_ollama_ │     │ create_openai_ │   │ create_admin_  │  │   response   │
│   endpoints()  │     │   endpoints()  │   │   endpoints()  │  │ • stream_    │
│                │     │                │   │                │  │   openai_*   │
│ 12 endpoints:  │     │ 4 endpoints:   │   │ 9 endpoints:   │  │ • format_sse │
│ • /api/        │     │ • /v1/chat/    │   │ • /health      │  │              │
│   generate     │     │   completions  │   │ • /config      │  │              │
│ • /api/chat    │     │ • /v1/         │   │ • /stats       │  │              │
│ • /api/tags    │     │   completions  │   │ • /admin/*     │  │              │
│ • /api/pull    │     │ • /v1/         │   │ • /queue/*     │  │              │
│ • /api/push    │     │   embeddings   │   │                │  │              │
│ • /api/create  │     │ • /v1/models   │   │                │  │              │
│ • /api/show    │     │                │   │                │  │              │
│ • /api/delete  │     │                │   │                │  │              │
│ • /api/copy    │     │                │   │                │  │              │
│ • /api/embed   │     │                │   │                │  │              │
│ • /api/ps      │     │                │   │                │  │              │
│ • /api/version │     │                │   │                │  │              │
└───────┬────────┘     └───────┬────────┘   └───────┬────────┘  └──────┬───────┘
        │                      │                    │                  │
        │                      │                    │                  │
        └──────────────────────┴────────────────────┴──────────────────┤
                                                                        │
                    ┌───────────────────────────────────────────────────┤
                    │                                                   │
                    ▼                                                   ▼
           ┌────────────────┐                                  ┌────────────────┐
           │   utils.py     │                                  │ http_client.py │
           ├────────────────┤                                  ├────────────────┤
           │ • extract_     │                                  │ • get_http_    │
           │   client_ip    │                                  │   client()     │
           │ • extract_     │                                  │ • forward_     │
           │   model_*      │                                  │   request()    │
           │ • extract_     │                                  │ • safe_json()  │
           │   text_*       │                                  │ • close_http_  │
           │ • combine_     │                                  │   client()     │
           │   messages     │                                  │                │
           │ • build_       │                                  │ Singleton      │
           │   ollama_      │                                  │ HTTP client    │
           │   options      │                                  │ with pooling   │
           └────────────────┘                                  └────────────────┘
```

## Data Flow: Request Processing

### Example: POST /api/generate (Streaming)

```
1. Client Request
   │
   ▼
┌─────────────────────┐
│  FastAPI Middleware │
│  - IP Whitelist     │ ◄── ip_whitelist.py
│  - Request Logging  │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────┐
│ endpoints_ollama.py  │
│ proxy_generate()     │
└──────────┬───────────┘
           │
           ├─── Extract model & prompt ──► utils.py
           │
           ├─── Detect language ──────────► language.py
           │
           ├─── Scan input ───────────────► guard_manager.py
           │    (check cache first) ───────► cache.py
           │
           ├─── Forward to Ollama ────────► http_client.py
           │    (with concurrency) ────────► concurrency.py
           │
           ▼
┌──────────────────────┐
│ streaming_handlers.py│
│ stream_response_with │
│      _guard()        │
└──────────┬───────────┘
           │
           ├─── For each chunk:
           │    │
           │    ├─── Accumulate text
           │    │
           │    ├─── Scan output (every 500 chars) ──► guard_manager.py
           │    │    - If blocked: close connection
           │    │    - Send error chunk
           │    │
           │    └─── Yield chunk to client
           │
           └─── Final scan ───────────────► guard_manager.py
                (cache result) ───────────► cache.py
                │
                ▼
           Close connection
                │
                ▼
           Response to client
```

## Component Initialization Flow

```
┌────────────────────────┐
│  Application Startup   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Load Configuration    │
│  (config.py)           │
└───────────┬────────────┘
            │
            ├────────────────────────┐
            │                        │
            ▼                        ▼
┌─────────────────────┐   ┌──────────────────────┐
│  Initialize Guards  │   │  Initialize Cache    │
│  (guard_manager.py) │   │  (cache.py - Redis)  │
│  - Load scanners    │   │  - Connect to Redis  │
│  - Set device       │   │  - Test connection   │
└──────────┬──────────┘   └──────────┬───────────┘
           │                         │
           ├─────────────────────────┴────────────┐
           │                                      │
           ▼                                      ▼
┌────────────────────┐              ┌──────────────────────┐
│  Initialize        │              │  Initialize          │
│  Concurrency Mgr   │              │  IP Whitelist        │
│  - Auto-detect     │              │  - Load IPs          │
│  - Set limits      │              │  - Validate          │
└──────────┬─────────┘              └──────────┬───────────┘
           │                                   │
           └───────────────┬───────────────────┘
                           │
                           ▼
                ┌────────────────────┐
                │  Create Routers    │
                │  - Ollama          │
                │  - OpenAI          │
                │  - Admin           │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Register Routes   │
                │  app.include_router│
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Start HTTP Client │
                │  (connection pool)  │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Application Ready │
                └────────────────────┘
```

## Request Flow with Concurrency Control

```
Multiple Concurrent Requests
         │
         ├──── Request 1 (model: llama3)
         ├──── Request 2 (model: llama3)
         ├──── Request 3 (model: mistral)
         └──── Request 4 (model: llama3)
         │
         ▼
┌────────────────────────────────┐
│   Concurrency Manager          │
│   (concurrency.py)             │
│                                │
│   Model Queues:                │
│   ┌─────────────────┐          │
│   │ llama3: [R1,R2] │ ◄─ Parallel: 2    │
│   │       Queue:[R4]│ ◄─ Queue: 512     │
│   └─────────────────┘          │
│   ┌─────────────────┐          │
│   │ mistral: [R3]   │ ◄─ Parallel: 2    │
│   │       Queue:[]  │ ◄─ Queue: 512     │
│   └─────────────────┘          │
└───────────┬────────────────────┘
            │
            ├──► R1 Processing ──► Ollama (parallel)
            ├──► R2 Processing ──► Ollama (parallel)
            ├──► R3 Processing ──► Ollama (parallel)
            └──► R4 Queued (waiting for slot)
                 │
                 └──► When R1 or R2 completes, R4 starts
```

## Endpoint Distribution

```
Total: 25 Endpoints
│
├─── Ollama Endpoints (12) ───────────────── endpoints_ollama.py
│    ├─ POST   /api/generate
│    ├─ POST   /api/chat
│    ├─ POST   /api/pull
│    ├─ POST   /api/push
│    ├─ POST   /api/create
│    ├─ GET    /api/tags
│    ├─ POST   /api/show
│    ├─ DELETE /api/delete
│    ├─ POST   /api/copy
│    ├─ POST   /api/embed
│    ├─ GET    /api/ps
│    └─ GET    /api/version
│
├─── OpenAI Endpoints (4) ────────────────── endpoints_openai.py
│    ├─ POST   /v1/chat/completions
│    ├─ POST   /v1/completions
│    ├─ POST   /v1/embeddings
│    └─ POST   /v1/models
│
└─── Admin Endpoints (9) ─────────────────── endpoints_admin.py
     ├─ GET    /health
     ├─ GET    /config
     ├─ GET    /stats
     ├─ POST   /admin/cache/clear
     ├─ POST   /admin/cache/cleanup
     ├─ GET    /queue/stats
     ├─ GET    /queue/memory
     ├─ POST   /admin/queue/reset
     └─ POST   /admin/queue/update
```

## Guard Scanning Flow

```
┌──────────────┐
│ User Request │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│  Input Guard Scan   │ ◄─── guard_manager.py
│  - Check cache      │ ◄─── cache.py (Redis)
│  - Run scanners:    │
│    • PromptInjection│
│    • Toxicity       │
│    • Secrets        │
│    • Code          │
│  - Cache result     │
└──────┬──────────────┘
       │
       ├─── If Blocked ──► 403 Error Response
       │                   (with failed scanners)
       │
       └─── If Allowed ───►
                          │
                          ▼
                   ┌──────────────┐
                   │ Forward to   │
                   │   Ollama     │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────────┐
                   │ Ollama Response  │
                   └──────┬───────────┘
                          │
                          ▼
                   ┌─────────────────────┐
                   │  Output Guard Scan  │ ◄─── guard_manager.py
                   │  - Check cache      │ ◄─── cache.py (Redis)
                   │  - Run scanners:    │
                   │    • Toxicity       │
                   │    • Bias           │
                   │    • MaliciousURLs  │
                   │    • Code           │
                   │  - Cache result     │
                   └──────┬──────────────┘
                          │
                          ├─── If Blocked ──► 451 Error Response
                          │                   Close connection
                          │                   (with failed scanners)
                          │
                          └─── If Allowed ──► Return Response
```

## Cache Architecture

```
┌────────────────────┐
│  Guard Requests    │
└─────────┬──────────┘
          │
          ▼
┌─────────────────────────────┐
│     GuardCache              │
│     (cache.py)              │
│                             │
│  ┌────────────────────┐     │
│  │  Memory Cache      │     │     Fast local cache
│  │  (dict/LRU)        │─────┼───► for recent results
│  │  Max: 1000 entries │     │
│  │  TTL: 3600s        │     │
│  └────────────────────┘     │
│           │                 │
│           │ fallback        │
│           ▼                 │
│  ┌────────────────────┐     │
│  │  Redis Cache       │     │     Shared cache across
│  │  (distributed)     │─────┼───► multiple instances
│  │  Max: unlimited    │     │
│  │  TTL: 3600s        │     │
│  └────────────────────┘     │
└─────────────────────────────┘

Cache Keys:
  - Input:  "input:{hash(prompt)}"
  - Output: "output:{hash(text)}"

Cache Value:
  {
    "allowed": true/false,
    "scanners": {
      "scanner_name": {
        "passed": true/false,
        "reason": "...",
        "score": 0.95
      }
    },
    "timestamp": 1234567890
  }
```

## File Organization

```
guardrails/
│
├── ollama_guard_proxy.py      # Main entry (250 lines after refactor)
│   ├─ FastAPI app
│   ├─ Global initialization
│   ├─ Middleware
│   ├─ Router registration
│   └─ Entry point
│
├── http_client.py             # HTTP client (75 lines)
│   ├─ Connection pooling
│   ├─ Request forwarding
│   └─ JSON parsing
│
├── utils.py                   # Utilities (118 lines)
│   ├─ IP extraction
│   ├─ Text extraction
│   ├─ Payload mapping
│   └─ Helper functions
│
├── streaming_handlers.py      # Streaming (560 lines)
│   ├─ Ollama streaming
│   ├─ OpenAI streaming
│   ├─ Guard scanning
│   └─ Connection cleanup
│
├── endpoints_ollama.py        # Ollama endpoints (550 lines)
│   ├─ 12 API endpoints
│   ├─ Input/output scanning
│   ├─ Concurrency control
│   └─ Factory function
│
├── endpoints_openai.py        # OpenAI endpoints (520 lines)
│   ├─ 4 API endpoints
│   ├─ OpenAI compatibility
│   ├─ Streaming support
│   └─ Factory function
│
├── endpoints_admin.py         # Admin endpoints (140 lines)
│   ├─ 9 monitoring endpoints
│   ├─ Health checks
│   ├─ Statistics
│   └─ Factory function
│
├── config.py                  # Configuration
├── guard_manager.py           # LLM Guard integration
├── language.py                # Language detection
├── cache.py                   # Caching (Redis)
├── concurrency.py             # Concurrency control
├── ip_whitelist.py            # IP filtering
└── security.py                # Security features
```

## Benefits Summary

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| Main file size | 1971 lines | ~250 lines | 87% reduction |
| Largest module | 1971 lines | 560 lines | 71% reduction |
| Module count | 1 | 7 | Better organization |
| Avg module size | 1971 lines | 316 lines | 84% reduction |
| Testability | Low | High | Isolated modules |
| Reusability | Low | High | Portable components |
| Collaboration | Difficult | Easy | Clear boundaries |
| Extensibility | Hard | Easy | Modular structure |
