# Ollama Guard Proxy - Visual Guide

## Project Structure

```
guardrails/
│
├─ Core Application
│  ├── ollama_guard_proxy.py ────── Main FastAPI application (700+ lines)
│  ├── client_example.py ────────── Python client & CLI (300+ lines)
│  └── requirements.txt ──────────── Python dependencies
│
├─ Docker & Deployment
│  ├── Dockerfile ─────────────────── Container image definition
│  ├── docker-compose.yml ───────── Service orchestration
│  └── nginx-guard.conf ──────────── Nginx reverse proxy config
│
├─ Configuration
│  └── config.example.yaml ──────── Configuration template
│
└─ Documentation
   ├── README_SOLUTION.md ───────── Complete solution summary
   ├── SOLUTION.md ──────────────── Architecture & overview
   ├── USAGE.md ────────────────── User guide & examples
   ├── DEPLOYMENT.md ───────────── Production deployment
   ├── TROUBLESHOOTING.md ──────── Problem solving
   ├── QUICKREF.md ──────────────── Quick reference
   ├── INDEX.md ─────────────────── File index
   └── README ──────────────────── Original LLM Guard docs
```

---

## Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT APPLICATION                           │
│  (curl, Python client, web app, mobile app, etc.)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP/HTTPS Request
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       NGINX REVERSE PROXY                           │
│  • Port 80 (HTTP redirect to HTTPS)                                │
│  • Port 443 (HTTPS with SSL/TLS)                                   │
│  • Load balancing across instances                                 │
│  • Security headers                                                │
│  • Buffer optimization                                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Internal routing
                             ▼
     ┌──────────────────────────────────────────────────────┐
     │   OLLAMA GUARD PROXY INSTANCE (FastAPI)             │
     │                                                       │
     │  ┌────────────────────────────────────────────────┐ │
     │  │  1. REQUEST PARSING                           │ │
     │  │     • Parse JSON payload                      │ │
     │  │     • Extract client IP                       │ │
     │  │     • Log request metadata                    │ │
     │  └────────────────────────────────────────────────┘ │
     │                       │                              │
     │                       ▼                              │
     │  ┌────────────────────────────────────────────────┐ │
     │  │  2. IP ACCESS CONTROL                         │ │
     │  │     • Check IP whitelist                      │ │
     │  │     • Check IP blacklist                      │ │
     │  │     • Support CIDR ranges                     │ │
     │  │     • X-Forwarded-For handling               │ │
     │  │     ✗ DENY if not allowed                    │ │
     │  └────────────────────────────────────────────────┘ │
     │                       │                              │
     │                       ▼                              │
     │  ┌────────────────────────────────────────────────┐ │
     │  │  3. INPUT GUARD (LLM Guard Scanners)          │ │
     │  │     • PromptInjection detection               │ │
     │  │     • Toxicity analysis                       │ │
     │  │     • Secret detection (API keys, etc.)       │ │
     │  │     • Code injection prevention               │ │
     │  │     • Token limit enforcement                 │ │
     │  │     • Custom substring banning                │ │
     │  │     ✗ BLOCK if violations found              │ │
     │  └────────────────────────────────────────────────┘ │
     │                       │                              │
     │                       ▼                              │
     │  ┌────────────────────────────────────────────────┐ │
     │  │  4. FORWARD TO OLLAMA                         │ │
     │  │     • HTTP POST request                       │ │
     │  │     • Stream handling                         │ │
     │  │     • Error handling                          │ │
     │  └────────────────────────────────────────────────┘ │
     │                       │                              │
     └───────────────────────┼──────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OLLAMA BACKEND SERVICE                          │
│  • Model inference                                                 │
│  • Response generation (streaming or complete)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Response
                             ▼
     ┌──────────────────────────────────────────────────────┐
     │   OLLAMA GUARD PROXY INSTANCE (FastAPI) - Continue  │
     │                                                       │
     │  ┌────────────────────────────────────────────────┐ │
     │  │  5. OUTPUT GUARD (LLM Guard Scanners)          │ │
     │  │     (For streaming: check per chunk)           │ │
     │  │     (For complete: check full response)        │ │
     │  │     • Toxicity checking                        │ │
     │  │     • Bias detection                           │ │
     │  │     • Malicious URL detection                  │ │
     │  │     • Refusal pattern detection                │ │
     │  │     • Custom substring banning                 │ │
     │  │     ✗ BLOCK if violations found              │ │
     │  └────────────────────────────────────────────────┘ │
     │                       │                              │
     │                       ▼                              │
     │  ┌────────────────────────────────────────────────┐ │
     │  │  6. RESPONSE RETURN                           │ │
     │  │     • Format response                         │ │
     │  │     • Log metrics                             │ │
     │  │     • Stream or send complete                 │ │
     │  └────────────────────────────────────────────────┘ │
     │                       │                              │
     └───────────────────────┼──────────────────────────────┘
                             │
                             │ Response
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       NGINX REVERSE PROXY                           │
│  • Buffer and stream response                                      │
│  • Apply security headers                                          │
│  • Log access                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP/HTTPS Response
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT APPLICATION                           │
│  (Receives guarded, secure response)                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
INPUT VALIDATION PIPELINE
─────────────────────────

Prompt/Request
    │
    ├──→ BanSubstrings Scanner ──→ ✓/✗
    │
    ├──→ PromptInjection Scanner ──→ ✓/✗
    │
    ├──→ Toxicity Scanner ──→ ✓/✗
    │
    ├──→ Secrets Scanner ──→ ✓/✗
    │
    ├──→ Code Scanner ──→ ✓/✗
    │
    └──→ TokenLimit Scanner ──→ ✓/✗
            │
            └──→ All scanners passed? → Forward to Ollama
                │
                └──→ Any failed? → Block & return error


OUTPUT VALIDATION PIPELINE
──────────────────────────

Response/Output
    │
    ├──→ BanSubstrings Scanner ──→ ✓/✗
    │
    ├──→ Toxicity Scanner ──→ ✓/✗
    │
    ├──→ MaliciousURLs Scanner ──→ ✓/✗
    │
    ├──→ NoRefusal Scanner ──→ ✓/✗
    │
    ├──→ Bias Scanner ──→ ✓/✗
    │
    └──→ Deanonymize Scanner ──→ ✓/✗
            │
            └──→ All scanners passed? → Return to client
                │
                └──→ Any failed? → Block & return error


IP ACCESS CONTROL LOGIC
───────────────────────

Request with Client IP
    │
    ├──→ Extract IP from request
    │    • Direct connection: request.client.host
    │    • X-Real-IP header
    │    • X-Forwarded-For header
    │
    ├──→ Parse as IP Address
    │
    ├──→ Check Blacklist
    │    └──→ IP in blacklist? → ✗ DENY
    │
    ├──→ Check Whitelist
    │    ├──→ Whitelist defined?
    │    │   ├──→ Yes: IP in whitelist? → ✗ DENY if not
    │    │   └──→ No: allow all
    │
    └──→ ✓ ALLOW request
```

---

## Deployment Architecture Options

### Option 1: Development (Single Instance)

```
┌──────────────────────────────┐
│  Your Machine / Laptop       │
│                              │
│  ┌────────────────────────┐ │
│  │   Ollama               │ │
│  │   Port: 11434          │ │
│  └────────────────────────┘ │
│            ↑                │
│            │ localhost      │
│            ↓                │
│  ┌────────────────────────┐ │
│  │ Guard Proxy            │ │
│  │ Port: 8080             │ │
│  └────────────────────────┘ │
│            ↑                │
│            │ localhost      │
│            ↓                │
│  ┌────────────────────────┐ │
│  │   Client / Curl        │ │
│  │   client_example.py    │ │
│  └────────────────────────┘ │
└──────────────────────────────┘
```

### Option 2: Docker (Single Server)

```
┌────────────────────────────────────────────────┐
│          Docker Machine / Server               │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │     Docker Network (ollama_network)      │ │
│  │                                          │ │
│  │  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │   Ollama     │  │ Guard Proxy    │  │ │
│  │  │  :11434      │  │ :8080          │  │ │
│  │  └──────────────┘  └────────────────┘  │ │
│  │         (Container)      (Container)   │ │
│  │                                        │ │
│  └────────────────────┬───────────────────┘ │
│                       │ Port Mapping        │
│  ┌────────────────────▼───────────────────┐ │
│  │     Host Network                       │ │
│  │     Port 8080 ←→ Proxy:8080           │ │
│  └────────────────────┬───────────────────┘ │
│                       │ HTTP/HTTPS          │
└───────────────────────┼────────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
        External Client
```

### Option 3: Production (Multiple Servers)

```
┌──────────────────────────────────────────────────────────────┐
│                   NGINX Load Balancer                         │
│              (Multiple instances for HA)                      │
│                                                              │
│  • Port 80 → HTTPS redirect                                │
│  • Port 443 → HTTPS with SSL/TLS                           │
│  • Load balance → proxy instances                          │
└────┬──────────────────────┬──────────────────────┬──────────┘
     │                      │                      │
     ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│        Guard Proxy Cluster (3-N instances)                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Instance 1  │  Instance 2  │  Instance 3  │ ... N │   │
│  │   :8080      │    :8081     │    :8082     │       │   │
│  │              │              │              │       │   │
│  │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │       │   │
│  │ │IP Filter │ │ │IP Filter │ │ │IP Filter │ │       │   │
│  │ │Input Gd  │ │ │Input Gd  │ │ │Input Gd  │ │       │   │
│  │ │Output Gd │ │ │Output Gd │ │ │Output Gd │ │       │   │
│  │ └──────────┘ │ └──────────┘ │ └──────────┘ │       │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                  │                  │           │
└───────────┼──────────────────┼──────────────────┼───────────┘
            │                  │                  │
            ▼                  ▼                  ▼
┌──────────────────────────────────────────────────────────────┐
│        Ollama Backend Service (Local or Remote)             │
│                                                              │
│  Single instance or cluster behind its own LB              │
└──────────────────────────────────────────────────────────────┘
```

---

## Configuration Flow

```
Configuration Sources (Priority Order)
──────────────────────────────────────

1. HIGHEST PRIORITY: Environment Variables
   ├─ OLLAMA_URL
   ├─ PROXY_PORT
   ├─ ENABLE_IP_FILTER
   ├─ IP_WHITELIST
   ├─ IP_BLACKLIST
   └─ ... more env vars

            ↓ (env vars override)

2. MEDIUM PRIORITY: YAML Config File
   ├─ config.yaml
   ├─ ollama_url: ...
   ├─ proxy_port: ...
   ├─ enable_ip_filter: ...
   └─ ... more settings

            ↓ (config file provides defaults)

3. LOWEST PRIORITY: Hardcoded Defaults
   ├─ ollama_url: http://127.0.0.1:11434
   ├─ proxy_port: 8080
   ├─ enable_ip_filter: false
   └─ ... more defaults


Final Effective Configuration
─────────────────────────────

  Config Manager combines all three:
  • Env vars override everything
  • Config file provides most settings
  • Defaults used if nothing specified
  
  Result: Flexible, secure, production-ready
```

---

## Scaling Architecture

```
PHASE 1: Development
────────────────────
Single Instance
  Client → Proxy (:8080) → Ollama

Resources Needed:
  • 1 server
  • 4GB RAM minimum
  • 2+ CPU cores


PHASE 2: Staging / Testing
──────────────────────────
Multiple Instances with Load Balancer
  Clients → Nginx LB → Proxy1 (:8080)
                    → Proxy2 (:8081)
                    → Proxy3 (:8082)
                                ↓
                              Ollama

Resources Needed:
  • 4-5 servers
  • 2GB RAM per instance
  • 1+ CPU core per instance


PHASE 3: Production High Availability
──────────────────────────────────────
Multiple LBs, Multiple Instances, Cluster Backend
  
  Primary LB → Proxy 1-N
  ↓
  Backup LB → (fails over)
  
  All forward to:
  Ollama Cluster (Master + Slaves)

Resources Needed:
  • 6+ servers
  • 2-4GB RAM per instance
  • 2+ CPU cores
  • 20GB+ storage (for LLM Guard models)


SCALING STRATEGY
────────────────
1. Start: Single instance
2. Monitor: Track CPU, RAM, response times
3. Scale when: >70% CPU or >200ms latency
4. Add: New instances behind LB
5. Optimize: Tune scanner thresholds if needed
6. Monitor: Continuous performance tracking
```

---

## Security Layers

```
Layer 1: Network Security
─────────────────────────
  ↓
  HTTPS/TLS (Nginx)
  ├─ Port 443 encrypted
  ├─ Self-signed or CA certificates
  └─ Security headers (HSTS, X-Frame-Options, etc.)


Layer 2: Access Control
──────────────────────
  ↓
  IP Filtering
  ├─ Whitelist: Only allow specific IPs
  ├─ Blacklist: Block specific IPs
  └─ CIDR ranges: Support /24, /16, etc.


Layer 3: Input Validation
────────────────────────
  ↓
  LLM Guard Input Scanners
  ├─ Prompt Injection detection
  ├─ Toxicity analysis
  ├─ Secret detection (API keys, passwords)
  ├─ Code injection prevention
  ├─ Token limit enforcement
  └─ Custom substring banning


Layer 4: Execution
─────────────────
  ↓
  Safe Request Forwarding
  ├─ No command injection
  ├─ Proper escaping
  └─ Error handling


Layer 5: Output Validation
──────────────────────────
  ↓
  LLM Guard Output Scanners
  ├─ Response toxicity checking
  ├─ Bias detection
  ├─ Malicious URL detection
  ├─ Refusal pattern detection
  └─ Custom substring banning


Layer 6: Monitoring
──────────────────
  ↓
  Comprehensive Logging
  ├─ All requests logged
  ├─ Guard decisions tracked
  ├─ Errors recorded
  └─ Metrics collected
```

---

## Getting Started (Visual Flowchart)

```
                    START HERE
                        │
                        ▼
            ┌──────────────────────┐
            │ What's your goal?    │
            └──────────────────────┘
                │        │        │
         Local  │        │        │  Production
       Development │        │        │
                │        │        │
        ┌───────▼─┐   ┌──▼───┐  ┌──▼────────┐
        │ Docker  │   │Test? │  │Deploy?    │
        │Compose  │   │      │  │           │
        └───┬─────┘   └──┬───┘  └──┬────────┘
            │           │         │
            ▼           ▼         ▼
        ┌────────────────────────────────┐
        │  Read DEPLOYMENT.md            │
        │  Follow Checklist              │
        │  Set up Nginx + SSL            │
        │  Configure IP filtering        │
        │  Enable monitoring             │
        └────────────────────────────────┘
                    │
                    ▼
        ┌────────────────────────────────┐
        │  docker-compose up -d          │
        │  curl localhost:8080/health    │
        │  python client_example.py      │
        └────────────────────────────────┘
                    │
                    ▼
        ┌────────────────────────────────┐
        │  ✅ Running!                   │
        │  Start using the proxy         │
        │  Monitor logs                  │
        │  Adjust as needed              │
        └────────────────────────────────┘
```

---

## Feature Checklist (Visual)

```
INPUT GUARDS
────────────
☑ Prompt Injection Detection   ... ✓ Ready
☑ Toxicity Analysis           ... ✓ Ready
☑ Secret Detection            ... ✓ Ready
☑ Code Injection Prevention   ... ✓ Ready
☑ Token Limit Enforcement     ... ✓ Ready
☑ Custom Substring Banning    ... ✓ Ready

OUTPUT GUARDS
─────────────
☑ Response Toxicity Checking  ... ✓ Ready
☑ Bias Detection              ... ✓ Ready
☑ Malicious URL Detection     ... ✓ Ready
☑ Refusal Pattern Detection   ... ✓ Ready
☑ Custom Substring Banning    ... ✓ Ready

ACCESS CONTROL
──────────────
☑ IP Whitelist Support        ... ✓ Ready
☑ IP Blacklist Support        ... ✓ Ready
☑ CIDR Range Support          ... ✓ Ready
☑ X-Forwarded-For Handling    ... ✓ Ready

API FEATURES
────────────
☑ /v1/generate endpoint       ... ✓ Ready
☑ /v1/chat/completions        ... ✓ Ready
☑ Streaming Support           ... ✓ Ready
☑ Non-Streaming Support       ... ✓ Ready
☑ /health endpoint            ... ✓ Ready
☑ /config endpoint            ... ✓ Ready

OPERATIONAL
───────────
☑ Docker Support              ... ✓ Ready
☑ Nginx Integration           ... ✓ Ready
☑ SSL/TLS Support             ... ✓ Ready
☑ Comprehensive Logging       ... ✓ Ready
☑ Health Checks               ... ✓ Ready
☑ Horizontal Scaling          ... ✓ Ready
☑ Configuration Management    ... ✓ Ready
☑ Error Handling              ... ✓ Ready
```

---

## Documentation Navigation (Visual)

```
YOU ARE HERE
     │
     ▼
    START
     │
     ├─ Quick Start?         → QUICKREF.md
     │
     ├─ Understanding?       → SOLUTION.md
     │
     ├─ Learning to Use?     → USAGE.md
     │
     ├─ Deploying?           → DEPLOYMENT.md
     │
     ├─ Having Problems?     → TROUBLESHOOTING.md
     │
     ├─ Finding Files?       → INDEX.md
     │
     └─ Full Picture?        → README_SOLUTION.md
```

---

**Created**: October 16, 2025  
**Status**: ✅ Production Ready
