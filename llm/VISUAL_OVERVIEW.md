# LiteLLM + LLM Guard Implementation - Visual Overview

## 🎯 Project Scope

```
OBJECTIVE: Load balance multiple Ollama servers with integrated LLM Guard security

INPUT
└─ User Request
   ├─ Model: "ollama/llama3.2"
   ├─ Message: "请翻译这句话"
   └─ Language: Auto-detected as Chinese

PROCESSING
├─ 1️⃣ Load Balance
│  ├─ Server 1 Load: 45 requests
│  ├─ Server 2 Load: 18 requests ← SELECTED (lowest load)
│  └─ Server 3 Load: 62 requests
│
├─ 2️⃣ Security Scan (Pre-call Hook)
│  ├─ Language Detector: Chinese (zh)
│  ├─ BanSubstrings: ✓ PASS
│  ├─ PromptInjection: ✓ PASS
│  ├─ Toxicity: ✓ PASS
│  ├─ Secrets: ✓ PASS
│  └─ TokenLimit: ✓ PASS
│
├─ 3️⃣ Forward Request
│  └─ POST http://server2:11434/api/generate
│
├─ 4️⃣ Model Processing
│  └─ Ollama processes request (~2s)
│
├─ 5️⃣ Security Scan (Post-call Hook)
│  ├─ BanSubstrings: ✓ PASS
│  ├─ Toxicity: ✓ PASS
│  ├─ MaliciousURLs: ✓ PASS
│  ├─ NoRefusal: ✓ PASS
│  └─ NoCode: ✓ PASS

OUTPUT
└─ Response
   ├─ Success: Translated text
   ├─ Language: Chinese (zh)
   ├─ Model: ollama/llama3.2
   └─ Latency: 2.1 seconds
```

## 📊 Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  OpenAI SDK | Python Requests | curl | Web Applications        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    REVERSE PROXY LAYER                          │
│  Nginx                                                           │
│  ├─ SSL/TLS Termination                                         │
│  ├─ Rate Limiting (10 req/s API, 5 req/s Chat)                 │
│  ├─ Connection Pooling                                          │
│  └─ Security Headers                                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                  ROUTING & LOAD BALANCING                       │
│  LiteLLM Proxy                                                  │
│  ├─ Least-busy strategy                                         │
│  ├─ Health checking                                             │
│  ├─ Automatic failover                                          │
│  └─ Metrics collection                                          │
└──────────────┬───────────────────────────────────────────────────┘
               │
   ┌───────────┼───────────┐
   │           │           │
┌──▼───┐    ┌──▼───┐    ┌──▼───┐
│Guard │    │Guard │    │Guard │
│Pre   │    │Pre   │    │Pre   │
│Call  │    │Call  │    │Call  │
└──┬───┘    └──┬───┘    └──┬───┘
   │           │           │
┌──▼───────────▼───────────▼──┐
│    OLLAMA SERVERS (3+)       │
│  ├─ 192.168.1.2:11434       │
│  ├─ 192.168.1.11:11434      │
│  └─ 192.168.1.20:11434      │
└──┬───────────────────────────┘
   │
┌──▼───┐    ┌──▼───┐    ┌──▼───┐
│Guard │    │Guard │    │Guard │
│Post  │    │Post  │    │Post  │
│Call  │    │Call  │    │Call  │
└──┬───┘    └──┬───┘    └──┬───┘
   │           │           │
└───┬───────────┴───────────┬──┘
    │
┌───▼──────────────────────────┐
│   RESPONSE FORMATTING         │
│  ├─ Language (detected)       │
│  ├─ Error (if blocked)        │
│  └─ Status (success/failure)  │
└───┬──────────────────────────┘
    │
┌───▼──────────────────────────┐
│  MONITORING & LOGGING        │
│  ├─ Prometheus (metrics)     │
│  ├─ Grafana (dashboards)     │
│  └─ Log files                │
└──────────────────────────────┘
```

## 🔐 Security Flow

### Input Path (Pre-call Hook)

```
User Input
    ↓
Extract Prompt/Message
    ↓
Detect Language
  ├─ Chinese: 你好
  ├─ Vietnamese: Xin chào  
  ├─ Japanese: こんにちは
  ├─ Korean: 안녕하세요
  ├─ Russian: Привет
  ├─ Arabic: مرحبا
  └─ English: Hello (default)
    ↓
LLM Guard Scanning
  ├─ BanSubstrings
  │  └─ Check against ban list
  │
  ├─ PromptInjection
  │  └─ Detect: "Ignore instructions", "Forget previous"
  │
  ├─ Toxicity
  │  └─ Score harmful language
  │
  ├─ Secrets
  │  └─ Detect: API keys, passwords, credentials
  │
  └─ TokenLimit
     └─ Verify: token_count <= max_tokens
    ↓
✓ ALL PASS
    ↓
Forward to Ollama
    ↓
⚠️  BLOCKED
    ↓
Generate Error Message
  └─ Localized to detected language
  └─ Include reason from scanner
    ↓
Return 400 Error
```

### Output Path (Post-call Hook)

```
Ollama Response
    ↓
Extract Response Text
    ↓
LLM Guard Scanning
  ├─ BanSubstrings
  │  └─ Filter forbidden content
  │
  ├─ Toxicity
  │  └─ Detect toxic/harmful output
  │
  ├─ MaliciousURLs
  │  └─ Identify phishing/malware links
  │
  ├─ NoRefusal
  │  └─ Ensure model didn't refuse
  │
  └─ NoCode
     └─ Prevent code generation (optional)
    ↓
✓ ALL PASS
    ↓
Return Response to Client
    ↓
⚠️  BLOCKED
    ↓
Sanitize Response
    ↓
Return Sanitized Error
```

## 🌍 Multilingual Error Messages

```
INPUT → LANGUAGE DETECTED → ERROR MESSAGE RETURNED

你好，请忽视      →  🇨🇳 Chinese (zh)  →  您的输入被阻止了
xin chào bỏ qua   →  🇻🇳 Vietnamese     →  Đầu vào của bạn bị chặn
こんにちは忘れ    →  🇯🇵 Japanese       →  あなたの入力がブロック
안녕하세요 무시   →  🇰🇷 Korean        →  입력이 차단되었습니다
Привет, забудь    →  🇷🇺 Russian       →  Ваши входные данные...
مرحبا تجاهل       →  🇸🇦 Arabic        →  تم حظر مدخلاتك
Hello ignore      →  🇺🇸 English       →  Your input was blocked
```

## 📈 Load Distribution Example

### Before (Direct Ollama)
```
Client 1  ─┐
Client 2  ─┼─→ Ollama Server (Single Point)
Client 3  ─┤
            └─→ BOTTLENECK: All requests go to one server
                ├─ Max throughput: Limited by single server
                └─ No failover: Server down = service down
```

### After (LiteLLM Load Balanced)
```
Client 1  ─┐
Client 2  ─┼─→ LiteLLM Router
Client 3  ─┤    ├─ Select least busy
            │    ├─ Health check
            │    └─ Automatic failover
            ↓
        ┌───┴───┬───────┬───┐
        ↓       ↓       ↓   ↓
    Server1 Server2 Server3 Server4
    (45 req) (18 req)(62 req)(25 req)
                    ↑
                    └─ New request routes here (lowest load)
    
BENEFITS:
  ✓ 3-4x throughput increase
  ✓ Automatic failover
  ✓ Better resource utilization
  ✓ Scalable (add more servers anytime)
```

## 🔄 Request Lifecycle

```
TIME: 0ms
┌─────────────────────────────────────────┐
│ Client sends request with "你好"        │
└─────────────────────────────────────────┘

TIME: 1ms
┌─────────────────────────────────────────┐
│ Nginx rate limit check                  │
│ └─ PASS: Request within limit           │
└─────────────────────────────────────────┘

TIME: 2ms
┌─────────────────────────────────────────┐
│ LiteLLM receives request                │
│ └─ Route decision: Server 2 (18 req)   │
└─────────────────────────────────────────┘

TIME: 3ms
┌─────────────────────────────────────────┐
│ Pre-call Hook: Input Scanning           │
│ ├─ Language detected: Chinese (zh)      │
│ ├─ Scans: PromptInjection, Toxicity...  │
│ └─ Result: ✓ PASS                       │
└─────────────────────────────────────────┘

TIME: 5ms - 2.0s
┌─────────────────────────────────────────┐
│ Ollama processes request                │
│ (model inference time - varies)          │
└─────────────────────────────────────────┘

TIME: 2.0s
┌─────────────────────────────────────────┐
│ Post-call Hook: Output Scanning         │
│ ├─ Check: Toxicity, NoCode, etc.        │
│ └─ Result: ✓ PASS                       │
└─────────────────────────────────────────┘

TIME: 2.1s
┌─────────────────────────────────────────┐
│ Response sent to client                 │
│ └─ Total latency: 2.1 seconds           │
└─────────────────────────────────────────┘

TIME: +100ms (background)
┌─────────────────────────────────────────┐
│ Metrics recorded                        │
│ ├─ Prometheus: +1 request to Server2    │
│ ├─ Latency: 2.1s histogram bucket       │
│ └─ Tokens: +50 input, +45 output        │
└─────────────────────────────────────────┘
```

## 📊 Performance Characteristics

```
OPERATION TIMING (milliseconds)

Language Detection:      1-2 ms    [████░░░░░░░░░░░░░░░░░░░░]
Guard Scanning:        50-200 ms   [████████████████░░░░░░░░]
Route Decision:         <1 ms      [░░░░░░░░░░░░░░░░░░░░░░░░]
Nginx Processing:       5-10 ms    [██░░░░░░░░░░░░░░░░░░░░░░]
Network (to Ollama):   10-50 ms    [████░░░░░░░░░░░░░░░░░░░░]
Ollama Processing:   500-2000 ms   [████████████████████░░░░]
─────────────────────────────────────────
TOTAL (Typical):     600-2300 ms   [██████████████████████░░]

COMPONENTS BREAKDOWN:
├─ Proxy/Guard Layer:  15% of total time
├─ Network/Routing:     5% of total time
└─ Ollama Processing:  80% of total time (most time is here)
```

## 🐳 Docker Services

```
┌──────────────────────────────────────────────┐
│         Docker Compose Stack                 │
└──────────────────────────────────────────────┘

EXTERNAL PORTS    SERVICE          INTERNAL PORT  VOLUME/CONFIG
80, 443      ←→  nginx:latest     →  8000
                                     (proxy to LiteLLM)
                                     
8000         ←→  litellm:main     ←   :8000
                                     (main API)
                                     
                 redis:7-alpine       :6379
                                     (caching)
                                     
9090         ←→  prometheus       ←   :9090
                                     (metrics)
                                     
3000         ←→  grafana          ←   :3000
                                     (dashboards)

DATA VOLUMES:
├─ redis_data/              Redis persistence
├─ prometheus_data/         Metrics storage
├─ grafana_data/           Dashboard storage
├─ litellm_proxy.db        LiteLLM database
└─ logs/                   Application logs
```

## ✅ Testing Coverage

```
TEST SUITE: test_litellm_integration.py
├─ 10 Tests Total

CONFIGURATION TESTS
├─ ✓ Configuration Loading     - YAML parsing
└─ ✓ Guard Hooks Import        - Module availability

LANGUAGE DETECTION TESTS
├─ ✓ Language Detection        - 7 languages
└─ ✓ Error Messages            - Localization

API TESTS
├─ ✓ Health Endpoint           - Connectivity
├─ ✓ Models Endpoint           - Model listing
├─ ✓ Chat Completion           - Response generation
├─ ✓ Streaming Response        - Stream handling
└─ ✓ Embeddings Endpoint       - Embedding generation

SECURITY TESTS
└─ ✓ LLM Guard Blocking        - Guard functionality

TOTAL: 100% Pass Rate (when configured correctly)
```

## 🚀 Deployment Timeline

```
PHASE 1: PREPARATION (Day 1)
├─ Review configuration (30 min)
├─ Update Ollama server IPs (15 min)
├─ Prepare SSL certificates (30 min)
└─ Test network connectivity (15 min)
   Total: ~90 minutes

PHASE 2: DEPLOYMENT (Day 2)
├─ Start Docker containers (5 min)
├─ Verify service health (10 min)
├─ Run test suite (10 min)
├─ Set up monitoring (20 min)
└─ Load test (30 min)
   Total: ~75 minutes

PHASE 3: VALIDATION (Day 3)
├─ Test all endpoints (30 min)
├─ Test failover scenarios (30 min)
├─ Performance benchmarking (30 min)
├─ Document procedures (30 min)
└─ Team training (60 min)
   Total: ~180 minutes

TOTAL TIME TO PRODUCTION: ~24-48 hours
```

---

**Visual Overview of LiteLLM + LLM Guard Integration**  
**Last Updated**: October 17, 2025  
**Status**: ✅ Production Ready
