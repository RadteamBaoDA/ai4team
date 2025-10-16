# Nginx + Ollama Guard Proxy - Quick Reference

## 🚀 Quick Start (5 minutes)

### Linux/macOS

```bash
# Make script executable
chmod +x deploy-nginx.sh

# Start everything (proxies + nginx)
sudo ./deploy-nginx.sh start

# Check status
sudo ./deploy-nginx.sh status

# Test endpoints
curl http://localhost/health
```

### Windows

```batch
# Admin PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Start deployment
.\deploy-nginx.bat start

# Check status
.\deploy-nginx.bat status

# Test endpoints
curl http://localhost/health
```

---

## 📋 Architecture at a Glance

```
Internet → Nginx (Load Balancer + IP Filter)
         ↓
    ┌────┼────┐
    ↓    ↓    ↓
  8080 8081 8082  (3 Proxy Instances with Guards)
    ↓    ↓    ↓
    └────┼────┘
         ↓
      Ollama
```

---

## 🔧 Commands Reference

### Deployment Script

| Command | Purpose |
|---------|---------|
| `./deploy-nginx.sh start` | Start all services |
| `./deploy-nginx.sh stop` | Stop all services |
| `./deploy-nginx.sh restart` | Restart all services |
| `./deploy-nginx.sh status` | Show current status |
| `./deploy-nginx.sh test` | Run diagnostics |

### Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload (no downtime)
sudo nginx -s reload

# Stop
sudo nginx -s stop

# Start
sudo systemctl start nginx

# View logs
tail -f /var/log/nginx/ollama_guard_access.log
tail -f /var/log/nginx/ollama_guard_error.log
```

### Proxy Commands

```bash
# Start single instance
./run_proxy.sh --port 8080 --workers 4

# Start with custom config
./run_proxy.sh --port 8080 --workers 8 --config custom.yaml

# View logs
tail -f /var/log/ollama-guard/proxy-8080.log
```

---

## 🎯 Configuration Quick Tips

### Enable IP Whitelist

Edit `nginx-ollama-production.conf`:

```nginx
# Uncomment this section to enable whitelist
# if ($ip_allowed = 0) {
#     return 403;
# }
```

Then update the `geo` block:

```nginx
geo $ip_allowed {
    default 0;
    127.0.0.1 1;      # Localhost
    ::1 1;             # IPv6 localhost
    192.168.1.0/24 1;  # Office network
    10.0.0.0/8 1;      # VPN
}
```

### Add Blocked IPs

```nginx
geo $ip_denied {
    default 0;
    192.168.1.100 1;   # Blocked IP
}
```

### Adjust Rate Limits

```nginx
# Current: 10 requests/second per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Change to 20 requests/second
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;
```

---

## 📊 Monitoring Commands

### Health Checks

```bash
# All backends
for port in 8080 8081 8082; do
  echo "Port $port:"
  curl -s http://localhost:$port/health | jq '.'
done

# Through load balancer
curl -s http://localhost/health | jq '.'
```

### View Request Distribution

```bash
# Count requests per backend (requires logging)
sudo tail -f /var/log/nginx/ollama_guard_access.log | \
  awk '{print $7}' | sort | uniq -c
```

### Performance Monitoring

```bash
# Watch proxy processes
watch -n 1 'ps aux | grep python | grep ollama_guard'

# Monitor memory usage
watch -n 1 'free -h'

# Check Nginx worker processes
ps aux | grep nginx
```

---

## 🧪 Testing Endpoints

### Basic Tests

```bash
# Health check
curl http://localhost/health

# Get configuration
curl http://localhost/config | jq '.'

# Generate request
curl -X POST http://localhost/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "prompt": "What is AI?",
    "stream": false
  }'
```

### Load Testing

```bash
# Simple load test (10 concurrent)
for i in {1..10}; do
  (curl -s http://localhost/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"test","stream":false}' \
    -o /dev/null) &
done
wait
echo "Done"
```

### Rate Limit Testing

```bash
# Send 50 requests rapidly (limit is 10r/s)
for i in {1..50}; do
  (curl -s http://localhost/health -o /dev/null -w "%{http_code}\n") &
done
wait | sort | uniq -c

# Should see 429 (Too Many Requests) for some
```

---

## 🔒 IP Filtering Test

### Simulate Different IPs

```bash
# Test with X-Forwarded-For header
curl http://localhost/v1/generate \
  -H "X-Forwarded-For: 192.168.1.100" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test","stream":false}'

# Should get 403 if IP is blacklisted
```

---

## 📝 Configuration Files

### Main Files

| File | Purpose |
|------|---------|
| `nginx-ollama-production.conf` | Nginx configuration with all features |
| `nginx-guard.conf` | Alternative (simpler) Nginx config |
| `config.example.yaml` | Proxy configuration template |
| `deploy-nginx.sh` | Linux/macOS deployment script |
| `deploy-nginx.bat` | Windows deployment script |

### Nginx Configuration Locations

- **Linux**: `/etc/nginx/sites-available/ollama-guard`
- **macOS**: `/usr/local/etc/nginx/servers/ollama-guard.conf`
- **Windows**: `C:\nginx\conf\servers\ollama-guard.conf`

---

## 🐛 Troubleshooting

### Proxy Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Check Python installation
python3 --version

# Check Uvicorn
python3 -c "import uvicorn; print(uvicorn.__version__)"
```

### Nginx Won't Start

```bash
# Test configuration
sudo nginx -t

# Check if port 80/443 is in use
lsof -i :80
lsof -i :443

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Slow Responses

```bash
# Check proxy CPU/memory
top | grep python

# Check network connectivity
ping <ollama-ip>

# Check load on each backend
curl http://localhost:8080/config | jq '.'
curl http://localhost:8081/config | jq '.'
curl http://localhost:8082/config | jq '.'
```

### High Error Rate

```bash
# Check error logs
sudo tail -100 /var/log/nginx/ollama_guard_error.log

# Check proxy logs
tail -100 /var/log/ollama-guard/proxy-*.log

# Verify backends are responding
curl -i http://localhost:8080/health
```

---

## 🔄 Common Workflows

### Restart After Config Changes

```bash
# Edit configuration
nano nginx-ollama-production.conf

# Test
sudo nginx -t

# Reload without downtime
sudo nginx -s reload

# Verify
curl http://localhost/health
```

### Add New Proxy Instance

```bash
# Edit deploy script to add port 8083
# Or manually run:
./run_proxy.sh --port 8083 --workers 4 &

# Add to nginx.conf upstream block:
# server 127.0.0.1:8083;

# Reload Nginx
sudo nginx -s reload
```

### Enable HTTPS with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d ollama.example.com

# Update nginx config paths:
# ssl_certificate /etc/letsencrypt/live/ollama.example.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/ollama.example.com/privkey.pem;

# Reload
sudo nginx -s reload
```

### Backup Configuration

```bash
# Backup Nginx config
cp nginx-ollama-production.conf nginx-ollama-production.conf.backup

# Backup proxy config
cp config.example.yaml config.example.yaml.backup

# Backup Nginx system config
sudo cp -r /etc/nginx /etc/nginx.backup
```

---

## 📈 Performance Tuning

### Increase Proxy Workers

```bash
# Each worker handles 128 concurrent connections
# For high load, use more workers:

./run_proxy.sh --port 8080 --workers 8 --concurrency 256
./run_proxy.sh --port 8081 --workers 8 --concurrency 256
./run_proxy.sh --port 8082 --workers 8 --concurrency 256
```

### Optimize Nginx

In nginx config:

```nginx
# Increase upstream connections
upstream ollama_guard_cluster {
    keepalive 64;  # Increase from 32
    ...
}

# Increase limits per IP
limit_conn addr 20;  # Increase from 10

# Increase burst
limit_req zone=api_limit burst=50 nodelay;  # Increase from 20
```

### Monitor Performance

```bash
# Baseline test (1 minute)
time for i in {1..100}; do
  curl -s http://localhost/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"test","stream":false}' &
done
wait
```

---

## 🔗 Key Ports

| Port | Service | Purpose |
|------|---------|---------|
| 80 | Nginx HTTP | Redirect to HTTPS |
| 443 | Nginx HTTPS | Main entry point |
| 8080 | Proxy 1 | Guard Proxy instance 1 |
| 8081 | Proxy 2 | Guard Proxy instance 2 |
| 8082 | Proxy 3 | Guard Proxy instance 3 |

---

## 📚 Log Locations

| Log | Path |
|-----|------|
| Nginx Access | `/var/log/nginx/ollama_guard_access.log` |
| Nginx Error | `/var/log/nginx/ollama_guard_error.log` |
| Proxy 1 | `/var/log/ollama-guard/proxy-8080.log` |
| Proxy 2 | `/var/log/ollama-guard/proxy-8081.log` |
| Proxy 3 | `/var/log/ollama-guard/proxy-8082.log` |

---

## ✅ Pre-Deployment Checklist

- [ ] All proxy instances running and healthy
- [ ] Nginx configuration syntax valid
- [ ] SSL certificates generated or configured
- [ ] IP filtering rules configured (if needed)
- [ ] Rate limiting configured
- [ ] Ollama backend accessible
- [ ] Proxy memory and CPU adequate
- [ ] Network ports available (80, 443, 8080-8082)
- [ ] Logging enabled
- [ ] Monitoring setup complete

---

**Last Updated**: October 16, 2025
