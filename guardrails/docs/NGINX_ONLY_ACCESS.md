# Ollama Proxy - Nginx-Only Access Configuration

## Overview

The Ollama Guard Proxy now supports **IP whitelist restriction** to allow requests from **Nginx only**. This provides an additional security layer by preventing direct access to the proxy.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Nginx Reverse Proxy                                 │
│  (Allowed IP: configured in whitelist)              │
└─────────────────────────┬──────────────────────────┘
                          │ http://127.0.0.1:8080
                          │ (from trusted nginx)
┌─────────────────────────▼──────────────────────────┐
│  Ollama Guard Proxy                                  │
│  ✓ IP Whitelist Check                               │
│  ✓ LLM Guard Scanning                               │
│  ✓ Request Routing                                  │
└─────────────────────────┬──────────────────────────┘
                          │
                          ▼
                    Ollama Backends
```

## Quick Start (2 Minutes)

### Option 1: Environment Variable

```bash
# Allow requests from Nginx on same machine + specific IPs
export NGINX_WHITELIST="127.0.0.1,192.168.1.10"
./run_proxy.sh start

# Allow requests from Nginx on remote machine
export NGINX_WHITELIST="192.168.100.50"
./run_proxy.sh start
```

### Option 2: Configuration File

```yaml
# config.yaml
nginx_whitelist:
  - "127.0.0.1"          # Local nginx
  - "192.168.1.10"       # Remote nginx server
  - "10.0.0.0/24"        # Nginx cluster (CIDR notation)

enable_input_guard: true
enable_output_guard: true
```

```bash
export CONFIG_FILE="config.yaml"
./run_proxy.sh start
```

## Configuration Examples

### Example 1: Local Nginx Only

```bash
# Nginx and proxy on same machine
export NGINX_WHITELIST="127.0.0.1"
./run_proxy.sh start
```

**Nginx Configuration:**
```nginx
upstream ollama_proxy {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://ollama_proxy;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

### Example 2: Multiple Nginx Servers

```bash
# Allow from multiple nginx instances
export NGINX_WHITELIST="192.168.1.10,192.168.1.11,192.168.1.12"
./run_proxy.sh start
```

### Example 3: Nginx Cluster with CIDR

```yaml
# config.yaml
nginx_whitelist:
  - "192.168.1.0/24"    # Entire subnet (useful for Kubernetes)
  - "10.0.0.5"          # Specific backup server
```

### Example 4: Production Multi-Region Setup

```yaml
# config.yaml
nginx_whitelist:
  # Primary region
  - "192.168.100.0/24"
  
  # Backup region
  - "192.168.200.0/24"
  
  # Development/Testing
  - "10.0.0.50"
```

## Testing

### Test 1: Direct Access (Should Fail)

```bash
# This should be rejected (403 Forbidden)
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'

# Response:
# {
#   "error": "access_denied",
#   "message": "Access denied. Only requests from whitelisted IPs are allowed.",
#   "client_ip": "127.0.0.1"
# }
```

### Test 2: From Nginx (Should Work)

```bash
# Make request through Nginx
curl http://api.example.com/api/generate \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'

# Should return valid response (after guard scanning)
```

### Test 3: With X-Forwarded-For (For Testing)

```bash
# Simulate request from nginx with X-Forwarded-For header
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.10" \
  -d '{"model":"mistral","prompt":"test"}'

# If 192.168.1.10 is whitelisted, request proceeds
```

## Nginx Configuration Examples

### Basic Nginx Setup (Same Machine)

```nginx
upstream ollama_proxy {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name api.example.com;
    
    location /api/ {
        proxy_pass http://ollama_proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Nginx with Authentication

```nginx
upstream ollama_proxy {
    server 127.0.0.1:8080;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Basic auth (optional layer)
    auth_basic "Ollama API";
    auth_basic_user_file /etc/nginx/htpasswd;
    
    location /api/ {
        proxy_pass http://ollama_proxy;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Increase timeout for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### Nginx Load Balancer (Multiple Proxy Instances)

```nginx
upstream ollama_proxy {
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;  # Second proxy instance
    server 127.0.0.1:8082;  # Third proxy instance
}

server {
    listen 80;
    server_name api.example.com;
    
    location /api/ {
        proxy_pass http://ollama_proxy;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Round-robin by default, or:
        # least_conn;  # Use least connections
    }
}
```

### Nginx Rate Limiting

```nginx
upstream ollama_proxy {
    server 127.0.0.1:8080;
}

# Rate limit: 100 requests per minute per IP
limit_req_zone $binary_remote_addr zone=ollama_limit:10m rate=100r/m;

server {
    listen 80;
    server_name api.example.com;
    
    location /api/ {
        limit_req zone=ollama_limit burst=20 nodelay;
        
        proxy_pass http://ollama_proxy;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Monitoring

### Check Whitelist Status

```bash
# View current whitelist configuration
curl http://localhost:8080/config | jq '.nginx_whitelist'

# Response:
# {
#   "enabled": true,
#   "count": 2,
#   "whitelist": [
#     "127.0.0.1",
#     "192.168.1.10"
#   ]
# }
```

### Check Health with Whitelist Info

```bash
curl http://localhost:8080/health | jq '.whitelist'

# Response:
# {
#   "enabled": true,
#   "count": 2,
#   "whitelist": [
#     "127.0.0.1",
#     "192.168.1.10"
#   ]
# }
```

### View Proxy Logs

```bash
# Watch logs for access denied messages
./run_proxy.sh logs | grep "access_denied\|IP whitelist"

# Example output:
# 2024-10-17 10:30:45 - WARNING - Rejected request from non-whitelisted IP: 192.168.50.5 POST /api/generate
# 2024-10-17 10:30:46 - DEBUG - IP whitelist check passed for 127.0.0.1
```

## Advanced Configuration

### CIDR Notation (Network Ranges)

```yaml
# config.yaml
nginx_whitelist:
  # Single host
  - "192.168.1.10"
  
  # Entire subnet (/24 = 256 hosts)
  - "192.168.1.0/24"
  
  # Larger subnet (/16 = 65,536 hosts)
  - "10.0.0.0/16"
  
  # Small subnet (/30 = 4 hosts, useful for specific services)
  - "172.16.0.0/30"
```

### Disabling Whitelist (For Testing)

```yaml
# config.yaml - Empty whitelist allows all
nginx_whitelist: []
```

Or via environment:

```bash
# Empty whitelist disables IP filtering
export NGINX_WHITELIST=""
./run_proxy.sh start
```

## Security Best Practices

### 1. Restrict Proxy to Localhost

```bash
# Run proxy on localhost only (not 0.0.0.0)
export PROXY_HOST="127.0.0.1"
export PROXY_PORT="8080"
export NGINX_WHITELIST="127.0.0.1"
./run_proxy.sh start
```

**Nginx config:**
```nginx
upstream ollama_proxy {
    server 127.0.0.1:8080;  # Local connection only
}
```

### 2. Use Loopback + Remote Nginx

```bash
# Allow localhost (Docker/local) + remote nginx
export NGINX_WHITELIST="127.0.0.1,192.168.1.10"
./run_proxy.sh start
```

### 3. Use Firewall + Whitelist (Defense in Depth)

```bash
# Configure system firewall
sudo ufw allow from 192.168.1.10 to any port 8080  # Nginx server
sudo ufw deny from any to any port 8080             # Block all others

# Also enable proxy whitelist as second layer
export NGINX_WHITELIST="192.168.1.10"
./run_proxy.sh start
```

### 4. Use TLS Between Nginx and Proxy

```nginx
upstream ollama_proxy {
    server 127.0.0.1:8443;  # HTTPS
}

server {
    location /api/ {
        proxy_pass https://ollama_proxy;  # HTTPS
        
        # Trust self-signed cert if needed
        proxy_ssl_verify off;
    }
}
```

### 5. Use VPN/Private Network

For remote Nginx instances, use VPN or private network:

```bash
# Only allow from VPN subnet
export NGINX_WHITELIST="10.8.0.0/24"  # OpenVPN subnet
./run_proxy.sh start
```

## Troubleshooting

### Issue: Access Denied from Nginx

```bash
# 1. Check proxy logs
./run_proxy.sh logs | tail -20

# 2. Verify nginx IP is in whitelist
curl http://localhost:8080/config | jq '.nginx_whitelist'

# 3. Check nginx configuration
# Ensure X-Forwarded-For header is set:
# proxy_set_header X-Forwarded-For $remote_addr;

# 4. Test with X-Forwarded-For header
curl -X GET http://localhost:8080/health \
  -H "X-Forwarded-For: 192.168.1.10"
```

### Issue: Whitelist Not Working

```bash
# 1. Verify whitelist is enabled
curl http://localhost:8080/config | jq '.nginx_whitelist.enabled'

# 2. Check YAML syntax (if using config file)
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 3. Restart proxy after config changes
./run_proxy.sh restart

# 4. Verify environment variable
echo $NGINX_WHITELIST
```

### Issue: Cannot Test Locally

```bash
# To bypass whitelist for testing (NOT production)
export NGINX_WHITELIST=""
./run_proxy.sh start

# Or add 127.0.0.1 to whitelist
export NGINX_WHITELIST="127.0.0.1"
./run_proxy.sh start
```

## Docker Compose Setup

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

  proxy:
    build: .
    environment:
      - OLLAMA_URL=http://ollama:11434
      - PROXY_PORT=8080
      - NGINX_WHITELIST=172.18.0.2    # Nginx container IP
    ports:
      - "8080:8080"
    depends_on:
      - ollama
    networks:
      - ollama-net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - proxy
    networks:
      - ollama-net

volumes:
  ollama-data:

networks:
  ollama-net:
```

## API Reference

### Configuration Endpoints

**GET /config**
```bash
curl http://localhost:8080/config | jq '.nginx_whitelist'
```

Response:
```json
{
  "enabled": true,
  "count": 2,
  "whitelist": ["127.0.0.1", "192.168.1.10"]
}
```

**GET /health**
```bash
curl http://localhost:8080/health
```

Response includes:
```json
{
  "whitelist": {
    "enabled": true,
    "count": 2,
    "whitelist": ["127.0.0.1", "192.168.1.10"]
  }
}
```

## Summary

| Feature | Benefit |
|---------|---------|
| IP Whitelist | Only Nginx can access proxy |
| CIDR Support | Support for network ranges |
| X-Forwarded-For | Works with proxy headers |
| Multiple IPs | Support multiple Nginx servers |
| Logs | Track rejected requests |
| Easy Config | Environment variable or YAML |

## Next Steps

1. **Identify Nginx IP Address**
   ```bash
   # On nginx server
   hostname -I
   ```

2. **Configure Proxy with Whitelist**
   ```bash
   export NGINX_WHITELIST="<nginx-ip>"
   ./run_proxy.sh start
   ```

3. **Configure Nginx Reverse Proxy**
   - Set `proxy_set_header X-Forwarded-For`
   - Point to proxy URL

4. **Test Access**
   ```bash
   # Through nginx (should work)
   curl http://api.example.com/api/generate
   
   # Direct to proxy (should be rejected)
   curl http://localhost:8080/api/generate
   ```

5. **Monitor**
   ```bash
   ./run_proxy.sh logs | grep "whitelist\|access"
   ```

---

**Proxy is now restricted to Nginx-only access!** 🔒
