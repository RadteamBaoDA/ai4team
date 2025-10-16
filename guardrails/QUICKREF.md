# Ollama Guard Proxy - Quick Reference

## Installation

### Option 1: Local
```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
python ollama_guard_proxy.py
```

### Option 2: Docker
```bash
docker-compose up -d
```

### Option 3: Docker with Custom Config
```bash
docker-compose up -d -e OLLAMA_URL=http://your-ollama:11434
```

---

## Configuration

### Via Environment Variables
```bash
export OLLAMA_URL=http://127.0.0.1:11434
export PROXY_PORT=8080
export ENABLE_INPUT_GUARD=true
export ENABLE_OUTPUT_GUARD=true
export ENABLE_IP_FILTER=true
export IP_WHITELIST="192.168.1.0/24,10.0.0.0/8"
export IP_BLACKLIST="192.168.1.100"
python ollama_guard_proxy.py
```

### Via YAML Config
```yaml
ollama_url: http://127.0.0.1:11434
proxy_port: 8080
enable_input_guard: true
enable_output_guard: true
enable_ip_filter: true
ip_whitelist: "192.168.1.0/24,10.0.0.0/8"
```

---

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/health
```

### Generate (Non-Streaming)
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"What is AI?","stream":false}'
```

### Generate (Streaming)
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Tell a story","stream":true}'
```

### Chat Completion
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mistral",
    "messages":[{"role":"user","content":"Hello"}],
    "stream":false
  }'
```

### Get Config
```bash
curl http://localhost:8080/config
```

---

## Python Client

### Basic Usage
```python
from client_example import OllamaGuardClient

client = OllamaGuardClient("http://localhost:8080")

# Check health
health = client.health_check()

# Generate text
response = client.generate("What is machine learning?", model="mistral")
print(response["response"])

# Stream response
for chunk in client.generate("Tell a story", stream=True):
    if "response" in chunk:
        print(chunk["response"], end="", flush=True)

# Chat
messages = [{"role": "user", "content": "How are you?"}]
response = client.chat_completion(messages)
print(response["choices"][0]["message"]["content"])
```

### Command Line
```bash
# Test generation
python client_example.py --prompt "Explain quantum computing"

# Stream response
python client_example.py --prompt "Tell a joke" --stream

# Chat mode
python client_example.py --chat "Hello!"

# Check health
python client_example.py --health

# View config
python client_example.py --config
```

---

## Docker Commands

### Start
```bash
docker-compose up -d
```

### Stop
```bash
docker-compose down
```

### Restart
```bash
docker-compose restart ollama-guard-proxy
```

### View Logs
```bash
docker-compose logs -f ollama-guard-proxy
```

### Scale Instances
```bash
docker-compose up -d --scale ollama-guard-proxy=3
```

### Remove Everything
```bash
docker-compose down -v
```

---

## Nginx Setup

### Copy Config
```bash
sudo cp nginx-guard.conf /etc/nginx/conf.d/
```

### Test Configuration
```bash
sudo nginx -t
```

### Reload
```bash
sudo systemctl reload nginx
```

### With SSL (Self-Signed)
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/ollama.key \
  -out /etc/nginx/ssl/ollama.crt
sudo nginx -t
sudo systemctl reload nginx
```

---

## Monitoring & Debugging

### Health Status
```bash
curl http://localhost:8080/health | jq
```

### Check Ollama Connection
```bash
docker-compose exec ollama-guard-proxy \
  curl -s http://ollama:11434/api/tags | jq
```

### View Live Logs
```bash
docker-compose logs -f --tail=100 ollama-guard-proxy
```

### Test with IP Restriction
```bash
curl -H "X-Real-IP: 192.168.1.100" \
  http://localhost:8080/health
```

### Check IP Filtering Config
```bash
curl http://localhost:8080/config | jq '.enable_ip_filter'
```

---

## Common Issues

### Connection Refused
```bash
# Check Ollama is running
curl http://127.0.0.1:11434/api/tags

# Check proxy is running
curl http://localhost:8080/health

# Check logs
docker-compose logs ollama-guard-proxy
```

### IP Filtered Out
```bash
# Check whitelist/blacklist
curl http://localhost:8080/config | jq '.ip_whitelist, .ip_blacklist'

# Disable IP filter temporarily
export ENABLE_IP_FILTER=false
docker-compose restart
```

### High Memory Usage
```bash
# Check resources
docker stats ollama-guard-proxy

# Disable heavy scanners in config
enable_output_guard: false

# Restart with new config
docker-compose restart ollama-guard-proxy
```

### Slow Responses
```bash
# Check Ollama backend performance
time curl -X POST http://127.0.0.1:11434/api/generate \
  -d '{"model":"mistral","prompt":"test","stream":false}'

# Check proxy overhead
time curl -X POST http://localhost:8080/v1/generate \
  -d '{"model":"mistral","prompt":"test","stream":false}'
```

---

## Production Checklist

- [ ] Set `ENABLE_IP_FILTER=true` with appropriate whitelist
- [ ] Configure HTTPS in Nginx
- [ ] Set `BLOCK_ON_GUARD_ERROR=false` to prevent false blocks
- [ ] Enable logging and monitor regularly
- [ ] Backup configuration files
- [ ] Set up health monitoring
- [ ] Configure rate limiting (optional)
- [ ] Use strong SSL certificates (not self-signed)
- [ ] Set resource limits in Docker
- [ ] Enable auto-restart on failure

---

## Security Commands

### Enable Only Input Guard
```bash
export ENABLE_INPUT_GUARD=true
export ENABLE_OUTPUT_GUARD=false
```

### Enable Only Output Guard
```bash
export ENABLE_INPUT_GUARD=false
export ENABLE_OUTPUT_GUARD=true
```

### Strict IP Filtering (Whitelist Only)
```bash
export ENABLE_IP_FILTER=true
export IP_WHITELIST="10.0.0.0/8"
export IP_BLACKLIST=""
```

### Block Specific IPs
```bash
export ENABLE_IP_FILTER=true
export IP_BLACKLIST="192.168.1.100,10.0.0.0/8"
```

### Block on Any Guard Error
```bash
export BLOCK_ON_GUARD_ERROR=true
```

---

## Performance Tuning

### Reduce Guard Overhead
```yaml
# Disable unnecessary scanners
input_scanners:
  gibberish:
    enabled: false
  language:
    enabled: false

output_scanners:
  factual_consistency:
    enabled: false
```

### Increase Throughput
```bash
# Run multiple instances
docker-compose up -d --scale ollama-guard-proxy=5

# Use Nginx load balancing
sudo systemctl reload nginx
```

### Lower Latency
```yaml
# Use local Ollama
ollama_url: http://localhost:11434

# Disable heavy output scanners
enable_output_guard: false
```

---

## Backup & Restore

### Backup Configuration
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz \
  config.yaml docker-compose.yml .env
```

### Restore Configuration
```bash
tar -xzf backup-*.tar.gz
docker-compose restart
```

### Export Logs
```bash
docker-compose logs ollama-guard-proxy > logs-$(date +%Y%m%d).txt
```

---

## Update Procedure

### Update LLM Guard
```bash
pip install --upgrade llm-guard
pip freeze > requirements.txt
docker-compose build --no-cache
docker-compose up -d
```

### Update Proxy Code
```bash
git pull origin main
docker-compose build --no-cache
docker-compose up -d
docker-compose logs -f ollama-guard-proxy
```

---

## Testing Commands

### Load Test
```bash
# Simple stress test
for i in {1..100}; do
  curl -X POST http://localhost:8080/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"test","stream":false}' &
done
wait
```

### Latency Test
```bash
time curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"What is AI?","stream":false}'
```

### Streaming Test
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Tell a long story","stream":true}' | head -20
```

---

## Useful Links

- **Full Documentation**: See `SOLUTION.md`
- **Deployment Guide**: See `DEPLOYMENT.md`
- **Usage Guide**: See `USAGE.md`
- **LLM Guard**: https://protectai.github.io/llm-guard/
- **Ollama**: https://ollama.ai
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker**: https://docs.docker.com/

---

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify health: `curl http://localhost:8080/health`
3. Review config: `curl http://localhost:8080/config`
4. Check Ollama: `curl http://ollama:11434/api/tags`
5. Review documentation files

---

Last Updated: October 16, 2025
