# LiteLLM Load Balancing Deployment Guide

## Quick Start

### Local Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ensure Ollama servers are running and accessible
ping 192.168.1.2
ping 192.168.1.11
ping 192.168.1.20

# 3. Run the proxy
python run_litellm_proxy.py

# 4. Test in another terminal
curl http://localhost:8000/v1/models
```

### Docker Deployment (Recommended)

```bash
# 1. Build and start all services
docker-compose up -d

# 2. Check services are running
docker-compose ps

# 3. View logs
docker-compose logs -f litellm-proxy

# 4. Test health
curl http://localhost/health

# 5. Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

## Configuration Steps

### Step 1: Configure Ollama Servers

Edit `litellm_config.yaml` - update Ollama server IPs:

```yaml
model_list:
  - model_name: ollama/llama3.2
    litellm_params:
      api_base: http://192.168.1.2:11434  # ← Change these
      
  - model_name: ollama/llama3.2
    litellm_params:
      api_base: http://192.168.1.11:11434  # ← Change these
```

**Verify connectivity:**

```bash
# Test each Ollama server
for server in 192.168.1.2 192.168.1.11 192.168.1.20; do
  echo "Testing $server..."
  curl -s http://$server:11434/api/tags | jq .
done
```

### Step 2: Configure Load Balancing Strategy

In `litellm_config.yaml`:

```yaml
load_balancing_config:
  strategy: "least_busy"  # Options: round_robin, least_busy, weighted
  enable_fallback: true
  health_check_enabled: true
  health_check_interval: 30
```

**Strategies:**

- **round_robin**: Rotate through servers sequentially
  ```yaml
  strategy: "round_robin"
  ```

- **least_busy** (recommended): Route to server with lowest load
  ```yaml
  strategy: "least_busy"
  ```

- **weighted**: Assign weights (e.g., new/powerful server gets more)
  ```yaml
  strategy: "weighted"
  model_list:
    - model_name: ollama/llama3.2
      litellm_params:
        api_base: http://192.168.1.2:11434
        weight: 1
      
    - model_name: ollama/llama3.2
      litellm_params:
        api_base: http://192.168.1.11:11434
        weight: 2  # Gets 2x more requests
  ```

### Step 3: Enable LLM Guard Security

In `litellm_config.yaml`:

```yaml
llm_guard:
  enabled: true
  
  input_scanning:
    enabled: true
    scanners:
      - BanSubstrings          # Block keywords
      - PromptInjection        # Detect injection
      - Toxicity               # Detect harmful content
      - Secrets                # Prevent credential leakage
      - TokenLimit             # Enforce limits
  
  output_scanning:
    enabled: true
    scanners:
      - BanSubstrings          # Filter responses
      - Toxicity               # Detect toxic output
      - MaliciousURLs          # Prevent phishing
      - NoRefusal              # Ensure compliance
      - NoCode                 # Prevent code gen
  
  multilingual_errors: true  # Localized error messages
```

### Step 4: Configure Rate Limiting

In `nginx-litellm.conf`:

```nginx
# Adjust request rates (requests per second)
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=health_limit:10m rate=30r/s;

# In location blocks:
location /v1/chat/completions {
    limit_req zone=chat_limit burst=20 nodelay;  # 5 req/s, burst 20
    # ...
}
```

**Common values:**
- Development: 30 req/s
- Production: 10 req/s  
- Restricted: 5 req/s

### Step 5: Configure SSL/TLS (Production)

1. **Get SSL certificates**:

```bash
# Using Let's Encrypt (example)
certbot certonly --standalone -d llm.ai4team.vn

# Copy certificates
mkdir -p ssl
cp /etc/letsencrypt/live/llm.ai4team.vn/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/llm.ai4team.vn/privkey.pem ssl/key.pem
```

2. **Or create self-signed (testing)**:

```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

3. **Update Nginx config**:

```nginx
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

### Step 6: Test the Setup

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. List models
curl http://localhost:8000/v1/models

# 3. Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'

# 4. Test with Nginx (if running)
curl http://localhost/health
```

## Advanced Configuration

### Health Checks

Configure automatic server health monitoring:

```yaml
health_check:
  endpoint: "/api/tags"
  expected_response_field: "models"
  unhealthy_threshold: 3      # Mark down after 3 failures
  healthy_threshold: 2        # Mark up after 2 successes
```

### Cost Tracking

Track usage and costs (useful for accounting):

```yaml
cost_tracking:
  enabled: true
  cost_per_1k_input_tokens: 0.0      # Ollama is typically free
  cost_per_1k_output_tokens: 0.0
```

Costs are included in response metadata.

### Caching

Enable response caching to reduce latency:

```yaml
cache:
  type: "redis"               # Use Redis for distributed caching
  redis_host: "redis"
  redis_port: 6379
  redis_db: 0
  ttl: 3600                   # Cache for 1 hour
```

### Fallback Strategy

Automatic failover to alternative models:

```yaml
fallback_models:
  ollama/llama3.2:
    - model_name: ollama/mistral
      provider: ollama
    
  ollama/mistral:
    - model_name: ollama/neural-chat
      provider: ollama
```

If `ollama/llama3.2` fails, automatically try `ollama/mistral`.

### Request Logging

Enable detailed logging:

```yaml
advanced:
  log_requests: true
  log_responses: true
  mask_sensitive_data: true
```

## Monitoring & Observability

### Prometheus Metrics

Access Prometheus UI: `http://localhost:9090`

Useful queries:

```promql
# Request rate (req/sec)
rate(litellm_request_count[1m])

# Error rate
rate(litellm_request_count{status="error"}[1m]) / rate(litellm_request_count[1m])

# P95 latency (milliseconds)
histogram_quantile(0.95, litellm_request_duration_seconds) * 1000

# Request count by model
sum(litellm_request_count) by (model)

# Token usage by model
sum(litellm_tokens_used) by (model, type)

# Cost by model
sum(litellm_cost) by (model)
```

### Grafana Dashboards

Access Grafana: `http://localhost:3000` (admin/admin)

1. **Add Prometheus datasource**:
   - Data Sources → Add → Prometheus
   - URL: http://prometheus:9090

2. **Import Dashboard**:
   - Create → Import → Paste JSON from `grafana_dashboard.json`
   - Or use community dashboards from Grafana Hub

3. **Create Custom Dashboard**:
   - Panel → Graph
   - Query: `rate(litellm_request_count[1m])`

### Logs

View service logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f litellm-proxy
docker-compose logs -f nginx

# Real-time filtering
docker-compose logs -f litellm-proxy | grep -i error
docker-compose logs -f litellm-proxy | grep -i "guard\|scan"
```

## Troubleshooting

### Issue: Requests failing with "No healthy backends"

**Solution:**

```bash
# 1. Check Ollama servers are running
curl http://192.168.1.2:11434/api/tags

# 2. Check LiteLLM sees them
curl http://localhost:8000/v1/models

# 3. Check firewall
ping 192.168.1.2
curl -v telnet://192.168.1.2:11434

# 4. Increase health check timeout
# Edit litellm_config.yaml:
health_check:
  health_check_timeout: 10  # Increase from 5
```

### Issue: Rate limiting blocking legitimate requests

**Solution:**

```bash
# 1. Check current limits
grep "limit_req_zone" nginx-litellm.conf

# 2. Increase limits
# Edit nginx-litellm.conf:
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;  # Increase

# 3. Reload Nginx
docker-compose exec nginx nginx -s reload
```

### Issue: High latency or timeouts

**Solution:**

```bash
# 1. Check Ollama server performance
time curl http://192.168.1.2:11434/api/generate -d '{"model":"llama3.2"}'

# 2. Increase timeouts in litellm_config.yaml:
model_list:
  - litellm_params:
      timeout: 600  # Increase from 300

# 3. Check LiteLLM logs
docker-compose logs litellm-proxy | grep -i timeout
```

### Issue: LLM Guard blocking valid requests

**Solution:**

```bash
# 1. Check which scanner is blocking
docker-compose logs litellm-proxy | grep -i "blocked"

# 2. Disable problematic scanner temporarily
# Edit litellm_config.yaml:
llm_guard:
  input_scanning:
    scanners:
      - PromptInjection  # Might be too aggressive
      # - Toxicity       # Disable temporarily to test

# 3. Adjust scanner settings
# (Scanner-specific configuration via LLM Guard)
```

## Performance Tuning

### Increase Throughput

```yaml
proxy_server:
  num_workers: 8              # Increase from 4
  max_concurrent_requests: 2000

load_balancing_config:
  strategy: "least_busy"      # Use least_busy, not round_robin
```

### Reduce Latency

```yaml
cache:
  type: "redis"
  ttl: 3600

advanced:
  retry_on_timeout: true
  max_retries: 1              # Reduce from 2
  retry_delay: 0.5            # Reduce from 1
```

### Scale Horizontally

1. **Add more Ollama servers** to `litellm_config.yaml`
2. **Run multiple LiteLLM proxies**:
   ```bash
   docker-compose up -d --scale litellm-proxy=3
   ```
3. **Load balance between LiteLLM instances** with another Nginx layer

## Production Checklist

- [ ] Configure all Ollama server IPs in `litellm_config.yaml`
- [ ] Choose load balancing strategy (recommend `least_busy`)
- [ ] Enable LLM Guard security scanners
- [ ] Configure SSL/TLS certificates
- [ ] Set up rate limiting appropriate for your SLA
- [ ] Configure firewall rules
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Test failover scenarios
- [ ] Document your configuration
- [ ] Set up alerting rules
- [ ] Plan backup/recovery procedures
- [ ] Load test the setup
- [ ] Document API endpoints for clients
- [ ] Train support team on troubleshooting

## Migration from Direct Ollama to LiteLLM

For existing clients using Ollama directly:

### Before
```python
import requests

response = requests.post(
    'http://192.168.1.2:11434/api/generate',
    json={'model': 'llama3.2', 'prompt': 'Hello'}
)
```

### After (minimal changes)
```python
import requests

# Just change the URL - API is identical!
response = requests.post(
    'http://localhost:8000/v1/completions',  # LiteLLM endpoint
    json={'model': 'ollama/llama3.2', 'prompt': 'Hello'}  # Note: model name changes
)
```

Or use OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key="not-needed-for-ollama",  # Dummy key
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="ollama/llama3.2",
    messages=[{"role": "user", "content": "Hello"}],
    stream=False
)

print(response.choices[0].message.content)
```

## Next Steps

1. **Deploy**: Follow Quick Start → Docker Deployment
2. **Configure**: Update Ollama server IPs
3. **Test**: Verify all endpoints work
4. **Monitor**: Set up Grafana dashboards
5. **Migrate**: Update client applications
6. **Scale**: Add more Ollama servers as needed

---

**Last Updated**: October 17, 2025
**Status**: Production Ready ✅
