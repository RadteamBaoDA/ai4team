# Ollama Guard Proxy - Deployment Guide

Complete guide for deploying the Ollama Guard Proxy in various environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Nginx Integration](#nginx-integration)
5. [Scaling](#scaling)
6. [Monitoring](#monitoring)
7. [Security Hardening](#security-hardening)

---

## Local Development

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy configuration
cp config.example.yaml config.yaml

# 3. Ensure Ollama is running
# Start Ollama on your machine or ensure it's accessible at the configured URL

# 4. Run the proxy
python ollama_guard_proxy.py
```

### Environment Setup

```bash
# Set environment variables
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_PATH=/api/generate
export PROXY_PORT=8080
export ENABLE_INPUT_GUARD=true
export ENABLE_OUTPUT_GUARD=true

# Run proxy
python ollama_guard_proxy.py
```

### Testing

```bash
# Health check
curl http://localhost:8080/health

# Test generation
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "prompt": "What is Python?",
    "stream": false
  }'

# Run client example
python client_example.py --prompt "Explain machine learning"
```

---

## Docker Deployment

### Single Container

```bash
# Build image
docker build -t ollama-guard-proxy:latest .

# Run container
docker run -d \
  --name ollama-guard-proxy \
  -p 8080:8080 \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  -e ENABLE_INPUT_GUARD=true \
  -e ENABLE_OUTPUT_GUARD=true \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  ollama-guard-proxy:latest

# Check logs
docker logs -f ollama-guard-proxy

# Stop container
docker stop ollama-guard-proxy
docker rm ollama-guard-proxy
```

### Docker Compose (Recommended)

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f ollama-guard-proxy

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v
```

### Docker Compose with Custom Configuration

```bash
# Create .env file
cat > .env << EOF
OLLAMA_URL=http://ollama:11434
PROXY_PORT=8080
ENABLE_INPUT_GUARD=true
ENABLE_OUTPUT_GUARD=true
ENABLE_IP_FILTER=true
IP_WHITELIST=192.168.0.0/16,10.0.0.0/8
EOF

# Start with environment file
docker-compose --env-file .env up -d
```

---

## Production Deployment

### Prerequisites

- Ubuntu 20.04 LTS or similar
- Docker and Docker Compose installed
- Ollama running on the same or accessible network
- Nginx installed for reverse proxy (optional but recommended)
- SSL certificates (for HTTPS)

### System Requirements

- **CPU**: 2+ cores
- **RAM**: 4GB minimum (8GB recommended for NLP models)
- **Storage**: 20GB for LLM Guard models
- **Network**: Low-latency connection to Ollama backend

### Step-by-Step Deployment

#### 1. Clone Repository

```bash
git clone <repository-url>
cd guardrails
```

#### 2. Create Production Configuration

```bash
# Copy and customize config
cp config.example.yaml config.yaml

# Edit with production settings
nano config.yaml
```

**config.yaml** for production:

```yaml
ollama_url: http://ollama-backend:11434
ollama_path: /api/generate
proxy_host: 0.0.0.0
proxy_port: 8080

enable_ip_filter: true
ip_whitelist: "10.0.0.0/8,172.16.0.0/12"
ip_blacklist: ""

enable_input_guard: true
enable_output_guard: true
block_on_guard_error: false
```

#### 3. Create Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  ollama-guard-proxy:
    image: ollama-guard-proxy:latest
    container_name: ollama-guard-proxy-prod
    restart: always
    ports:
      - "8080:8080"
    environment:
      OLLAMA_URL: ${OLLAMA_URL:-http://ollama:11434}
      OLLAMA_PATH: /api/generate
      PROXY_HOST: 0.0.0.0
      PROXY_PORT: 8080
      ENABLE_INPUT_GUARD: "true"
      ENABLE_OUTPUT_GUARD: "true"
      ENABLE_IP_FILTER: "true"
      IP_WHITELIST: "${IP_WHITELIST}"
      CONFIG_FILE: /app/config.yaml
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./logs:/app/logs
    networks:
      - ollama_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  ollama_network:
    driver: bridge
```

#### 4. Deploy

```bash
# Build image for production
docker build -t ollama-guard-proxy:prod .

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f ollama-guard-proxy
```

#### 5. Verify Installation

```bash
# Health check
curl http://localhost:8080/health

# Check configuration
curl http://localhost:8080/config

# Test with sample request
python client_example.py --proxy http://localhost:8080 --prompt "Test"
```

---

## Nginx Integration

### Basic Reverse Proxy Setup

```bash
# Copy Nginx configuration
sudo cp nginx-guard.conf /etc/nginx/conf.d/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Configuration with SSL

```bash
# 1. Generate self-signed certificate (for testing)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/ollama.key \
  -out /etc/nginx/ssl/ollama.crt

# 2. Update paths in nginx-guard.conf
sudo nano /etc/nginx/conf.d/ollama-guard.conf

# 3. Test and reload
sudo nginx -t
sudo systemctl reload nginx

# 4. Access via HTTPS
curl https://ollama.ai4team.vn/v1/generate \
  --cacert /etc/nginx/ssl/ollama.crt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'
```

### Nginx with Multiple Proxy Instances

```nginx
# Scale to multiple instances
upstream ollama_guard_proxy {
    least_conn;
    server 127.0.0.1:8080 weight=1;
    server 127.0.0.1:8081 weight=1;
    server 127.0.0.1:8082 weight=1;
}
```

Start multiple instances:

```bash
# Start 3 instances on different ports
for port in 8080 8081 8082; do
  PROXY_PORT=$port docker-compose up -d ollama-guard-proxy-$port
done
```

---

## Scaling

### Horizontal Scaling with Docker

```bash
# Scale with Docker Compose
docker-compose up -d --scale ollama-guard-proxy=3

# Use load balancer (Nginx, HAProxy, or cloud LB)
```

### Kubernetes Deployment (Optional)

```yaml
# ollama-guard-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-guard-proxy
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ollama-guard-proxy
  template:
    metadata:
      labels:
        app: ollama-guard-proxy
    spec:
      containers:
      - name: ollama-guard-proxy
        image: ollama-guard-proxy:latest
        ports:
        - containerPort: 8080
        env:
        - name: OLLAMA_URL
          value: "http://ollama-service:11434"
        - name: ENABLE_INPUT_GUARD
          value: "true"
        - name: ENABLE_OUTPUT_GUARD
          value: "true"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: ollama-guard-proxy-service
  namespace: default
spec:
  selector:
    app: ollama-guard-proxy
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

Deploy to Kubernetes:

```bash
kubectl apply -f ollama-guard-deployment.yaml
kubectl get pods
kubectl logs -f deployment/ollama-guard-proxy
```

---

## Monitoring

### Prometheus Metrics (Optional Enhancement)

Add to `ollama_guard_proxy.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
request_count = Counter('ollama_guard_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
guard_blocks = Counter('ollama_guard_blocks_total', 'Blocked requests', ['reason'])
response_time = Histogram('ollama_guard_response_seconds', 'Response time')

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Log Monitoring

```bash
# Monitor logs in real-time
docker-compose logs -f ollama-guard-proxy

# Search logs for errors
docker-compose logs ollama-guard-proxy | grep ERROR

# Export logs for analysis
docker-compose logs ollama-guard-proxy > logs-$(date +%Y%m%d).txt
```

### Health Monitoring Script

```bash
#!/bin/bash
# monitor-health.sh

while true; do
  status=$(curl -s http://localhost:8080/health | jq -r '.status')
  if [ "$status" != "healthy" ]; then
    echo "[$(date)] Alert: Proxy unhealthy!"
    # Add your alert logic here (email, Slack, PagerDuty, etc.)
  fi
  sleep 60
done
```

---

## Security Hardening

### 1. Network Security

```bash
# Use internal network only
docker network create --internal ollama_internal
```

### 2. IP Filtering

```bash
# Enable IP whitelist in production
export ENABLE_IP_FILTER=true
export IP_WHITELIST="10.0.0.0/8,172.16.0.0/12"
```

### 3. HTTPS Only

```bash
# Update Nginx to redirect HTTP to HTTPS
return 301 https://$server_name$request_uri;
```

### 4. Authentication (Optional)

Add to `ollama_guard_proxy.py`:

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/v1/generate")
async def proxy_generate(request: Request, credentials: HTTPAuthCredentials = Depends(security)):
    # Verify token
    if credentials.credentials != "your-secret-token":
        raise HTTPException(status_code=403, detail="Invalid credentials")
    # ... rest of function
```

### 5. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/v1/generate")
@limiter.limit("100/minute")
async def proxy_generate(request: Request):
    # ... function body
```

### 6. Docker Security

```bash
# Run container with security options
docker run -d \
  --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp \
  ollama-guard-proxy:latest
```

---

## Troubleshooting Production Issues

### Issue: High Latency

**Solution**: Enable output buffering optimization:

```yaml
proxy_buffer_size: 256k
proxy_buffers: 8 512k
```

### Issue: Memory Leaks

**Solution**: Monitor and restart periodically:

```bash
# Docker restart policy
restart: unless-stopped
```

### Issue: LLM Guard Models Not Loading

**Solution**: Increase startup time:

```yaml
healthcheck:
  start_period: 120s  # Increase from 60s
```

### Issue: Connection Refused to Ollama

**Solution**: Check Ollama accessibility:

```bash
# From proxy container
docker-compose exec ollama-guard-proxy \
  curl -v http://ollama:11434/api/tags
```

---

## Maintenance

### Regular Backups

```bash
# Backup configuration
tar -czf backup-$(date +%Y%m%d).tar.gz config.yaml

# Backup logs
tar -czf logs-$(date +%Y%m%d).tar.gz logs/
```

### Update Procedure

```bash
# 1. Pull latest changes
git pull origin main

# 2. Rebuild image
docker build -t ollama-guard-proxy:latest .

# 3. Stop old container
docker-compose down

# 4. Start new container
docker-compose up -d

# 5. Verify
docker-compose logs -f ollama-guard-proxy
```

---

## Support and Debugging

For issues:

1. Check logs: `docker-compose logs`
2. Verify Ollama: `curl http://ollama:11434/api/tags`
3. Test health: `curl http://localhost:8080/health`
4. Review configuration: `curl http://localhost:8080/config`
5. Check IP access: Review nginx/proxy logs for IP-related errors

---

## Performance Tuning

### Optimize for Low Latency

```yaml
# config.yaml
ollama_url: http://ollama-local:11434  # Use local/LAN connection

# Remove heavy output scanners if not needed
output_scanners:
  toxicity:
    enabled: false  # Disable if not critical
```

### Optimize for High Throughput

```bash
# Run multiple instances
docker-compose up -d --scale ollama-guard-proxy=5

# Use hardware accelerated LLM Guard
# (requires compatible GPU)
export CUDA_VISIBLE_DEVICES=0
```

### Resource Allocation

```yaml
# docker-compose.yml
resources:
  limits:
    cpus: '2'
    memory: 4G
  reservations:
    cpus: '1'
    memory: 2G
```

---

End of Deployment Guide
