# Ollama Guard Proxy with Nginx - Complete Deployment Guide

## 📑 Document Overview

This guide provides everything needed to deploy the Ollama Guard Proxy with Nginx load balancing and IP filtering.

**Key Documents**:
- `NGINX_DEPLOYMENT.md` - Comprehensive 12-part deployment guide
- `NGINX_QUICKREF.md` - Quick reference and common tasks
- `nginx-ollama-production.conf` - Production-ready Nginx configuration
- `deploy-nginx.sh` - Automated deployment script (Linux/macOS)
- `deploy-nginx.bat` - Automated deployment script (Windows)

---

## 🎯 Solution Overview

### What This Solves

You requested: **"Can deploy guard proxy with nginx to handle load balancing and IP filter"**

This solution provides:

1. **Load Balancing**
   - Nginx reverse proxy distributing requests across 3 Guard Proxy instances
   - Least connections algorithm for optimal distribution
   - Automatic failover if a backend fails
   - Health checks monitoring backend status

2. **IP Filtering**
   - Whitelist specific IPs/networks (allow only these)
   - Blacklist specific IPs/networks (deny these)
   - CIDR notation support (192.168.1.0/24)
   - Per-IP rate limiting

3. **High Availability**
   - 3 parallel proxy instances (ports 8080, 8081, 8082)
   - Each with 4+ worker processes
   - Multi-level concurrency support

4. **Security**
   - SSL/TLS encryption
   - Security headers
   - Rate limiting (10 req/sec default)
   - Input/output guard scanning

---

## 🏗️ Architecture

### Deployment Topology

```
┌─────────────────────────────────────────────┐
│         Internet / Client Requests          │
└──────────────────┬──────────────────────────┘
                   │ (Port 80/443)
                   ▼
        ┌─────────────────────────┐
        │  Nginx Load Balancer    │
        │  - IP Filtering         │
        │  - Rate Limiting        │
        │  - SSL/TLS              │
        │  - Health Checks        │
        └──────────┬──────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐
    │ Proxy1 │ │ Proxy2 │ │ Proxy3 │
    │ :8080  │ │ :8081  │ │ :8082  │
    │4 Work  │ │4 Work  │ │4 Work  │
    └────────┘ └────────┘ └────────┘
        │          │          │
        └──────────┼──────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Ollama LLM Backend    │
        │ (Remote or Local)     │
        └──────────────────────┘
```

### Data Flow

```
1. Client connects to Nginx (80/443)
2. Nginx checks IP against whitelist/blacklist
3. If allowed, Nginx checks rate limits
4. Request forwarded to least-loaded backend
5. Proxy instance receives request
6. Input scanning (LLM Guard)
7. Forward to Ollama
8. Ollama processes request
9. Output scanning (LLM Guard)
10. Response returned through Nginx
11. Response sent to client
```

### Component Breakdown

| Component | Purpose | Quantity | Resources |
|-----------|---------|----------|-----------|
| Nginx | Load balancing, IP filtering, SSL | 1 | ~50MB |
| Guard Proxy | Request/response scanning | 3 | ~200MB each |
| Ollama | LLM inference | 1+ | Variable |
| Python Workers | Request handlers | 12+ | Shared |

---

## 📦 Installation & Setup

### Prerequisites

#### Linux/macOS
```bash
# Python 3.9+
python3 --version

# Required packages
pip install fastapi uvicorn requests pydantic pyyaml llm-guard

# Nginx
# Ubuntu/Debian
sudo apt-get install nginx

# macOS
brew install nginx
```

#### Windows
```batch
# Python 3.9+ (from python.org or Microsoft Store)
python --version

# Nginx - download from nginx.org or use WSL Ubuntu
# Or use Windows package managers:
choco install nginx       # via Chocolatey
winget install nginx      # via Windows Package Manager
```

### Quick Setup (5 minutes)

**Linux/macOS:**
```bash
cd /path/to/guardrails
chmod +x deploy-nginx.sh
sudo ./deploy-nginx.sh start
```

**Windows (PowerShell as Admin):**
```powershell
cd C:\path\to\guardrails
.\deploy-nginx.bat start
```

This will:
1. ✅ Start 3 Guard Proxy instances
2. ✅ Configure Nginx
3. ✅ Start Nginx load balancer
4. ✅ Run health checks
5. ✅ Display status and endpoints

---

## 🔧 Configuration

### Basic IP Filtering

Edit `nginx-ollama-production.conf`:

**Allow Only Specific IPs (Whitelist):**
```nginx
geo $ip_allowed {
    default 0;
    127.0.0.1 1;           # Localhost
    192.168.1.0/24 1;      # Office network
    10.0.0.0/8 1;          # VPN network
}

# Then uncomment in server block:
if ($ip_allowed = 0) {
    return 403;  # Deny all not in list
}
```

**Block Specific IPs (Blacklist):**
```nginx
geo $ip_denied {
    default 0;
    192.168.1.100 1;       # Blocked IP
    203.0.113.51 1;        # Another blocked IP
}

# In server block:
if ($ip_denied = 1) {
    return 403;
}
```

### Rate Limiting

Default: 10 requests/second per IP

**Increase for high traffic:**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;
```

**Adjust burst:**
```nginx
location /v1/ {
    limit_req zone=api_limit burst=50 nodelay;  # Was 20
}
```

### Proxy Workers

Increase parallelism for high load:

**Current (Default):**
```bash
./deploy-nginx.sh start
# Starts 3 proxies × 4 workers = 12 workers
# 12 × 128 concurrency = 1,536 concurrent connections
```

**High Performance:**
```bash
# Edit deploy-nginx.sh and change workers from 4 to 8
# or manually run:
./run_proxy.sh --port 8080 --workers 8 --concurrency 256
./run_proxy.sh --port 8081 --workers 8 --concurrency 256
./run_proxy.sh --port 8082 --workers 8 --concurrency 256
```

---

## 🚀 Deployment

### Automated Deployment

**Linux/macOS:**
```bash
# Full setup
sudo ./deploy-nginx.sh start

# Stop everything
sudo ./deploy-nginx.sh stop

# Restart after changes
sudo ./deploy-nginx.sh restart

# Check status
sudo ./deploy-nginx.sh status

# Run diagnostics
sudo ./deploy-nginx.sh test
```

**Windows:**
```batch
# Run as Administrator
.\deploy-nginx.bat start
.\deploy-nginx.bat stop
.\deploy-nginx.bat restart
.\deploy-nginx.bat status
.\deploy-nginx.bat test
```

### Manual Deployment

**Step 1: Start Proxy Instances**
```bash
# Terminal 1
./run_proxy.sh --port 8080 --workers 4

# Terminal 2
./run_proxy.sh --port 8081 --workers 4

# Terminal 3
./run_proxy.sh --port 8082 --workers 4
```

**Step 2: Test Proxies**
```bash
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

**Step 3: Configure Nginx**
```bash
# Copy configuration
sudo cp nginx-ollama-production.conf /etc/nginx/sites-available/ollama-guard

# Enable site
sudo ln -sf /etc/nginx/sites-available/ollama-guard \
             /etc/nginx/sites-enabled/ollama-guard

# Or for macOS:
cp nginx-ollama-production.conf /usr/local/etc/nginx/servers/
```

**Step 4: Test & Start Nginx**
```bash
# Validate configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx

# Or macOS:
brew services start nginx
```

**Step 5: Verify**
```bash
# Health check through load balancer
curl http://localhost/health

# Load test
for i in {1..10}; do
  curl -s http://localhost/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"test","stream":false}' &
done
wait
```

---

## 📊 Testing & Validation

### Health Checks

```bash
# Individual proxies
curl http://localhost:8080/health | jq
curl http://localhost:8081/health | jq
curl http://localhost:8082/health | jq

# Through load balancer
curl http://localhost/health | jq
```

### Load Distribution Test

```bash
# Monitor real-time request distribution
sudo tail -f /var/log/nginx/ollama_guard_access.log | \
  awk '{print $7}' | sort | uniq -c

# In another terminal, send requests
for i in {1..30}; do
  curl -s http://localhost/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"test","stream":false}' &
done
wait
```

### IP Filtering Test

```bash
# Test allowed IPs (localhost)
curl http://localhost/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test","stream":false}'

# Test blocked IP (if configured)
curl http://localhost/v1/generate \
  -H "X-Forwarded-For: 192.168.1.100" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test","stream":false}'
# Should return 403
```

### Rate Limiting Test

```bash
# Send 50 requests rapidly (limit: 10r/s)
for i in {1..50}; do
  (curl -s http://localhost/health -w "%{http_code}\n" -o /dev/null) &
done
wait | sort | uniq -c

# Should see:
# - 200 OK for ~10 requests
# - 429 Too Many Requests for the rest
```

---

## 🔍 Monitoring

### Check Service Status

```bash
# Nginx
sudo systemctl status nginx

# Proxy processes
ps aux | grep "run_proxy\|ollama_guard"

# All running processes
pgrep -a "nginx\|python.*ollama"
```

### View Logs

```bash
# Access logs (real-time)
sudo tail -f /var/log/nginx/ollama_guard_access.log

# Error logs
sudo tail -f /var/log/nginx/ollama_guard_error.log

# Proxy logs
tail -f /var/log/ollama-guard/proxy-8080.log
tail -f /var/log/ollama-guard/proxy-8081.log
tail -f /var/log/ollama-guard/proxy-8082.log

# Filter for errors
sudo tail -f /var/log/nginx/ollama_guard_access.log | grep "429\|403\|500"
```

### Performance Monitoring

```bash
# Memory usage
watch -n 1 'free -h && echo "---" && ps aux | grep python | grep ollama_guard'

# CPU usage
top -p $(pgrep -d, "nginx\|python.*ollama")

# Network connections
netstat -an | grep ESTABLISHED | wc -l

# Per-IP request count
sudo awk '{print $1}' /var/log/nginx/ollama_guard_access.log | sort | uniq -c | sort -rn
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
lsof -i :8080
lsof -i :80

# Kill the process
kill -9 <PID>

# Or use different port
./run_proxy.sh --port 9000
```

### Nginx Won't Start

```bash
# Check configuration
sudo nginx -t

# Check if ports are available
sudo lsof -i :80
sudo lsof -i :443

# Check error log
sudo tail -20 /var/log/nginx/error.log

# Try manual start with verbose
sudo nginx -g 'daemon off;'
```

### Proxies Slow or Unresponsive

```bash
# Check load
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health

# Check memory
free -h

# Check if Ollama is responding
curl http://<ollama-ip>:11434/api/tags

# Restart proxies
./deploy-nginx.sh restart
```

### High Error Rate (429/503)

```bash
# 429 = Rate limited (expected under high load)
# 503 = Backend unavailable

# Check backends
curl -i http://localhost:8080/health
curl -i http://localhost:8081/health
curl -i http://localhost:8082/health

# Check Nginx config
sudo nginx -t

# Review logs
sudo tail -100 /var/log/nginx/ollama_guard_error.log

# Increase concurrency if needed
# Edit run_proxy.sh or manually restart with higher concurrency
```

---

## 📈 Performance Tuning

### For Light Load (< 100 req/min)
```bash
# Default configuration is sufficient
./deploy-nginx.sh start
```

### For Medium Load (100-1000 req/min)
```bash
# Increase workers
./run_proxy.sh --port 8080 --workers 6 --concurrency 128
./run_proxy.sh --port 8081 --workers 6 --concurrency 128
./run_proxy.sh --port 8082 --workers 6 --concurrency 128

# Increase rate limits
# Edit nginx config: rate=20r/s
```

### For High Load (> 1000 req/min)
```bash
# Maximum workers and concurrency
./run_proxy.sh --port 8080 --workers 8 --concurrency 256
./run_proxy.sh --port 8081 --workers 8 --concurrency 256
./run_proxy.sh --port 8082 --workers 8 --concurrency 256

# Add more proxy instances
./run_proxy.sh --port 8083 --workers 8
./run_proxy.sh --port 8084 --workers 8

# Update Nginx upstream:
# server 127.0.0.1:8083;
# server 127.0.0.1:8084;

# Disable rate limiting or increase significantly
# rate=50r/s
```

### Memory Optimization

Each component uses:
- Nginx: ~50MB
- Proxy worker: ~150-200MB (with guards loaded)
- Python base: ~30MB

**Total for default setup**: ~3 × 200MB + 50MB = ~650MB

**For limited memory**:
```bash
# Reduce workers
./run_proxy.sh --port 8080 --workers 2 --concurrency 64
```

---

## 🔐 Security Best Practices

### 1. Use Real SSL Certificates

Replace self-signed with:
```bash
# Let's Encrypt (free)
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d ollama.example.com

# Update nginx config
ssl_certificate /etc/letsencrypt/live/ollama.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ollama.example.com/privkey.pem;
```

### 2. Restrict IP Access

Configure strict whitelist:
```nginx
geo $ip_allowed {
    default 0;
    # Only your IPs
    203.0.113.50 1;       # Your IP
    192.168.1.0/24 1;     # Your network
}

if ($ip_allowed = 0) {
    return 403;
}
```

### 3. Enable All Guards

In proxy config:
```yaml
enable_input_guard: true      # Block malicious prompts
enable_output_guard: true     # Block malicious responses
block_on_guard_error: false   # Don't block on errors
```

### 4. Monitor Logs

```bash
# Alert on errors
sudo tail -f /var/log/nginx/ollama_guard_error.log | \
  while read line; do
    [[ "$line" =~ error ]] && echo "ALERT: $line" | mail -s "Proxy Error" admin@example.com
  done
```

### 5. Rate Limiting

Prevent abuse:
```nginx
# Aggressive for API endpoints
limit_req zone=api_limit burst=10 nodelay;

# Less aggressive for health checks
location /health {
    limit_req zone=health_limit burst=50 nodelay;
}
```

---

## 📋 Maintenance

### Regular Tasks

**Daily**:
- [ ] Monitor error logs: `tail -f /var/log/nginx/ollama_guard_error.log`
- [ ] Check health: `curl http://localhost/health`

**Weekly**:
- [ ] Review access logs for patterns: `tail -1000 /var/log/nginx/ollama_guard_access.log | awk '{print $1}' | sort | uniq -c`
- [ ] Check disk space: `df -h /var/log`
- [ ] Verify SSL cert expiry: `openssl x509 -in /etc/nginx/ssl/ollama-guard.crt -noout -dates`

**Monthly**:
- [ ] Rotate logs: `sudo logrotate -f /etc/logrotate.d/nginx`
- [ ] Review and optimize config
- [ ] Security update: `sudo apt update && sudo apt upgrade`

### Backup Configuration

```bash
# Backup before major changes
sudo cp -r /etc/nginx /etc/nginx.backup-$(date +%Y%m%d)

# Restore if needed
sudo rm -rf /etc/nginx
sudo cp -r /etc/nginx.backup-20251016 /etc/nginx
sudo systemctl restart nginx
```

---

## ✅ Post-Deployment Checklist

- [ ] All 3 proxy instances running
- [ ] Nginx load balancer running
- [ ] Health check endpoint responding
- [ ] SSL/TLS working
- [ ] IP filtering configured and tested
- [ ] Rate limiting active
- [ ] Logging enabled
- [ ] Ollama backend verified
- [ ] Load testing completed
- [ ] Performance baseline established
- [ ] Monitoring alerts configured
- [ ] Backup procedure documented

---

## 📚 Additional Resources

- `NGINX_DEPLOYMENT.md` - Detailed deployment guide
- `NGINX_QUICKREF.md` - Quick reference guide
- `UVICORN_GUIDE.md` - Proxy worker configuration
- `USAGE.md` - API usage guide
- `TROUBLESHOOTING.md` - Common issues and solutions

---

## 🎓 Key Concepts

### Load Balancing
Distributes incoming requests across multiple backend servers to:
- Increase throughput
- Improve reliability
- Enable horizontal scaling

### IP Filtering
Controls access based on client IP address:
- **Whitelist**: Only allow specific IPs
- **Blacklist**: Deny specific IPs
- **CIDR notation**: Support for networks (192.168.1.0/24)

### Rate Limiting
Restricts request frequency to:
- Prevent abuse
- Protect backend
- Ensure fair resource allocation

### Health Checks
Monitors backend status to:
- Detect failures
- Route around dead backends
- Trigger failover

---

## 🤝 Support

For issues:
1. Check `TROUBLESHOOTING.md`
2. Review logs (see Monitoring section)
3. Run diagnostic tests: `./deploy-nginx.sh test`
4. Verify prerequisites are met

---

**Version**: 1.0  
**Last Updated**: October 16, 2025  
**Status**: Production Ready
