# Ollama Guard Proxy - Nginx-Only Deployment Examples

## Complete End-to-End Example

This file shows complete, copy-paste-ready examples for deploying the proxy with Nginx-only access.

---

## Example 1: Local Development (Single Machine)

### Setup Files

**1. Start Ollama**
```bash
# Terminal 1
ollama serve
```

**2. Start Proxy with Nginx-Only Access**
```bash
# Terminal 2
cd /path/to/guardrails

export OLLAMA_URL="http://127.0.0.1:11434"
export PROXY_PORT=8080
export NGINX_WHITELIST="127.0.0.1"

./run_proxy.sh start
```

**3. Nginx Configuration**
```nginx
# /etc/nginx/conf.d/ollama-proxy.conf

upstream ollama_proxy {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name localhost;
    
    location /api/ {
        proxy_pass http://ollama_proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

**4. Restart Nginx**
```bash
sudo systemctl restart nginx
```

**5. Test**
```bash
# Direct access (should fail - 403)
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello"}'
# Response: 403 Forbidden

# Through Nginx (should work)
curl -X POST http://localhost/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello"}'
# Response: 200 OK (after scanning)
```

---

## Example 2: Remote Nginx + Proxy on Different Servers

### Setup Files

**Proxy Server (192.168.1.50)**

```bash
# Start proxy
export OLLAMA_URL="http://127.0.0.1:11434"
export PROXY_PORT=8080
export NGINX_WHITELIST="192.168.1.10"  # Nginx server IP

./run_proxy.sh start
```

**Nginx Server (192.168.1.10)**

```nginx
# /etc/nginx/conf.d/ollama-api.conf

upstream ollama_proxy {
    server 192.168.1.50:8080;  # Proxy server IP
}

server {
    listen 80;
    server_name api.example.local;
    
    location /api/ {
        proxy_pass http://ollama_proxy;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_connect_timeout 30s;
    }
}
```

**Test from Client Machine**
```bash
# Add to /etc/hosts on client
192.168.1.10  api.example.local

# Make request
curl -X POST http://api.example.local/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello"}'
```

---

## Example 3: Docker Compose (Complete Stack)

**docker-compose.yml**
```yaml
version: '3.8'

services:
  # Ollama backend
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - ollama-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Guard proxy (internal only)
  proxy:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ollama-proxy
    environment:
      - OLLAMA_URL=http://ollama:11434
      - PROXY_PORT=8080
      - PROXY_HOST=0.0.0.0
      - NGINX_WHITELIST=nginx  # Nginx container hostname
      - ENABLE_INPUT_GUARD=true
      - ENABLE_OUTPUT_GUARD=true
    ports:
      - "8080:8080"
    depends_on:
      ollama:
        condition: service_healthy
    networks:
      - ollama-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Nginx reverse proxy (public facing)
  nginx:
    image: nginx:alpine
    container_name: ollama-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      proxy:
        condition: service_healthy
    networks:
      - ollama-net

volumes:
  ollama-data:

networks:
  ollama-net:
    driver: bridge
```

**nginx.conf**
```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    upstream ollama_proxy {
        server proxy:8080;
    }

    server {
        listen 80;
        server_name _;
        
        client_max_body_size 100M;

        location / {
            proxy_pass http://ollama_proxy;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 30s;
        }
    }
}
```

**Dockerfile**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn requests pyyaml llm-guard

# Copy proxy
COPY ollama_guard_proxy.py .
COPY requirements.txt .

# Run proxy
CMD ["python", "ollama_guard_proxy.py"]
```

**Deploy**
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f proxy

# Test
curl http://localhost/api/generate -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello"}'

# Stop services
docker-compose down
```

---

## Example 4: Kubernetes Deployment

**namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ollama
```

**ollama-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: ollama
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
      volumes:
      - name: ollama-data
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: ollama
  namespace: ollama
spec:
  clusterIP: None
  selector:
    app: ollama
  ports:
  - port: 11434
    targetPort: 11434
```

**proxy-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-proxy
  namespace: ollama
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-proxy
  template:
    metadata:
      labels:
        app: ollama-proxy
    spec:
      containers:
      - name: proxy
        image: ollama-proxy:latest
        ports:
        - containerPort: 8080
        env:
        - name: OLLAMA_URL
          value: "http://ollama:11434"
        - name: PROXY_PORT
          value: "8080"
        - name: NGINX_WHITELIST
          value: "10.244.0.0/16"  # Kubernetes pod CIDR
        - name: ENABLE_INPUT_GUARD
          value: "true"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: ollama-proxy
  namespace: ollama
spec:
  selector:
    app: ollama-proxy
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
```

**nginx-ingress.yaml**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ollama-api
  namespace: ollama
spec:
  ingressClassName: nginx
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: ollama-proxy
            port:
              number: 8080
```

**Deploy to Kubernetes**
```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy services
kubectl apply -f ollama-deployment.yaml
kubectl apply -f proxy-deployment.yaml
kubectl apply -f nginx-ingress.yaml

# Check status
kubectl get pods -n ollama
kubectl logs -f -n ollama deployment/ollama-proxy

# Test (port forward)
kubectl port-forward -n ollama svc/ollama-proxy 8080:8080
curl http://localhost:8080/health
```

---

## Example 5: Multi-Node Proxy Setup (HA)

**config.yaml (Shared)**
```yaml
nginx_whitelist:
  - "192.168.1.0/24"      # Nginx servers subnet
  - "10.0.0.0/8"          # Backup region

enable_input_guard: true
enable_output_guard: true
```

**Proxy Node 1 (192.168.1.50)**
```bash
export CONFIG_FILE="config.yaml"
export OLLAMA_URL="http://127.0.0.1:11434"
export PROXY_PORT=8080

./run_proxy.sh start
```

**Proxy Node 2 (192.168.1.51)**
```bash
export CONFIG_FILE="config.yaml"
export OLLAMA_URL="http://127.0.0.1:11434"
export PROXY_PORT=8080

./run_proxy.sh start
```

**Nginx Load Balancer (192.168.1.10)**
```nginx
upstream ollama_proxy_cluster {
    server 192.168.1.50:8080;
    server 192.168.1.51:8080;
}

server {
    listen 80;
    server_name api.example.local;
    
    location /api/ {
        proxy_pass http://ollama_proxy_cluster;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        
        # Health check
        access_log /var/log/nginx/ollama-api.log;
    }
}
```

---

## Example 6: Production Checklist

**Pre-Deployment**
```bash
# [ ] Identify all Nginx server IPs
ips_to_whitelist="192.168.1.10,192.168.1.11"

# [ ] Test IP whitelist configuration locally
export NGINX_WHITELIST="127.0.0.1"
./run_proxy.sh start

# [ ] Verify Nginx headers are set
# grep "X-Forwarded-For" nginx.conf

# [ ] Test access through Nginx
curl http://localhost:8080/health

# [ ] Check logs for access
./run_proxy.sh logs | tail -10

# [ ] Verify guards are enabled
curl http://localhost:8080/config | jq '.enable_input_guard'

# [ ] Test reject scenario
curl http://localhost:8080/api/generate
# Should return 403
```

**Deployment**
```bash
# [ ] Deploy proxy with whitelist
export NGINX_WHITELIST="$ips_to_whitelist"
./run_proxy.sh start

# [ ] Deploy Nginx pointing to proxy
systemctl restart nginx

# [ ] Monitor logs
./run_proxy.sh logs

# [ ] Test application endpoints
curl http://api.example.com/api/generate

# [ ] Setup monitoring/alerting
# Monitor for: 403 errors, response times, uptime
```

**Post-Deployment**
```bash
# [ ] Document whitelist IPs
# echo "Proxy whitelist: $ips_to_whitelist"

# [ ] Setup log rotation
# sudo touch /etc/logrotate.d/ollama-proxy

# [ ] Setup backup
# crontab -e

# [ ] Document runbook
# Create RUNBOOK.md with troubleshooting steps

# [ ] Update monitoring dashboard
# Add /health and /config endpoints
```

---

## Quick Copy-Paste Commands

### Local Testing
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Proxy
export OLLAMA_URL="http://127.0.0.1:11434"
export PROXY_PORT=8080
export NGINX_WHITELIST="127.0.0.1"
cd guardrails && ./run_proxy.sh start

# Terminal 3: Start Nginx
sudo systemctl restart nginx

# Terminal 4: Test
curl http://localhost/api/generate -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'
```

### Remote Deployment
```bash
# On Proxy Server
export NGINX_WHITELIST="<nginx-ip>"
./run_proxy.sh start

# On Nginx Server
# Edit nginx config to point to proxy server IP
# Restart nginx
sudo systemctl restart nginx

# Test from client
curl http://<nginx-ip>/api/generate
```

### Docker Stack
```bash
# Build and deploy
docker-compose build
docker-compose up -d
docker-compose logs -f

# Test
curl http://localhost/api/generate

# Clean up
docker-compose down
```

---

## Troubleshooting During Deployment

### Test 1: Proxy Starts but Returns 403

```bash
# Check whitelist
curl http://localhost:8080/config | jq '.nginx_whitelist'

# Check actual client IP
./run_proxy.sh logs | tail -5

# Add your IP to whitelist
export NGINX_WHITELIST="<your-ip>"
./run_proxy.sh restart
```

### Test 2: Nginx Can't Connect to Proxy

```bash
# Check proxy is running
./run_proxy.sh status

# Check connectivity
curl http://localhost:8080/health

# Check nginx config
nginx -t

# Check logs
./run_proxy.sh logs | grep -i error
```

### Test 3: Client Can't Connect to Nginx

```bash
# Check Nginx is running
systemctl status nginx

# Test locally
curl http://localhost/api/

# Test from another machine
curl http://<nginx-ip>/api/

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## Summary

✅ **Local Dev** - Copy example 1 for single-machine setup
✅ **Remote** - Copy example 2 for multi-machine deployment
✅ **Docker** - Copy example 3 for containerized stack
✅ **Kubernetes** - Copy example 4 for cloud deployment
✅ **High-Availability** - Copy example 5 for multi-node proxy
✅ **Production** - Follow example 6 checklist

**Ready to deploy! 🚀**
