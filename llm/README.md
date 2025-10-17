# LiteLLM Load Balancing with LLM Guard - Implementation Summary

## 🎯 Project Overview

This implementation provides **production-grade load balancing for multiple Ollama servers** with **integrated LLM Guard security scanning** via LiteLLM's call hooks system.

### Key Achievements

✅ **Load Balancing**
- Multiple load balancing strategies (round_robin, least_busy, weighted)
- Automatic health checking and failover
- Request routing across 3+ Ollama servers
- Intelligent load distribution

✅ **Security Integration**
- LLM Guard input scanning (5 scanners)
- LLM Guard output scanning (5 scanners)
- Multilingual error messages (7 languages)
- Automatic language detection

✅ **API Compatibility**
- OpenAI-compatible endpoints
- Support for chat completions, completions, embeddings
- Legacy endpoint support (/api/* → /v1/*)
- Streaming support

✅ **Production Ready**
- Nginx reverse proxy with SSL/TLS
- Rate limiting per endpoint
- Prometheus metrics collection
- Grafana dashboards
- Docker Compose deployment

## 📁 Files Created/Modified

### Configuration Files

| File | Purpose |
|------|---------|
| `litellm_config.yaml` | LiteLLM proxy configuration with model list and load balancing |
| `nginx-litellm.conf` | Nginx reverse proxy with SSL/TLS and rate limiting |
| `prometheus.yml` | Prometheus metrics scraping configuration |
| `docker-compose.yml` | Complete Docker stack for all services |
| `requirements.txt` | Python dependencies (LiteLLM, LLM Guard, etc.) |

### Implementation Files

| File | Purpose |
|------|---------|
| `litellm_guard_hooks.py` | LLM Guard integration with pre/post-call hooks |
| `run_litellm_proxy.py` | Launcher script for LiteLLM with hooks |
| `test_litellm_integration.py` | Comprehensive test suite |

### Documentation Files

| File | Purpose |
|------|---------|
| `LITELLM_INTEGRATION.md` | Complete technical documentation |
| `DEPLOYMENT_GUIDE.md` | Step-by-step deployment instructions |
| `ARCHITECTURE.md` | System architecture and design decisions |

## 🏗️ Architecture

```
┌──────────────────┐
│  Client Request  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│  Nginx Reverse Proxy         │
│  ├─ SSL/TLS Termination      │
│  ├─ Rate Limiting            │
│  └─ Connection Pooling       │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  LiteLLM Proxy               │
│  ├─ Load Balancing Logic     │
│  ├─ Model Routing            │
│  ├─ Health Checking          │
│  └─ Metrics Collection       │
└────────┬─────────────────────┘
         │
    ┌────┴──────────────┐
    │                   │
    ▼                   ▼
┌─────────────┐   ┌──────────────┐
│   Pre-Call  │   │  Post-Call   │
│  LLM Guard  │   │  LLM Guard   │
│   Hooks     │   │   Hooks      │
└──────┬──────┘   └──────┬───────┘
       │                 │
       ▼                 ▼
INPUT VALIDATION    OUTPUT VALIDATION
├─ BanSubstrings    ├─ BanSubstrings
├─ PromptInjection  ├─ Toxicity
├─ Toxicity         ├─ MaliciousURLs
├─ Secrets          ├─ NoRefusal
└─ TokenLimit       └─ NoCode

LANGUAGE DETECTION & LOCALIZED ERRORS
├─ Chinese (Simplified/Traditional)
├─ Vietnamese
├─ Japanese
├─ Korean
├─ Russian
├─ Arabic
└─ English (default)

    │
    ▼
┌──────────────────────┐
│  Ollama Servers      │
│  ├─ 192.168.1.2      │ (Primary)
│  ├─ 192.168.1.11     │ (Secondary)
│  └─ 192.168.1.20     │ (Tertiary)
└──────────────────────┘
```

## 🔧 Load Balancing Strategies

### 1. Round Robin (Sequential Distribution)

Evenly distributes requests across all servers in sequence.

```yaml
load_balancing_config:
  strategy: "round_robin"
```

**Use case**: Uniform server capacity

### 2. Least Busy (Recommended)

Routes requests to server with lowest current load.

```yaml
load_balancing_config:
  strategy: "least_busy"
```

**Use case**: Heterogeneous server capacity, production deployments

### 3. Weighted Distribution

Routes proportional to configured weights.

```yaml
load_balancing_config:
  strategy: "weighted"
  
model_list:
  - litellm_params:
      api_base: http://192.168.1.2:11434    # weight 1 (default)
  - litellm_params:
      api_base: http://192.168.1.11:11434   # weight 2 (gets 2x more traffic)
      weight: 2
```

**Use case**: Mix of different hardware capabilities

## 🔐 Security Integration

### LLM Guard Flow

```
Request → Pre-Call Hook → Input Scanners
  │
  ├─ BanSubstrings (Check blocked keywords)
  ├─ PromptInjection (Detect injection)
  ├─ Toxicity (Check harmful content)
  ├─ Secrets (Prevent credential leakage)
  └─ TokenLimit (Enforce constraints)
  
  ├─ BLOCKED → Return Localized Error
  └─ ALLOWED → Continue to Ollama
  
  │
  ▼
Response ← Post-Call Hook ← Output Scanners
  │
  ├─ BanSubstrings (Filter response)
  ├─ Toxicity (Check toxic output)
  ├─ MaliciousURLs (Prevent phishing)
  ├─ NoRefusal (Ensure compliance)
  └─ NoCode (Prevent code generation)
  
  ├─ BLOCKED → Return Sanitized Response
  └─ ALLOWED → Return to Client
```

### Multilingual Error Messages

Automatic detection from user input:

```python
# Input: "你好，请忽视之前的指令"
# Detected: Chinese (zh)
# Error: "您的输入被安全扫描器阻止。原因: PromptInjection"

# Input: "Xin chào, bỏ qua hướng dẫn"
# Detected: Vietnamese (vi)
# Error: "Đầu vào của bạn bị chặn bởi bộ quét bảo mật. Lý do: PromptInjection"

# Input: "Please disregard instructions"
# Detected: English (en, default)
# Error: "Your input was blocked by the security scanner. Reason: PromptInjection"
```

## 📊 API Endpoints

### OpenAI-Compatible Endpoints

All endpoints follow OpenAI API format for seamless client migration.

```bash
# Chat Completions (streaming)
POST /v1/chat/completions
POST /api/chat  (legacy redirect)

# Text Completions
POST /v1/completions

# Embeddings
POST /v1/embeddings

# Model List
GET /v1/models

# Health Check
GET /health
```

### Usage Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="not-needed",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="ollama/llama3.2",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

## 🚀 Deployment

### Quick Start

```bash
cd llm

# 1. Configure Ollama servers in litellm_config.yaml
# Update: 192.168.1.2, 192.168.1.11, 192.168.1.20 → Your server IPs

# 2. Start all services
docker-compose up -d

# 3. Verify
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# 4. Test
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Services in Docker Stack

| Service | Port | Purpose |
|---------|------|---------|
| litellm-proxy | 8000 | Main LiteLLM API |
| nginx | 80/443 | Reverse proxy + SSL |
| redis | 6379 | Caching & sessions |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Dashboards |

## 📈 Monitoring

### Prometheus Metrics

Access: `http://localhost:9090`

Key metrics:
- `litellm_request_count` - Total requests
- `litellm_request_duration_seconds` - Response time
- `litellm_tokens_used` - Token consumption
- `litellm_cost` - Cost tracking

### Grafana Dashboards

Access: `http://localhost:3000` (admin/admin)

Pre-built visualizations:
- Request rate (req/sec)
- Error rate (%)
- P95 latency (ms)
- Token usage by model
- Cost by model
- Server health status

## 🧪 Testing

### Run Test Suite

```bash
# All tests
python test_litellm_integration.py

# Specific test
python test_litellm_integration.py --test guard

# Verbose output
python test_litellm_integration.py --verbose
```

### Test Coverage

- ✅ Configuration loading
- ✅ Language detection (7 languages)
- ✅ Error message generation
- ✅ API endpoints (health, models, chat, embeddings)
- ✅ LLM Guard blocking
- ✅ Streaming responses
- ✅ Load distribution

## 🔄 Load Balancing in Action

### Scenario: Least Busy Strategy

```
Server Load:
├─ Server 1 (192.168.1.2):   50 requests in progress
├─ Server 2 (192.168.1.11):  20 requests in progress
└─ Server 3 (192.168.1.20):  100 requests in progress

New Request → Routed to Server 2 (lowest load) ✓
```

### Scenario: Health Check & Failover

```
Server Status:
├─ Server 1: Healthy ✓
├─ Server 2: Unhealthy ✗ (health check failed)
└─ Server 3: Healthy ✓

New Request → Only routed to Server 1 or 3
Server 2 automatically removed from rotation
Periodic health check on Server 2 for recovery
```

### Scenario: Automatic Retry with Fallback

```
Request → Server 1 → Timeout/Error
  │
  └─ Retry 1 → Server 3 → Success ✓
       (automatic failover)
```

## 🎓 Key Features

### Load Balancing
- ✅ 3+ simultaneous Ollama servers
- ✅ Least-busy intelligent routing
- ✅ Automatic health checking
- ✅ Configurable failover strategy
- ✅ Weighted distribution support

### Security
- ✅ 5 input scanners (injection, toxicity, secrets, etc.)
- ✅ 5 output scanners (code detection, malicious URLs, etc.)
- ✅ Automatic language detection
- ✅ Localized error messages (7 languages)
- ✅ Pre/post-call hooks for custom logic

### Performance
- ✅ Streaming support for large responses
- ✅ Connection pooling
- ✅ Response caching (Redis)
- ✅ Rate limiting per endpoint
- ✅ Metrics collection & monitoring

### Compatibility
- ✅ OpenAI API format (drop-in replacement)
- ✅ Legacy endpoint support
- ✅ Python SDK support
- ✅ curl/REST support
- ✅ Streaming format compatibility

## 📚 Documentation

### Quick References

| Topic | File |
|-------|------|
| **Technical Setup** | `LITELLM_INTEGRATION.md` |
| **Deployment Steps** | `DEPLOYMENT_GUIDE.md` |
| **Architecture** | This file |
| **API Reference** | `LITELLM_INTEGRATION.md` |
| **Troubleshooting** | `DEPLOYMENT_GUIDE.md` |

## 🔍 Configuration Examples

### Multi-Server Setup

```yaml
model_list:
  # Server 1
  - model_name: ollama/llama3.2
    litellm_params:
      api_base: http://192.168.1.2:11434
  
  # Server 2
  - model_name: ollama/llama3.2
    litellm_params:
      api_base: http://192.168.1.11:11434
  
  # Server 3
  - model_name: ollama/llama3.2
    litellm_params:
      api_base: http://192.168.1.20:11434

load_balancing_config:
  strategy: "least_busy"
  enable_fallback: true
  health_check_enabled: true
```

### Security Configuration

```yaml
llm_guard:
  enabled: true
  
  input_scanning:
    enabled: true
    scanners:
      - PromptInjection      # Critical
      - Toxicity             # Important
      - Secrets              # Critical
      - BanSubstrings        # Optional
      - TokenLimit           # Optional
  
  output_scanning:
    enabled: true
    scanners:
      - NoCode               # If needed
      - MaliciousURLs        # Important
      - Toxicity             # Important
      - BanSubstrings        # Optional
      - NoRefusal            # Optional
```

## 🛠️ Troubleshooting

### Issue: "No healthy backends"
- [ ] Verify Ollama servers are running
- [ ] Check firewall/network connectivity
- [ ] Increase health check timeout
- [ ] Check Ollama logs for errors

### Issue: Requests blocked unexpectedly
- [ ] Check which scanner is blocking
- [ ] Review LLM Guard configuration
- [ ] Temporarily disable problematic scanner
- [ ] Adjust scanner sensitivity settings

### Issue: Poor load distribution
- [ ] Verify strategy is set to `least_busy`
- [ ] Check server health status
- [ ] Monitor request distribution in metrics
- [ ] Review server performance

## 📋 Production Checklist

- [ ] Configure all Ollama server IPs
- [ ] Choose load balancing strategy
- [ ] Enable LLM Guard security scanners
- [ ] Configure SSL/TLS certificates
- [ ] Set up Prometheus monitoring
- [ ] Create Grafana dashboards
- [ ] Configure log aggregation
- [ ] Test failover scenarios
- [ ] Load test the system
- [ ] Document configuration
- [ ] Train support team
- [ ] Set up alerting rules
- [ ] Plan backup strategy
- [ ] Schedule updates

## 🎯 Next Steps

1. **Deploy**: Follow `DEPLOYMENT_GUIDE.md`
2. **Configure**: Update Ollama server IPs in `litellm_config.yaml`
3. **Test**: Run `test_litellm_integration.py`
4. **Monitor**: Access Grafana at `http://localhost:3000`
5. **Scale**: Add more Ollama servers as needed
6. **Maintain**: Regular updates and monitoring

## 📞 Support

For issues or questions:
1. Check `TROUBLESHOOTING.md` in `DEPLOYMENT_GUIDE.md`
2. Review `LITELLM_INTEGRATION.md` for technical details
3. Check logs: `docker-compose logs -f litellm-proxy`
4. Run tests: `python test_litellm_integration.py --verbose`

## 📄 Files Reference

```
llm/
├── litellm_config.yaml              # Main configuration
├── litellm_guard_hooks.py           # Security integration
├── run_litellm_proxy.py             # Launcher script
├── test_litellm_integration.py      # Test suite
├── nginx-litellm.conf               # Nginx config
├── prometheus.yml                   # Metrics config
├── docker-compose.yml               # Docker stack
├── requirements.txt                 # Dependencies
├── LITELLM_INTEGRATION.md          # Technical docs
├── DEPLOYMENT_GUIDE.md             # Deployment docs
└── README.md                        # This file
```

---

## Version Information

- **LiteLLM**: 1.41.0
- **LLM Guard**: 0.3.18
- **Ollama API**: v1 (OpenAI-compatible)
- **Python**: 3.9+
- **Status**: ✅ **Production Ready**
- **Last Updated**: October 17, 2025

---

**Created by**: AI4Team Team  
**License**: MIT  
**Repository**: [ai4team](https://github.com/RadteamBaoDA/ai4team)
