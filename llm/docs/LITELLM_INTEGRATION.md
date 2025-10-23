# LiteLLM Load Balancing with LLM Guard Integration

## Overview

This setup implements a production-ready LiteLLM proxy that provides:

- **Intelligent Load Balancing**: Distributes requests across multiple Ollama servers using least-busy strategy
- **LLM Guard Security**: Input/output scanning with multilingual error messages
- **High Availability**: Automatic failover and health checking
- **Performance Monitoring**: Prometheus metrics and Grafana dashboards
- **Rate Limiting**: Nginx-based rate limiting per endpoint
- **SSL/TLS Security**: Production-grade encryption
- **OpenAI Compatible API**: Seamless integration with existing clients

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Requests                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │    Nginx Reverse Proxy         │
        │ (SSL/TLS, Rate Limiting)       │
        └────────────────┬───────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │     LiteLLM Proxy              │
        │  (Load Balancing, Routing)     │
        └────────────────┬───────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │ Ollama │      │ Ollama │      │ Ollama │
    │ Server │      │ Server │      │ Server │
    │   #1   │      │   #2   │      │   #3   │
    └────────┘      └────────┘      └────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 LLM Guard Integration                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Pre-Call Hook: Input Scanning                          │   │
│  │  - BanSubstrings, PromptInjection, Toxicity             │   │
│  │  - Secrets Detection, Token Limiting                    │   │
│  │  - Multilingual language detection                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Post-Call Hook: Output Scanning                        │   │
│  │  - BanSubstrings, Toxicity Detection                    │   │
│  │  - Malicious URL Detection, Refusal Detection           │   │
│  │  - Code Generation Prevention                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  Monitoring & Analytics                          │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │    Prometheus    │  │      Grafana     │                     │
│  │    Metrics       │  │   Dashboards     │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. LiteLLM Configuration (`litellm_config.yaml`)

Defines model endpoints and load balancing strategy:

```yaml
model_list:
  - model_name: ollama/llama3.2
    litellm_params:
      model: ollama/llama3.2
      api_base: http://192.168.1.2:11434
      timeout: 300
      max_retries: 2

load_balancing_config:
  strategy: "least_busy"  # Intelligent load balancing
  enable_fallback: true
  health_check_enabled: true
```

**Load Balancing Strategies**:
- `round_robin`: Equal distribution across servers
- `least_busy`: Route to server with lowest load (default)
- `weighted`: Manual weight assignment per server

### 2. LLM Guard Hooks (`litellm_guard_hooks.py`)

Implements pre/post-call hooks for security scanning:

```python
# Pre-call hook: Input validation
async def pre_call_hook(**kwargs):
    # Extract prompt
    # Detect language
    # Scan input with LLM Guard
    # Return error if blocked

# Post-call hook: Output validation
async def post_call_hook(response, **kwargs):
    # Extract response text
    # Scan output with LLM Guard
    # Return sanitized response if blocked
```

**Integration Points**:
- `pre_call_hook`: Validates input before sending to Ollama
- `post_call_hook`: Validates output before returning to client
- `on_failure_hook`: Logs failed requests
- `on_success_hook`: Logs successful requests

### 3. Nginx Configuration (`nginx-litellm.conf`)

Provides reverse proxy, SSL/TLS, and rate limiting:

- **SSL/TLS**: TLSv1.2+ with modern ciphers
- **Rate Limiting**: 10 req/s API, 5 req/s chat, 30 req/s health
- **Streaming Support**: Disabled buffering for streaming endpoints
- **Security Headers**: HSTS, X-Frame-Options, CSP
- **Connection Limits**: 10 concurrent per IP

### 4. Docker Compose Stack

```yaml
services:
  litellm-proxy:      # Main LiteLLM service
  redis:              # Cache and session store
  prometheus:         # Metrics collection
  grafana:            # Visualization dashboards
  nginx:              # Reverse proxy
```

## Setup & Deployment

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Ollama servers (1+) accessible from proxy
- 2GB+ RAM (4GB+ recommended)

### Quick Start

```bash
# 1. Navigate to llm directory
cd d:\Project\ai4team\llm

# 2. Install dependencies (optional, for local testing)
pip install -r requirements.txt

# 3. Start the stack
docker-compose up -d

# 4. Check services
docker-compose ps

# 5. View logs
docker-compose logs -f litellm-proxy
```

### Verify Setup

```bash
# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Test chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

## Configuration

### Model List Management

Add new Ollama servers to `litellm_config.yaml`:

```yaml
model_list:
  - model_name: ollama/custom-model
    litellm_params:
      model: ollama/custom-model
      api_base: http://192.168.1.X:11434
      timeout: 300
      max_retries: 2
```

### LLM Guard Scanners

Enable/disable scanners in `litellm_config.yaml`:

```yaml
llm_guard:
  input_scanning:
    enabled: true
    scanners:
      - BanSubstrings
      - PromptInjection
      - Toxicity
      - Secrets
      - TokenLimit
  
  output_scanning:
    enabled: true
    scanners:
      - BanSubstrings
      - Toxicity
      - MaliciousURLs
      - NoRefusal
      - NoCode
```

### Rate Limiting

Adjust in `nginx-litellm.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=5r/s;

location /v1/chat/completions {
    limit_req zone=chat_limit burst=20 nodelay;
    # ...
}
```

## API Reference

### OpenAI-Compatible Endpoints

All endpoints are compatible with OpenAI API clients (with model names like `ollama/llama3.2`):

#### Chat Completions (Streaming)

```bash
curl -X POST https://llm.ai4team.vn/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Tell me a joke"}
    ],
    "stream": true,
    "temperature": 0.7,
    "top_p": 1.0
  }'
```

**Response** (streaming):
```json
{
  "id": "chatcmpl-xxx",
  "object": "text_completion.chunk",
  "created": 1697000000,
  "model": "ollama/llama3.2",
  "choices": [{
    "delta": {"content": "Why did the..."},
    "index": 0,
    "finish_reason": null
  }]
}
```

#### Text Completions

```bash
curl -X POST https://llm.ai4team.vn/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "prompt": "Tell me a joke",
    "max_tokens": 100
  }'
```

#### Embeddings

```bash
curl -X POST https://llm.ai4team.vn/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "input": "Hello world"
  }'
```

#### List Models

```bash
curl https://llm.ai4team.vn/v1/models
```

### Response with Security Blocking

When LLM Guard blocks a request:

```json
{
  "error": {
    "message": "[zh] 您的输入被安全扫描器阻止。原因: PromptInjection",
    "type": "prompt_blocked",
    "param": null,
    "code": null
  }
}
```

## LLM Guard Integration

### How It Works

1. **Request arrives** at LiteLLM proxy
2. **Pre-call hook** executes:
   - Extracts user prompt/message
   - Detects language automatically
   - Scans with LLM Guard input scanners
   - Blocks if dangerous (returns localized error)
   - Otherwise continues
3. **Request sent** to Ollama backend
4. **Post-call hook** executes:
   - Extracts model response
   - Scans with LLM Guard output scanners
   - Blocks if dangerous output detected
   - Otherwise returns response to client

### Language Detection

Automatic detection for 7 languages:
- 🇨🇳 Chinese (Simplified & Traditional)
- 🇻🇳 Vietnamese
- 🇯🇵 Japanese
- 🇰🇷 Korean
- 🇷🇺 Russian
- 🇸🇦 Arabic
- 🇺🇸 English (default)

Error messages are returned in the user's detected language.

### Input Scanners

| Scanner | Purpose | Detects |
|---------|---------|---------|
| BanSubstrings | Block keywords | Specific banned phrases |
| PromptInjection | Prevent injection | Injection attempts |
| Toxicity | Detect harmful content | Toxic language |
| Secrets | Prevent leakage | API keys, credentials |
| TokenLimit | Enforce constraints | Excessive token use |

### Output Scanners

| Scanner | Purpose | Detects |
|---------|---------|---------|
| BanSubstrings | Filter responses | Banned content in output |
| Toxicity | Detect harmful output | Toxic model responses |
| MaliciousURLs | Prevent phishing | Suspicious links |
| NoRefusal | Ensure compliance | Refusal attempts |
| NoCode | Prevent code generation | Generated code (optional) |

## Monitoring

### Access Prometheus

```bash
# Port 9090
http://localhost:9090

# Useful queries:
# Request rate: rate(http_requests_total[1m])
# Error rate: rate(http_requests_total{status=~"5.."}[1m])
# Latency: histogram_quantile(0.95, http_request_duration_seconds)
```

### Access Grafana

```bash
# Port 3000, default credentials admin/admin
http://localhost:3000

# Import pre-built dashboards for LiteLLM monitoring
```

### Metrics

LiteLLM exposes Prometheus metrics:

```
litellm_request_count{model="ollama/llama3.2",status="success"}
litellm_request_duration_seconds{model="ollama/llama3.2"}
litellm_tokens_used{model="ollama/llama3.2",type="input"}
litellm_cost{model="ollama/llama3.2"}
```

## Troubleshooting

### LiteLLM won't start

```bash
# Check configuration
docker-compose logs litellm-proxy

# Verify config file exists
ls -la litellm_config.yaml

# Test with debug logging
export LITELLM_LOGGING=DEBUG
docker-compose up -d litellm-proxy
```

### Requests failing with "blocked"

```bash
# Check LLM Guard is working
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"model":"ollama/llama3.2","messages":[{"role":"user","content":"test"}]}'

# Check guard hooks logs
docker-compose logs litellm-proxy | grep -i "guard\|scan"
```

### Load balancing not working

```bash
# Verify Ollama servers are accessible
curl http://192.168.1.2:11434/api/tags
curl http://192.168.1.11:11434/api/tags
curl http://192.168.1.20:11434/api/tags

# Check LiteLLM routing
curl http://localhost:8000/v1/models
```

### Rate limiting too restrictive

Edit `nginx-litellm.conf` rate limiting zones:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;  # Increase from 10 to 20
```

Then reload Nginx:

```bash
docker-compose exec nginx nginx -s reload
```

## Performance Tuning

### Increase Concurrency

In `litellm_config.yaml`:

```yaml
proxy_server:
  num_workers: 8  # Increase from 4
  
load_balancing_config:
  max_concurrent_requests: 2000  # Increase from 1000
```

### Enable Caching

Use Redis for response caching:

```yaml
cache:
  type: redis
  ttl: 3600  # Cache responses for 1 hour
```

### Optimize Timeouts

Adjust in `litellm_config.yaml`:

```yaml
model_list:
  - model_name: ollama/llama3.2
    litellm_params:
      timeout: 600  # Increase for larger models
      max_retries: 3
```

## Security Best Practices

1. **Enable HTTPS**: Use valid SSL certificates
2. **Configure Firewalls**: Restrict access to admin endpoints
3. **Use API Keys**: Enable authentication in LiteLLM
4. **Monitor Logs**: Set up log aggregation
5. **Regular Updates**: Keep dependencies updated
6. **Rate Limiting**: Adjust based on your SLA
7. **LLM Guard**: Enable all recommended scanners

## Production Deployment

### Using Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: litellm-proxy
spec:
  containers:
  - name: litellm
    image: ghcr.io/berriai/litellm:main
    ports:
    - containerPort: 8000
    volumeMounts:
    - name: config
      mountPath: /app/litellm_config.yaml
    env:
    - name: CONFIG_PATH
      value: /app/litellm_config.yaml
  volumes:
  - name: config
    configMap:
      name: litellm-config
```

### Using Docker Swarm

```bash
docker stack deploy -c docker-compose.yml litellm
```

## Advanced Features

### Custom Hooks

Extend `litellm_guard_hooks.py` with custom logic:

```python
async def custom_pre_hook(**kwargs):
    # Custom validation
    # Rate limiting by user
    # Cost tracking
    pass
```

### Cost Tracking

Enable in `litellm_config.yaml`:

```yaml
cost_tracking:
  enabled: true
  cost_per_1k_input_tokens: 0.001
  cost_per_1k_output_tokens: 0.002
```

### Fallback Models

Configure automatic fallback:

```yaml
fallback_models:
  ollama/llama3.2:
    - model_name: ollama/mistral
      provider: ollama
```

## Documentation

- **LiteLLM Docs**: https://docs.litellm.ai/
- **LiteLLM Load Balancing**: https://docs.litellm.ai/docs/proxy/load_balancing
- **LiteLLM Call Hooks**: https://docs.litellm.ai/docs/proxy/call_hooks
- **LLM Guard**: https://protectai.github.io/llm-guard/
- **Ollama API**: https://github.com/ollama/ollama/blob/main/docs/api.md

## Support & Troubleshooting

For issues:
1. Check logs: `docker-compose logs -f litellm-proxy`
2. Verify configuration: `cat litellm_config.yaml`
3. Test endpoints manually with curl
4. Check Ollama server health
5. Review security scanner settings

## License

This integration is provided as part of AI4Team project. All components maintain their respective licenses.

---

**Last Updated**: October 17, 2025
**Status**: Production Ready ✅
