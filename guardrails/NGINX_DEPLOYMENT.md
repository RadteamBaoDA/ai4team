# Ollama Guard Proxy - Nginx Load Balancing & IP Filtering Deployment

## Architecture Overview

```
                    ┌─────────────────────┐
                    │   Internet Clients  │
                    │   (Various IPs)     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Nginx Reverse Proxy│
                    │  - Load Balancing   │
                    │  - IP Filtering     │
                    │  - SSL/TLS          │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
        ┌───────▼────────┬────▼────────┬────▼────────┐
        │  Guard Proxy 1 │ Guard Proxy 2│ Guard Proxy 3│
        │   :8080        │   :8081      │   :8082     │
        │  (4 workers)   │  (4 workers) │  (4 workers)│
        └───────┬────────┴────┬─────────┴────┬────────┘
                │              │              │
        ┌───────▼────────────┬─┴──────────────┘
        │    Ollama Cluster  │
        │   - Multi-node     │
        │   - Load Balanced  │
        └────────────────────┘
```

---

## Part 1: Nginx Configuration for Load Balancing

### Setup: Multiple Proxy Instances

First, run 3 instances of the Guard Proxy on different ports:

**Terminal 1: Proxy Instance 1**
```bash
./run_proxy.sh --port 8080 --workers 4 --log-level info
```

**Terminal 2: Proxy Instance 2**
```bash
./run_proxy.sh --port 8081 --workers 4 --log-level info
```

**Terminal 3: Proxy Instance 3**
```bash
./run_proxy.sh --port 8082 --workers 4 --log-level info
```

**Or use background processes:**
```bash
# Linux/macOS
./run_proxy.sh --port 8080 --workers 4 &
./run_proxy.sh --port 8081 --workers 4 &
./run_proxy.sh --port 8082 --workers 4 &
jobs

# Windows PowerShell
Start-Process powershell -ArgumentList "-NoExit", "./run_proxy.bat --port 8080 --workers 4"
Start-Process powershell -ArgumentList "-NoExit", "./run_proxy.bat --port 8081 --workers 4"
Start-Process powershell -ArgumentList "-NoExit", "./run_proxy.bat --port 8082 --workers 4"
```

---

## Part 2: Nginx Installation

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install nginx -y
```

### macOS
```bash
brew install nginx
```

### Windows
Download and install from [nginx.org](https://nginx.org/en/download.html) or use WSL Ubuntu.

---

## Part 3: Nginx Configuration Files

### Basic Load Balancing (No IP Filtering)

Create `/etc/nginx/sites-available/ollama-guard` (Linux) or `nginx/conf.d/ollama-guard.conf`:

```nginx
# Upstream cluster of Guard Proxy instances
upstream ollama_guard_cluster {
    least_conn;  # Use least connections load balancing
    server 127.0.0.1:8080 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8081 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8082 weight=1 max_fails=3 fail_timeout=30s;
}

# Server block listening on port 80
server {
    listen 80;
    listen [::]:80;
    server_name localhost;

    # Logging
    access_log /var/log/nginx/ollama_guard_access.log;
    error_log /var/log/nginx/ollama_guard_error.log;

    # Proxy settings
    client_max_body_size 50M;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Load balanced proxy
    location / {
        proxy_pass http://ollama_guard_cluster;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "upgrade";
        proxy_set_header Upgrade $http_upgrade;
        
        # Streaming support
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Health check
        access_log off;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://ollama_guard_cluster;
        access_log off;
    }
}
```

---

## Part 4: Nginx with IP Filtering

### Allow Specific IPs Only

```nginx
upstream ollama_guard_cluster {
    least_conn;
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}

# Define allowed IPs
geo $ip_allowed {
    default 0;
    192.168.1.0/24 1;      # Office network
    10.0.0.0/8 1;          # VPN network
    203.0.113.50 1;         # Specific IP (example)
}

# Define denied IPs (blacklist)
geo $ip_denied {
    default 0;
    192.168.1.100 1;        # Blocked IP
    203.0.113.51 1;         # Blocked IP
}

server {
    listen 80;
    server_name localhost;

    access_log /var/log/nginx/ollama_guard_access.log;
    error_log /var/log/nginx/ollama_guard_error.log;

    # IP Access Control
    if ($ip_denied) {
        return 403;  # Forbidden
    }

    if ($ip_allowed = 0) {
        return 403;  # Forbidden - IP not in whitelist
    }

    # Proxy configuration
    location / {
        proxy_pass http://ollama_guard_cluster;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /health {
        proxy_pass http://ollama_guard_cluster;
        access_log off;
    }
}
```

---

## Part 5: Advanced Nginx Configuration

### With Rate Limiting & IP Filtering

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=addr:10m;

# IP filtering
geo $ip_allowed {
    default 0;
    192.168.1.0/24 1;
    10.0.0.0/8 1;
}

geo $ip_denied {
    default 0;
    192.168.1.100 1;
}

upstream ollama_guard_cluster {
    least_conn;
    server 127.0.0.1:8080 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8081 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8082 weight=1 max_fails=3 fail_timeout=30s;
    
    keepalive 32;
}

server {
    listen 80;
    server_name ollama.example.com;

    access_log /var/log/nginx/ollama_guard_access.log combined;
    error_log /var/log/nginx/ollama_guard_error.log;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Client settings
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Proxy timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # IP Access Control
    if ($ip_denied = 1) {
        return 403;
    }

    if ($ip_allowed = 0) {
        # Allow local for health checks
        set $allow_access 0;
        if ($remote_addr ~* "127.0.0.1|::1") {
            set $allow_access 1;
        }
        if ($ip_allowed = 1) {
            set $allow_access 1;
        }
        if ($allow_access = 0) {
            return 403;
        }
    }

    # Main API endpoint
    location /v1/ {
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn addr 10;

        proxy_pass http://ollama_guard_cluster;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # Streaming
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Keepalive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # Health check (no rate limiting)
    location /health {
        access_log off;
        proxy_pass http://ollama_guard_cluster;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Config endpoint (restricted)
    location /config {
        limit_req zone=api_limit burst=5 nodelay;
        proxy_pass http://ollama_guard_cluster;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Part 6: HTTPS/SSL Configuration

### Generate Self-Signed Certificate

```bash
# Generate private key and certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/ollama-guard.key \
  -out /etc/nginx/ssl/ollama-guard.crt \
  -subj "/C=US/ST=State/L=City/O=Company/CN=ollama.local"

# Create SSL directory if not exists
sudo mkdir -p /etc/nginx/ssl
```

### HTTPS Configuration

```nginx
upstream ollama_guard_cluster {
    least_conn;
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name ollama.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ollama.example.com;

    # SSL certificates
    ssl_certificate /etc/nginx/ssl/ollama-guard.crt;
    ssl_certificate_key /etc/nginx/ssl/ollama-guard.key;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;

    # Logging
    access_log /var/log/nginx/ollama_guard_access.log;
    error_log /var/log/nginx/ollama_guard_error.log;

    # Client settings
    client_max_body_size 50M;

    # Proxy configuration
    location / {
        proxy_pass http://ollama_guard_cluster;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

---

## Part 7: Enable Nginx Configuration

### Linux/macOS

```bash
# Enable site (Ubuntu/Debian)
sudo ln -s /etc/nginx/sites-available/ollama-guard /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Verify status
sudo systemctl status nginx

# Restart after changes
sudo systemctl restart nginx
```

### macOS (Homebrew)

```bash
# Copy config to Homebrew Nginx location
cp nginx-ollama.conf $(brew --prefix nginx)/etc/nginx/servers/

# Test configuration
nginx -t

# Start Nginx
brew services start nginx
brew services restart nginx
```

### Windows

```cmd
# Navigate to Nginx directory
cd "C:\nginx"

# Test configuration
nginx -t

# Start Nginx
nginx

# View Nginx processes
tasklist | findstr nginx

# Stop Nginx
taskkill /IM nginx.exe /F
```

---

## Part 8: Deployment Configuration Files

Create `nginx-ollama.conf`:

```nginx
# Ollama Guard Proxy - Nginx Configuration
# Features:
#  - Load balancing across 3 proxy instances
#  - IP whitelisting/blacklisting
#  - Rate limiting
#  - SSL/TLS support
#  - Streaming support

# Upstream cluster
upstream ollama_guard_cluster {
    least_conn;
    server 127.0.0.1:8080 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8081 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8082 weight=1 max_fails=3 fail_timeout=30s;
}

# IP Access Control Lists
geo $ip_allowed {
    default 0;
    # Add your trusted networks here
    # 192.168.1.0/24 1;
    # 10.0.0.0/8 1;
    # 203.0.113.0/24 1;
}

geo $ip_denied {
    default 0;
    # Add blocked IPs here
    # 192.168.1.100 1;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=addr:10m;

# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    location / {
        return 301 https://$host$request_uri;
    }
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;

    # SSL Configuration (update paths as needed)
    ssl_certificate /etc/nginx/ssl/ollama-guard.crt;
    ssl_certificate_key /etc/nginx/ssl/ollama-guard.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "no-referrer";

    # Logging
    access_log /var/log/nginx/ollama_guard_access.log combined buffer=32k flush=5s;
    error_log /var/log/nginx/ollama_guard_error.log warn;

    # Client settings
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Proxy timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # IP Access Control
    if ($ip_denied = 1) {
        return 403;
    }

    # Check whitelist (if configured)
    # if ($ip_allowed = 0) { return 403; }

    # Main API endpoints
    location /v1/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn addr 10;

        proxy_pass http://ollama_guard_cluster;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # Streaming support
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        access_log off;
        limit_req zone=api_limit burst=30 nodelay;
        
        proxy_pass http://ollama_guard_cluster;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Configuration endpoint
    location /config {
        limit_req zone=api_limit burst=5 nodelay;
        
        proxy_pass http://ollama_guard_cluster;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Part 9: Testing Deployment

### Test 1: Basic Connectivity

```bash
# Through Nginx
curl http://localhost/health

# Specific backend
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

### Test 2: Load Balancing Distribution

```bash
# Run multiple requests and monitor logs
for i in {1..10}; do
  curl -s http://localhost/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"test"}' &
done
wait

# Check logs for distribution
sudo tail -f /var/log/nginx/ollama_guard_access.log
```

### Test 3: IP Filtering

```bash
# From allowed IP
curl http://localhost/v1/generate -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'

# Simulate blocked IP (using X-Forwarded-For)
curl http://localhost/v1/generate \
  -H "X-Forwarded-For: 192.168.1.100" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'
```

### Test 4: Rate Limiting

```bash
# Send 30 requests rapidly (limit is 10r/s)
for i in {1..30}; do
  curl -s http://localhost/health &
done
wait

# Should see 429 (Too Many Requests) for some
```

### Test 5: Monitor Load Distribution

```bash
# Terminal 1: Monitor proxy logs
tail -f /var/log/ollama*.log | grep -E "Request|Response"

# Terminal 2: Send requests
for i in {1..100}; do
  curl -s http://localhost/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"What is AI?","stream":false}' &
done
wait
```

---

## Part 10: Monitoring & Troubleshooting

### Nginx Status & Logs

```bash
# Check Nginx status
sudo systemctl status nginx

# View access logs
sudo tail -f /var/log/nginx/ollama_guard_access.log

# View error logs
sudo tail -f /var/log/nginx/ollama_guard_error.log

# Count requests per backend
sudo awk '{print $7}' /var/log/nginx/ollama_guard_access.log | sort | uniq -c

# Check upstream health
sudo nginx -s reload  # No downtime reload
```

### Monitor Backend Instances

```bash
# Check all backends are running
ps aux | grep "run_proxy"

# Monitor backend process memory
watch -n 1 'ps aux | grep "python.*ollama_guard"'

# Health check all backends
for port in 8080 8081 8082; do
  echo "Port $port:"
  curl -s http://localhost:$port/health | jq
done
```

### Nginx Configuration Issues

```bash
# Test configuration syntax
sudo nginx -t

# Detailed configuration check
sudo nginx -T

# Reload configuration safely
sudo nginx -s reload

# View current worker processes
ps aux | grep nginx
```

---

## Part 11: Production Checklist

- [ ] **Load Balancing**
  - [ ] 3+ proxy instances running
  - [ ] Nginx upstream configured
  - [ ] Health checks working
  - [ ] Round-robin load balancing verified

- [ ] **IP Filtering**
  - [ ] Whitelist configured (if needed)
  - [ ] Blacklist configured
  - [ ] Test denied IPs return 403
  - [ ] Test allowed IPs work normally

- [ ] **SSL/TLS**
  - [ ] Certificate installed
  - [ ] HTTPS working
  - [ ] HTTP redirects to HTTPS
  - [ ] Security headers present

- [ ] **Rate Limiting**
  - [ ] Rate limits configured
  - [ ] Test 429 responses above limits
  - [ ] Adjust rates for production load

- [ ] **Logging**
  - [ ] Access logs enabled
  - [ ] Error logs monitored
  - [ ] Log rotation configured

- [ ] **Monitoring**
  - [ ] Health checks working
  - [ ] Backend status monitored
  - [ ] Performance baseline established

- [ ] **Performance**
  - [ ] Load test completed
  - [ ] Response times acceptable
  - [ ] No bottlenecks identified

---

## Part 12: Performance Tuning

### Nginx Optimization

```nginx
# Add to main nginx.conf [http] section
worker_processes auto;
worker_connections 4096;

# Connection pooling
upstream ollama_guard_cluster {
    keepalive 32;
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}

# Proxy settings
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;

location /v1/ {
    # Enable caching for non-streaming responses
    proxy_cache api_cache;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    proxy_cache_valid 200 1m;
    proxy_cache_bypass $http_pragma $http_authorization;
    
    proxy_pass http://ollama_guard_cluster;
}
```

### Recommended Production Settings

- **Worker Processes**: `auto` (matches CPU cores)
- **Worker Connections**: 4096 (increase for high load)
- **Keepalive**: 32 (connections per upstream)
- **Buffer Size**: 16k to 32k
- **Gzip**: Enable for text responses

---

## Quick Deploy Script

Create `deploy.sh`:

```bash
#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Ollama Guard Proxy Nginx Deployment ===${NC}\n"

# Check prerequisites
echo "Checking prerequisites..."
command -v nginx &> /dev/null || { echo -e "${RED}Nginx not installed${NC}"; exit 1; }
command -v python3 &> /dev/null || { echo -e "${RED}Python3 not installed${NC}"; exit 1; }

# Create SSL directory
echo "Setting up SSL..."
mkdir -p /etc/nginx/ssl

# Start proxy instances
echo -e "\n${YELLOW}Starting Guard Proxy instances...${NC}"
./run_proxy.sh --port 8080 --workers 4 &
PID1=$!
sleep 2

./run_proxy.sh --port 8081 --workers 4 &
PID2=$!
sleep 2

./run_proxy.sh --port 8082 --workers 4 &
PID3=$!
sleep 2

echo -e "${GREEN}✓ Proxy 1: PID $PID1${NC}"
echo -e "${GREEN}✓ Proxy 2: PID $PID2${NC}"
echo -e "${GREEN}✓ Proxy 3: PID $PID3${NC}"

# Test proxy connectivity
echo -e "\n${YELLOW}Testing proxy instances...${NC}"
for port in 8080 8081 8082; do
  if curl -s http://localhost:$port/health > /dev/null; then
    echo -e "${GREEN}✓ Port $port: OK${NC}"
  else
    echo -e "${RED}✗ Port $port: FAILED${NC}"
    exit 1
  fi
done

# Configure Nginx
echo -e "\n${YELLOW}Configuring Nginx...${NC}"
cp nginx-ollama.conf /etc/nginx/sites-available/ 2>/dev/null || \
  cp nginx-ollama.conf /etc/nginx/conf.d/

# Test Nginx configuration
if nginx -t 2>&1 | grep -q "successful"; then
  echo -e "${GREEN}✓ Nginx configuration valid${NC}"
else
  echo -e "${RED}✗ Nginx configuration invalid${NC}"
  exit 1
fi

# Start Nginx
echo -e "\n${YELLOW}Starting Nginx...${NC}"
sudo systemctl restart nginx || nginx

# Test final endpoint
sleep 2
if curl -s http://localhost/health > /dev/null; then
  echo -e "${GREEN}✓ Nginx load balancer: OK${NC}"
else
  echo -e "${RED}✗ Nginx load balancer: FAILED${NC}"
  exit 1
fi

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "Guard Proxy:   http://localhost:8080/health"
echo -e "Load Balancer: http://localhost/health"
echo -e "Logs:          sudo tail -f /var/log/nginx/ollama_guard_access.log"
```

Make executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Reference

### Nginx Commands

```bash
# Check version
nginx -v

# Test configuration
nginx -t

# Reload without downtime
nginx -s reload

# Stop gracefully
nginx -s quit

# Quick stop
nginx -s stop

# View process tree
ps aux | grep nginx
```

### Common Ports

- 80: HTTP
- 443: HTTPS
- 8080: Guard Proxy 1
- 8081: Guard Proxy 2
- 8082: Guard Proxy 3

---

Last Updated: October 16, 2025
