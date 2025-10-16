# Ollama Guard Proxy - Solution Overview

## Project Summary

A production-ready, secure proxy service for Ollama that integrates LLM Guard for comprehensive input/output scanning and IP-based access control.

## Components Created

### 1. **Core Application** (`ollama_guard_proxy.py`)

**Features:**
- LLM Guard integration with configurable input/output scanners
- IP whitelist/blacklist access control
- Support for both streaming and non-streaming responses
- OpenAI-compatible chat endpoint support
- Comprehensive logging and error handling
- Health check and configuration endpoints
- Request tracing and metrics

**Key Classes:**
- `Config`: Configuration management (YAML and env vars)
- `IPAccessControl`: IP filtering with CIDR support
- `LLMGuardManager`: LLM Guard initialization and scanning
- Flask/FastAPI endpoints for proxying Ollama requests

### 2. **Configuration Files**

#### `config.example.yaml`
Template configuration file with all available options:
- Ollama backend settings
- Proxy server configuration
- IP access control rules
- LLM Guard scanner settings
- Logging configuration

#### `.env` (example)
Environment variable templates for easy deployment configuration

### 3. **Docker Deployment**

#### `Dockerfile`
- Python 3.11 slim base image
- Optimized for security (minimal attack surface)
- Health checks built-in
- Proper signal handling

#### `docker-compose.yml`
Complete stack including:
- Ollama service with volume persistence
- Guard proxy with environment configuration
- Internal networking
- Health monitoring
- Restart policies

#### `requirements.txt`
All Python dependencies pinned to specific versions

### 4. **Reverse Proxy Configuration**

#### `nginx-guard.conf`
Production-ready Nginx configuration:
- HTTPS/SSL support
- Load balancing across multiple proxy instances
- Security headers (HSTS, X-Content-Type-Options, etc.)
- Buffer optimization for large responses
- Health check endpoint
- Admin-restricted config endpoint
- Error handling

### 5. **Documentation**

#### `USAGE.md`
Comprehensive user guide covering:
- Installation instructions
- Configuration options
- API usage examples (curl, Python)
- IP access control examples
- LLM Guard scanner descriptions
- Response formats
- Troubleshooting
- Docker deployment
- Advanced usage patterns

#### `DEPLOYMENT.md`
Complete deployment guide:
- Local development setup
- Docker deployment (single/compose)
- Production deployment checklist
- Nginx integration with SSL
- Scaling strategies
- Monitoring setup
- Security hardening
- Kubernetes deployment (optional)
- Performance tuning

### 6. **Client Example** (`client_example.py`)

Python client demonstrating:
- Health checks
- Configuration retrieval
- Generation requests (streaming and non-streaming)
- Chat completion requests
- Error handling
- Command-line interface for testing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Applications                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ HTTP/HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Nginx Reverse Proxy                            │
│  • Load Balancing (multiple instances)                          │
│  • SSL/TLS Termination                                          │
│  • Request/Response Buffering                                   │
│  • Security Headers                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   Instance 1        Instance 2        Instance 3
   (Port 8080)       (Port 8081)       (Port 8082)
┌─────────────────────────────────────────────────────────────────┐
│            Ollama Guard Proxy (FastAPI)                         │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. IP Access Control                                       │ │
│  │    • Whitelist/Blacklist checking                         │ │
│  │    • CIDR range support                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ 2. Input Guard (LLM Guard)                                 │ │
│  │    • PromptInjection detection                            │ │
│  │    • Toxicity analysis                                     │ │
│  │    • Secret detection                                      │ │
│  │    • Code injection prevention                             │ │
│  │    • Token limit enforcement                               │ │
│  │    • Custom substring banning                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ 3. Request Forwarding                                      │ │
│  │    • HTTP proxying to Ollama backend                      │ │
│  │    • Streaming support                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ 4. Output Guard (LLM Guard)                                │ │
│  │    • Response toxicity checking                           │ │
│  │    • Bias detection                                        │ │
│  │    • Malicious URL detection                               │ │
│  │    • Refusal pattern detection                             │ │
│  │    • Custom substring banning                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ 5. Response Return                                         │ │
│  │    • Streaming or full response                           │ │
│  │    • Error reporting                                       │ │
│  │    • Logging                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │      Ollama Backend Service         │
        │  • Model inference                  │
        │  • Response generation              │
        └─────────────────────────────────────┘
```

---

## Features Implemented

### 1. **Input Scanning**
- ✅ Prompt Injection Detection
- ✅ Toxicity Analysis
- ✅ Secret/Credential Detection
- ✅ Code Injection Prevention
- ✅ Token Limit Enforcement
- ✅ Custom Substring Banning
- ✅ Gibberish Detection (optional)
- ✅ Language Detection (optional)

### 2. **Output Scanning**
- ✅ Response Toxicity Checking
- ✅ Bias Detection
- ✅ Malicious URL Detection
- ✅ Refusal Pattern Detection
- ✅ Custom Substring Banning
- ✅ Reading Time Analysis (optional)
- ✅ Factual Consistency (optional)
- ✅ Language Consistency (optional)

### 3. **Access Control**
- ✅ IP Whitelist Support
- ✅ IP Blacklist Support
- ✅ CIDR Range Support
- ✅ Dynamic IP Validation
- ✅ X-Forwarded-For Header Support
- ✅ Comprehensive Logging

### 4. **API Endpoints**
- ✅ `/v1/generate` - Ollama API compatible
- ✅ `/v1/chat/completions` - OpenAI compatible
- ✅ `/health` - Health check
- ✅ `/config` - Configuration view

### 5. **Operational Features**
- ✅ Streaming Response Support
- ✅ Non-Streaming Response Support
- ✅ Comprehensive Logging
- ✅ Request Tracing
- ✅ Error Handling
- ✅ Health Checks
- ✅ Configuration Hot-Reload (env vars)
- ✅ Docker Support
- ✅ Nginx Integration
- ✅ Horizontal Scaling

---

## Quick Start

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create config
cp config.example.yaml config.yaml

# 3. Run proxy
python ollama_guard_proxy.py

# 4. Test in another terminal
python client_example.py --prompt "Hello, what is AI?"
```

### Docker Deployment

```bash
# 1. Build and start
docker-compose up -d

# 2. Wait for initialization (60 seconds)
sleep 60

# 3. Test
curl http://localhost:8080/health

# 4. Make requests
python client_example.py --proxy http://localhost:8080 \
  --prompt "Explain machine learning"
```

### Production with Nginx

```bash
# 1. Copy Nginx config
sudo cp nginx-guard.conf /etc/nginx/conf.d/

# 2. Generate SSL certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/ollama.key \
  -out /etc/nginx/ssl/ollama.crt

# 3. Start proxy instances
docker-compose up -d --scale ollama-guard-proxy=3

# 4. Reload Nginx
sudo nginx -t && sudo systemctl reload nginx

# 5. Access via HTTPS
curl https://ollama.ai4team.vn/v1/generate \
  -X POST -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'
```

---

## Configuration Examples

### Example 1: Strict Input Validation

```yaml
enable_input_guard: true
enable_output_guard: true
block_on_guard_error: true  # Block on any error

input_scanners:
  toxicity:
    threshold: 0.3  # Low threshold = strict
  token_limit:
    limit: 2000  # Limit token count
  secrets:
    enabled: true
```

### Example 2: IP-Based Multi-Tenant Access

```yaml
enable_ip_filter: true
ip_whitelist: |
  10.0.0.0/8
  192.168.1.0/24
  172.16.5.100

ip_blacklist: |
  192.168.1.100
  10.0.0.50
```

### Example 3: Production Hardened

```yaml
ollama_url: http://ollama-prod.internal:11434
proxy_host: 0.0.0.0
proxy_port: 8080

enable_ip_filter: true
ip_whitelist: "10.0.0.0/8"

enable_input_guard: true
enable_output_guard: true
block_on_guard_error: false  # Allow errors, log them

input_scanners:
  prompt_injection:
    enabled: true
  toxicity:
    threshold: 0.5
  secrets:
    enabled: true

output_scanners:
  toxicity:
    threshold: 0.5
  malicious_urls:
    enabled: true
```

---

## API Examples

### Generate Request (Non-Streaming)

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "prompt": "What is machine learning?",
    "stream": false,
    "temperature": 0.7
  }'
```

### Generate Request (Streaming)

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Tell me a story",
    "stream": true
  }' | jq -r '.response'
```

### Chat Completion

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant"
      },
      {
        "role": "user",
        "content": "What is the capital of France?"
      }
    ],
    "stream": false
  }'
```

---

## Security Considerations

1. **Enable IP Filtering** in production
2. **Use HTTPS** for all client connections
3. **Configure Scanners** appropriately for your use case
4. **Monitor Logs** for suspicious activity
5. **Keep LLM Guard Updated** for latest security patches
6. **Rate Limit** if needed (add to proxy)
7. **Authenticate** sensitive endpoints (add to proxy)
8. **Run with Least Privileges** (Docker security opts)

---

## Performance Characteristics

| Operation | Typical Latency | Notes |
|-----------|-----------------|-------|
| IP Filtering | <1ms | Very fast |
| Input Guard (avg) | 100-500ms | Depends on prompt length |
| Ollama Processing | Variable | Model-dependent |
| Output Guard (avg) | 50-200ms | Depends on response length |
| **Total Overhead** | **150-700ms** | Per request |

---

## Files Summary

| File | Purpose | Size |
|------|---------|------|
| `ollama_guard_proxy.py` | Main application | ~700 lines |
| `config.example.yaml` | Configuration template | ~60 lines |
| `Dockerfile` | Container image def | ~30 lines |
| `docker-compose.yml` | Service orchestration | ~50 lines |
| `nginx-guard.conf` | Reverse proxy config | ~150 lines |
| `client_example.py` | Python client demo | ~300 lines |
| `USAGE.md` | User guide | ~600 lines |
| `DEPLOYMENT.md` | Deployment guide | ~800 lines |
| `requirements.txt` | Python dependencies | ~10 lines |
| **Total** | - | **~2,800 lines** |

---

## Next Steps

1. **Review Configuration**: Customize `config.yaml` for your environment
2. **Test Locally**: Run with local Ollama instance
3. **Deploy Docker**: Use docker-compose for containerized deployment
4. **Integrate Nginx**: Set up reverse proxy with SSL
5. **Scale**: Run multiple instances behind load balancer
6. **Monitor**: Enable logging and health checks
7. **Harden**: Apply security configurations from deployment guide

---

## Support Resources

- **LLM Guard Docs**: https://protectai.github.io/llm-guard/
- **Ollama Docs**: https://github.com/ollama/ollama
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Docker Docs**: https://docs.docker.com/

---

Created: October 16, 2025
Version: 1.0
Status: Production Ready
