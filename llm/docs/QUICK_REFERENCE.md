# LiteLLM Load Balancing Quick Reference

## 🚀 Quick Start (3 Steps)

### Step 1: Configure Servers
```bash
# Edit llm/litellm_config.yaml
# Update these lines:
api_base: http://192.168.1.2:11434     # ← Your Server 1 IP
api_base: http://192.168.1.11:11434    # ← Your Server 2 IP  
api_base: http://192.168.1.20:11434    # ← Your Server 3 IP
```

### Step 2: Deploy
```bash
cd llm
docker-compose up -d
```

### Step 3: Test
```bash
curl http://localhost:8000/v1/models
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ollama/llama3.2","messages":[{"role":"user","content":"Hello"}]}'
```

## 📊 Load Balancing Strategies

### Least Busy (Recommended ⭐)
```yaml
load_balancing_config:
  strategy: "least_busy"
```
✅ Automatically routes to server with lowest load  
✅ Best for production deployments  
✅ Handles heterogeneous server capacity  

### Round Robin
```yaml
load_balancing_config:
  strategy: "round_robin"
```
✅ Sequential distribution  
✅ Simple and predictable  
✅ Best for identical servers  

### Weighted
```yaml
load_balancing_config:
  strategy: "weighted"
  model_list:
    - litellm_params:
        api_base: http://server1:11434
        weight: 1
    - litellm_params:
        api_base: http://server2:11434
        weight: 2  # Gets 2x more traffic
```
✅ Proportional distribution  
✅ For mixed hardware capabilities  

## 🔐 Security Controls

### Enable/Disable Scanners
```yaml
llm_guard:
  enabled: true
  
  input_scanning:
    scanners:
      - PromptInjection      # CRITICAL
      - Toxicity             # IMPORTANT
      - Secrets              # CRITICAL
      - BanSubstrings        # OPTIONAL
      - TokenLimit           # OPTIONAL
  
  output_scanning:
    scanners:
      - NoCode               # For code-restricted policies
      - MaliciousURLs        # IMPORTANT
      - Toxicity             # IMPORTANT
      - BanSubstrings        # OPTIONAL
      - NoRefusal            # OPTIONAL
```

### What Gets Blocked

| Scanner | Blocks | Example |
|---------|--------|---------|
| **PromptInjection** | Prompt attacks | "Ignore previous instructions and..." |
| **Secrets** | Credentials | API keys, passwords |
| **Toxicity** | Harmful content | Profanity, violence |
| **BanSubstrings** | Keywords | Custom blocked phrases |
| **TokenLimit** | Excessive tokens | Requests >8000 tokens |
| **NoCode** | Generated code | Python scripts, bash commands |
| **MaliciousURLs** | Phishing links | Suspicious domains |

## 🌍 Language Support

Auto-detected from user input:

```
Chinese:    你好                    → Error in Chinese
Vietnamese: Xin chào              → Error in Vietnamese
Japanese:   こんにちは              → Error in Japanese
Korean:     안녕하세요              → Error in Korean
Russian:    Привет                → Error in Russian
Arabic:     مرحبا                 → Error in Arabic
English:    Hello                 → Error in English (default)
```

## 📡 API Endpoints

```bash
# Chat (streaming)
POST /v1/chat/completions
POST /api/chat  (redirect)

# Completions
POST /v1/completions

# Embeddings
POST /v1/embeddings

# Model list
GET /v1/models

# Health check
GET /health

# Proxy config
GET /config
```

## 🔄 Request Flow

```
1. Client sends request
   ↓
2. Nginx receives (rate limit check, SSL/TLS)
   ↓
3. LiteLLM routes to server (load balancing)
   ↓
4. Pre-call hook: Input scanning
   ├─ If blocked → Return error (localized)
   └─ If OK → Continue
   ↓
5. Ollama processes request
   ↓
6. Post-call hook: Output scanning
   ├─ If blocked → Return sanitized error
   └─ If OK → Continue
   ↓
7. Response sent to client
```

## 🐛 Troubleshooting Matrix

| Problem | Cause | Solution |
|---------|-------|----------|
| **"No healthy backends"** | Ollama down | Check Ollama servers: `curl http://ip:11434/api/tags` |
| **Port 8000 in use** | Another service | `docker-compose down` then retry |
| **High latency** | Slow server | Check `docker-compose logs litellm-proxy` |
| **Rate limited** | Too many requests | Increase `limit_req_zone` rate in nginx config |
| **Requests blocked** | Guard too strict | Disable scanner or adjust sensitivity |
| **Can't reach UI** | Firewall | Check firewall allows ports 80, 443, 3000, 9090 |

## 📊 Monitoring Dashboard

Access **Grafana** at: `http://localhost:3000` (admin/admin)

Key metrics to watch:
- **Request rate**: Should scale with requests
- **Error rate**: Should be <1% in normal operation
- **P95 latency**: Should be <2 seconds for most requests
- **Token usage**: Track by model
- **Server health**: All servers should show as "up"

## 💾 Configuration Files Location

```
llm/
├── litellm_config.yaml      ← Main config (UPDATE WITH YOUR IPs)
├── nginx-litellm.conf       ← Reverse proxy rules
├── docker-compose.yml       ← Container orchestration
├── prometheus.yml           ← Metrics collection
└── requirements.txt         ← Python dependencies
```

## 🔧 Common Configuration Changes

### Increase Rate Limit
```yaml
# In nginx-litellm.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;  # Changed from 10
```

### Add More Ollama Servers
```yaml
# In litellm_config.yaml - duplicate a model_list entry:
- model_name: ollama/llama3.2
  litellm_params:
    api_base: http://192.168.1.30:11434  # NEW SERVER
```

### Disable Security Scanning
```yaml
# In litellm_config.yaml
llm_guard:
  enabled: false  # Changed from true
```

### Change Load Strategy
```yaml
# In litellm_config.yaml
load_balancing_config:
  strategy: "round_robin"  # Changed from least_busy
```

## 🚀 Deployment Commands

```bash
# Navigate to llm directory
cd llm

# Start services
docker-compose up -d

# View logs
docker-compose logs -f litellm-proxy

# Check status
docker-compose ps

# Stop services
docker-compose down

# Restart specific service
docker-compose restart litellm-proxy

# View container logs
docker logs -f litellm-proxy

# Execute command in container
docker-compose exec litellm-proxy bash

# Scale to multiple instances
docker-compose up -d --scale litellm-proxy=3
```

## 🧪 Quick Tests

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Simple chat
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "Hi"}]
  }'

# Test with Chinese (to verify multilingual)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=litellm_request_count
```

## 📚 Documentation Map

```
START HERE → README.md (overview & architecture)
     ↓
Choose your path:
├─→ DEPLOYMENT_GUIDE.md (if deploying)
├─→ LITELLM_INTEGRATION.md (if technical details)
├─→ IMPLEMENTATION_COMPLETE.md (full reference)
└─→ Quick Reference (this document)
```

## 🎯 Success Criteria

After deployment, verify:
- [ ] `curl http://localhost/health` returns 200
- [ ] `curl http://localhost/v1/models` shows models
- [ ] Chat completion returns response without errors
- [ ] Prometheus shows metrics at `http://localhost:9090`
- [ ] Grafana accessible at `http://localhost:3000`
- [ ] All 3 Ollama servers show as healthy
- [ ] Test suite passes: `python test_litellm_integration.py`

## 🔐 Security Checklist

- [ ] Enable HTTPS in production (set SSL certificates)
- [ ] Configure firewall (allow only necessary ports)
- [ ] Enable LLM Guard scanners (at least critical ones)
- [ ] Set up rate limiting (prevent abuse)
- [ ] Monitor error logs (detect attacks)
- [ ] Regular security updates (update containers)
- [ ] Backup configuration files
- [ ] Document security policies

## 📞 Emergency Procedures

### If all servers down
```bash
# Check Ollama health on each server
for ip in 192.168.1.2 192.168.1.11 192.168.1.20; do
  echo "Checking $ip..."
  curl http://$ip:11434/api/tags
done
```

### If high error rate
```bash
# Check logs
docker-compose logs litellm-proxy | grep error

# Restart proxy
docker-compose restart litellm-proxy

# Check if guard is too strict
# Edit litellm_config.yaml and disable problematic scanner
```

### If port conflicts
```bash
# Find process using port
lsof -i :8000
lsof -i :80

# Change port in docker-compose.yml or release port
```

## 🎓 Key Concepts

**Load Balancing**: Distributing requests across multiple servers  
**Health Check**: Periodic verification that servers are responsive  
**Failover**: Automatic switch to backup server when primary fails  
**Rate Limiting**: Restricting requests to prevent abuse  
**Pre-call Hook**: Processing before sending to backend  
**Post-call Hook**: Processing after receiving from backend  
**Language Detection**: Automatically identifying input language  

---

**Quick Reference for LiteLLM Load Balancing with LLM Guard**  
**Last Updated**: October 17, 2025  
**Status**: Ready for Production ✅
