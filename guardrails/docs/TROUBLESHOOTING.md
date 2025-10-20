# Ollama Guard Proxy - Troubleshooting Guide

## Quick Diagnosis

### Step 1: Check Service Status
```bash
# Check if services are running
docker-compose ps

# Expected output:
# NAME                    STATUS
# ollama                  Up
# ollama-guard-proxy      Up (healthy)
```

### Step 2: Check Connectivity
```bash
# Test proxy
curl http://localhost:8080/health

# Test Ollama
curl http://localhost:11434/api/tags

# Test through proxy
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test","stream":false}'
```

### Step 3: Review Logs
```bash
docker-compose logs ollama-guard-proxy | tail -50
docker-compose logs ollama | tail -50
```

---

## Common Issues & Solutions

### ❌ Issue: "Connection refused" to Ollama

**Symptoms**:
```
ConnectionError: ('Connection aborted.', RemoteDisconnected(...))
Error: upstream_error
```

**Solutions**:
1. Check Ollama is running:
   ```bash
   docker-compose ps ollama
   docker-compose exec ollama curl http://127.0.0.1:11434/api/tags
   ```

2. Check OLLAMA_URL configuration:
   ```bash
   curl http://localhost:8080/config | jq '.ollama_url'
   ```

3. If using Docker, ensure correct hostname:
   ```bash
   # Inside docker-compose
   OLLAMA_URL=http://ollama:11434  # Use service name, not localhost
   ```

4. If using external Ollama:
   ```bash
   export OLLAMA_URL=http://your-ollama-host:11434
   docker-compose up -d
   ```

**Verification**:
```bash
# Test direct connectivity
docker-compose exec ollama-guard-proxy \
  curl -v http://ollama:11434/api/tags
```

---

### ❌ Issue: "400 Request Header Or Cookie Too Large"

**Symptoms**:
```
HTTP 400
400 Bad Request
Request Header Or Cookie Too Large
```

**Solutions**:
1. Update proxy buffer sizes (already done):
   - Check `config.yaml` includes buffer settings
   
2. In nginx-guard.conf:
   ```nginx
   client_header_buffer_size 16k;
   large_client_header_buffers 8 64k;
   ```

3. Increase if needed:
   ```nginx
   client_header_buffer_size 32k;
   large_client_header_buffers 16 128k;
   ```

4. Reload Nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

**Verification**:
```bash
# Check Nginx buffer config
sudo nginx -T | grep -A 5 "buffer"
```

---

### ❌ Issue: "Access denied" / IP filtered

**Symptoms**:
```
HTTP 403
{
  "error": "access_denied",
  "reason": "IP 192.168.1.50 is not in whitelist"
}
```

**Solutions**:
1. Check IP filtering status:
   ```bash
   curl http://localhost:8080/config | jq '.enable_ip_filter'
   ```

2. Check whitelist/blacklist:
   ```bash
   curl http://localhost:8080/config | jq '.ip_whitelist, .ip_blacklist'
   ```

3. Get your client IP:
   ```bash
   curl http://localhost:8080/config | jq '.ip_whitelist'
   # Then check what IP you're connecting from
   hostname -I
   ```

4. Disable temporarily to test:
   ```bash
   export ENABLE_IP_FILTER=false
   docker-compose restart
   curl http://localhost:8080/health
   ```

5. Add your IP to whitelist:
   ```bash
   export IP_WHITELIST="192.168.1.0/24,10.0.0.0/8"
   docker-compose restart
   ```

**Verification**:
```bash
# Test with specific IP header
curl -H "X-Real-IP: 192.168.1.100" http://localhost:8080/health

# Check if your IP is being read correctly
docker-compose exec ollama-guard-proxy python -c \
  "from ipaddress import ip_address; print(ip_address('192.168.1.100'))"
```

---

### ❌ Issue: "Prompt blocked" / Input guard rejection

**Symptoms**:
```
HTTP 400
{
  "error": "prompt_blocked",
  "details": {
    "allowed": false,
    "scanners": {
      "Toxicity": {"passed": false, "reason": "..."}
    }
  }
}
```

**Solutions**:
1. Check which scanner blocked it:
   - Look at the error details
   - Common blockers: Toxicity, PromptInjection, Secrets

2. Disable specific scanner (if false positive):
   - Edit `config.yaml`
   - Set scanner `enabled: false`
   - Restart: `docker-compose restart`

3. Adjust threshold (for Toxicity):
   ```yaml
   input_scanners:
     toxicity:
       threshold: 0.7  # Higher = less sensitive (0-1)
   ```

4. Temporarily disable input guard:
   ```bash
   export ENABLE_INPUT_GUARD=false
   docker-compose restart
   ```

**Verification**:
```bash
# Test with benign prompt
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"hello world","stream":false}'

# Check scanner configuration
curl http://localhost:8080/config | jq '.input_scanners'
```

---

### ❌ Issue: "Response blocked" / Output guard rejection

**Symptoms**:
```
HTTP 400
{
  "error": "response_blocked",
  "details": {
    "allowed": false,
    "scanners": {
      "Toxicity": {"passed": false}
    }
  }
}
```

**Solutions**:
1. Check which output scanner blocked:
   - Common blockers: Toxicity, MaliciousURLs, NoRefusal

2. Disable specific scanner:
   ```yaml
   output_scanners:
     toxicity:
       enabled: false
   ```

3. Adjust output guard:
   ```bash
   export ENABLE_OUTPUT_GUARD=false
   docker-compose restart
   ```

4. Check model behavior:
   - Some models are more likely to trigger guards
   - Try different model or prompt
   - Try with `block_on_guard_error=false`

**Verification**:
```bash
# Test with different model
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"what is python","stream":false}'

# Check output guard config
curl http://localhost:8080/config | jq '.output_scanners'
```

---

### ❌ Issue: Proxy starts but models don't work

**Symptoms**:
- Health check returns 200
- But requests fail with errors
- Ollama lists models but proxy can't use them

**Solutions**:
1. Verify Ollama has models:
   ```bash
   docker-compose exec ollama ollama list
   ```

2. Test Ollama directly:
   ```bash
   curl -X POST http://localhost:11434/api/generate \
     -d '{"model":"mistral","prompt":"test"}'
   ```

3. Check model name spelling:
   ```bash
   # In your request, model name must match exactly
   curl -X POST http://localhost:8080/v1/generate \
     -d '{"model":"mistral","prompt":"test"}'
   ```

4. Pull missing model:
   ```bash
   docker-compose exec ollama ollama pull mistral
   ```

**Verification**:
```bash
# Ensure model is available
docker-compose exec ollama ollama list | grep mistral

# Try direct request to Ollama
docker-compose exec ollama curl http://127.0.0.1:11434/api/generate \
  -d '{"model":"mistral","prompt":"test"}'
```

---

### ❌ Issue: High Memory Usage

**Symptoms**:
```
docker stats
CONTAINER     MEM USAGE
ollama        5.2G / 8G
proxy         2.1G / 4G
```

**Solutions**:
1. Check what's using memory:
   ```bash
   docker stats --no-stream
   ```

2. Disable output guard (uses NLP models):
   ```bash
   export ENABLE_OUTPUT_GUARD=false
   docker-compose restart
   ```

3. Limit container memory:
   ```yaml
   # docker-compose.yml
   services:
     ollama-guard-proxy:
       resources:
         limits:
           memory: 2G
         reservations:
           memory: 1G
   ```

4. Check for memory leaks:
   ```bash
   # Monitor over time
   watch docker stats
   ```

5. Restart service:
   ```bash
   docker-compose restart ollama-guard-proxy
   ```

**Verification**:
```bash
# Check memory before/after
docker stats ollama-guard-proxy --no-stream
docker-compose restart
sleep 10
docker stats ollama-guard-proxy --no-stream
```

---

### ❌ Issue: Slow Responses / High Latency

**Symptoms**:
- Requests take > 5 seconds
- Even simple requests are slow
- Streaming is very slow

**Solutions**:
1. Measure proxy overhead:
   ```bash
   # Direct to Ollama
   time curl http://localhost:11434/api/generate \
     -d '{"model":"mistral","prompt":"test","stream":false}'
   
   # Through proxy
   time curl http://localhost:8080/v1/generate \
     -d '{"model":"mistral","prompt":"test","stream":false}'
   ```

2. Disable guards to measure overhead:
   ```bash
   export ENABLE_INPUT_GUARD=false
   export ENABLE_OUTPUT_GUARD=false
   docker-compose restart
   ```

3. Check for network latency:
   ```bash
   docker-compose exec ollama-guard-proxy \
     ping -c 5 ollama
   ```

4. Optimize Nginx buffering:
   ```nginx
   proxy_buffering off;
   proxy_request_buffering off;
   ```

5. Use local Ollama:
   ```bash
   # Avoid network latency
   OLLAMA_URL=http://127.0.0.1:11434  # local
   # vs
   OLLAMA_URL=http://remote-host:11434  # remote
   ```

**Verification**:
```bash
# Compare with/without guards
echo "With guards:"
time curl http://localhost:8080/v1/generate \
  -d '{"model":"mistral","prompt":"hi","stream":false}'

export ENABLE_INPUT_GUARD=false
export ENABLE_OUTPUT_GUARD=false
docker-compose restart

echo "Without guards:"
time curl http://localhost:8080/v1/generate \
  -d '{"model":"mistral","prompt":"hi","stream":false}'
```

---

### ❌ Issue: LLM Guard models not loading

**Symptoms**:
```
WARNING: LLM Guard not installed
or
ModuleNotFoundError: No module named 'llm_guard'
or
Startup takes 60+ seconds
```

**Solutions**:
1. Verify installation:
   ```bash
   pip install llm-guard
   python -c "import llm_guard; print(llm_guard.__version__)"
   ```

2. Check Docker logs:
   ```bash
   docker-compose logs ollama-guard-proxy | grep -i guard
   ```

3. Increase startup time:
   ```yaml
   healthcheck:
     start_period: 120s  # Increase from 60s
   ```

4. Rebuild Docker image:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

5. Skip guard initialization:
   ```bash
   export ENABLE_INPUT_GUARD=false
   export ENABLE_OUTPUT_GUARD=false
   docker-compose restart
   ```

**Verification**:
```bash
# Check inside container
docker-compose exec ollama-guard-proxy \
  python -c "import llm_guard; print('OK')"

# Check startup logs
docker-compose logs ollama-guard-proxy | head -30
```

---

### ❌ Issue: Streaming responses stop early

**Symptoms**:
```
Streaming starts but stops after few chunks
Incomplete response
Output blocked error in middle of stream
```

**Solutions**:
1. Check error in stream:
   ```bash
   curl -X POST http://localhost:8080/v1/generate \
     -d '{"model":"mistral","prompt":"long text","stream":true}' | tail
   ```

2. Disable output guard for streaming:
   ```bash
   export ENABLE_OUTPUT_GUARD=false
   docker-compose restart
   ```

3. Increase timeout:
   ```yaml
   # In nginx-guard.conf or proxy settings
   proxy_read_timeout 600s;  # 10 minutes
   ```

4. Check for accumulated text issues:
   - Edit `ollama_guard_proxy.py`
   - Increase chunk size for scanning
   - See `stream_response_with_guard()` function

**Verification**:
```bash
# Test streaming without output guard
curl -X POST http://localhost:8080/v1/generate \
  -d '{"model":"mistral","prompt":"tell a long story","stream":true}' | wc -l
```

---

### ❌ Issue: Nginx "502 Bad Gateway"

**Symptoms**:
```
HTTP 502
502 Bad Gateway
```

**Solutions**:
1. Check upstream is running:
   ```bash
   docker-compose ps ollama-guard-proxy
   curl http://localhost:8080/health
   ```

2. Check Nginx config:
   ```bash
   sudo nginx -t
   ```

3. Check Nginx logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

4. Verify upstream address:
   ```bash
   # In nginx-guard.conf
   upstream ollama_guard_proxy {
       server 127.0.0.1:8080;  # Must match proxy port
   }
   ```

5. Reload Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

**Verification**:
```bash
# Test direct connection
curl http://127.0.0.1:8080/health

# Test through Nginx
curl http://ollama.ai4team.vn/health

# Check upstream status
sudo nginx -T | grep -A 5 "upstream"
```

---

### ❌ Issue: Docker container keeps restarting

**Symptoms**:
```
docker-compose ps
Status: Restarting (1) 5 seconds ago
Status: Restarting (1) 10 seconds ago
```

**Solutions**:
1. Check logs for errors:
   ```bash
   docker-compose logs --tail=100 ollama-guard-proxy
   ```

2. Look for common errors:
   - Port already in use: `Address already in use`
   - Import errors: `ModuleNotFoundError`
   - Config errors: `FileNotFoundError`

3. Check port conflicts:
   ```bash
   # Port 8080 in use?
   lsof -i :8080
   # Kill if needed
   kill -9 <PID>
   ```

4. Rebuild image:
   ```bash
   docker-compose build --no-cache ollama-guard-proxy
   docker-compose up -d
   ```

5. Check resource limits:
   ```bash
   docker stats  # See if OOMKilled
   ```

**Verification**:
```bash
# Check detailed logs
docker-compose logs -f ollama-guard-proxy

# Check if it stays running
docker-compose up -d
sleep 30
docker-compose ps
```

---

## Diagnostic Commands

### Check Everything
```bash
#!/bin/bash
echo "=== Services Status ==="
docker-compose ps

echo -e "\n=== Proxy Health ==="
curl http://localhost:8080/health 2>/dev/null | jq

echo -e "\n=== Ollama Status ==="
curl http://localhost:11434/api/tags 2>/dev/null | jq

echo -e "\n=== Proxy Config ==="
curl http://localhost:8080/config 2>/dev/null | jq '.enable_input_guard, .enable_output_guard, .enable_ip_filter'

echo -e "\n=== Docker Resources ==="
docker stats --no-stream

echo -e "\n=== Recent Logs ==="
docker-compose logs --tail=20 ollama-guard-proxy
```

### Network Diagnostics
```bash
# Test DNS resolution
docker-compose exec ollama-guard-proxy \
  getent hosts ollama

# Test connectivity
docker-compose exec ollama-guard-proxy \
  ping -c 5 ollama

# Test ports
docker-compose exec ollama-guard-proxy \
  netstat -tlnp
```

### Configuration Dump
```bash
# Export current config
curl http://localhost:8080/config > config-dump.json
cat config-dump.json | jq
```

---

## Emergency Procedures

### Restart Everything
```bash
docker-compose down -v
docker-compose up -d
sleep 30
docker-compose logs -f
```

### Reset to Defaults
```bash
# Remove containers
docker-compose down

# Remove images
docker rmi ollama-guard-proxy:latest ollama:latest

# Recreate
docker-compose up -d --build
```

### Clear Logs
```bash
# Docker compose logs
docker-compose logs --all --remove ollama-guard-proxy

# Or just restart without history
docker-compose restart
```

### Hard Reset
```bash
# Complete removal
docker-compose down -v

# Remove images and volumes
docker volume prune -f
docker image prune -a -f

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

---

## Performance Diagnostics

### Measure Proxy Overhead
```bash
# Test 1: Direct to Ollama (baseline)
time for i in {1..10}; do
  curl -s http://localhost:11434/api/generate \
    -d '{"model":"mistral","prompt":"test","stream":false}' > /dev/null
done

# Test 2: Through Proxy
time for i in {1..10}; do
  curl -s http://localhost:8080/v1/generate \
    -d '{"model":"mistral","prompt":"test","stream":false}' > /dev/null
done

# Difference = proxy overhead
```

### Load Testing
```bash
# Simple load test (10 concurrent requests)
for i in {1..10}; do (
  curl -X POST http://localhost:8080/v1/generate \
    -d '{"model":"mistral","prompt":"test","stream":false}' \
    -s > /dev/null
) & done
wait

# Monitor
docker stats
```

---

## When All Else Fails

1. **Check logs thoroughly**:
   ```bash
   docker-compose logs --all
   ```

2. **Test each component separately**:
   - Test Ollama: `curl localhost:11434/api/tags`
   - Test Proxy: `curl localhost:8080/health`
   - Test Nginx: `curl ollama.ai4team.vn/health`

3. **Try with minimal config**:
   ```bash
   export ENABLE_INPUT_GUARD=false
   export ENABLE_OUTPUT_GUARD=false
   export ENABLE_IP_FILTER=false
   docker-compose restart
   ```

4. **Verify dependencies installed**:
   ```bash
   pip list | grep -E "fastapi|llm-guard|pydantic"
   ```

5. **Check documentation**:
   - USAGE.md - Common usage issues
   - DEPLOYMENT.md - Deployment issues
   - README - LLM Guard specifics

6. **Ask for help** with:
   - Full error messages
   - Docker logs
   - Configuration (non-sensitive)
   - System info (OS, Python version, Docker version)

---

## Support Contacts

- **LLM Guard Issues**: https://github.com/protectai/llm-guard/issues
- **Ollama Issues**: https://github.com/ollama/ollama/issues
- **FastAPI Issues**: https://github.com/tiangolo/fastapi/issues
- **Docker Issues**: https://github.com/moby/moby/issues

---

Last Updated: October 16, 2025
