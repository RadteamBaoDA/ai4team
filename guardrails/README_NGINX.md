# Ollama Guard Proxy + Nginx Load Balancer

**Complete solution for deploying Ollama Guard Proxy with Nginx load balancing and IP filtering.**

---

## ⚡ Quick Start (5 minutes)

### Linux/macOS
```bash
cd guardrails
chmod +x deploy-nginx.sh
sudo ./deploy-nginx.sh start
```

### Windows (Admin PowerShell)
```batch
cd guardrails
.\deploy-nginx.bat start
```

### Verify
```bash
curl http://localhost/health
```

---

## 📚 Documentation

| Document | Read Time | Purpose |
|----------|-----------|---------|
| **START_NGINX.md** | 5 min | Visual overview (this file) |
| **NGINX_SETUP_COMPLETE.md** | 30 min | ⭐ Complete setup guide |
| **NGINX_QUICKREF.md** | 15 min | Quick reference & commands |
| **NGINX_DEPLOYMENT.md** | 60 min | Detailed 12-part guide |
| **NGINX_INDEX.md** | 10 min | Navigation & file index |

---

## 🎯 What This Provides

### Load Balancing
- Distributes requests across 3 proxy instances (8080, 8081, 8082)
- Least connections algorithm
- Automatic failover
- Health monitoring

### IP Filtering  
- Whitelist specific IPs (allow only these)
- Blacklist specific IPs (deny these)
- CIDR notation support (192.168.1.0/24)
- IPv6 ready

### Rate Limiting
- 10 requests/second per IP (configurable)
- Burst support
- Different limits for different endpoints
- 429 response on limit exceeded

### Security
- SSL/TLS encryption
- Security headers
- Input/output scanning
- Audit logging

---

## 📂 Key Files

```
guardrails/
├── deploy-nginx.sh                (Linux/macOS auto-deployment)
├── deploy-nginx.bat               (Windows auto-deployment)
├── nginx-ollama-production.conf   (Nginx configuration)
├── run_proxy.sh                   (Proxy runner - Linux/macOS)
├── run_proxy.bat                  (Proxy runner - Windows)
├── ollama_guard_proxy.py          (Main proxy app)
└── NGINX_*.md                     (Documentation)
```

---

## 🚀 Deployment

### Automated (Recommended)
```bash
sudo ./deploy-nginx.sh start    # Start all services
sudo ./deploy-nginx.sh status   # Check status
sudo ./deploy-nginx.sh stop     # Stop all services
```

### Manual
```bash
# 1. Start proxies
./run_proxy.sh --port 8080 --workers 4 &
./run_proxy.sh --port 8081 --workers 4 &
./run_proxy.sh --port 8082 --workers 4 &

# 2. Configure Nginx
sudo cp nginx-ollama-production.conf /etc/nginx/sites-available/ollama-guard
sudo ln -s /etc/nginx/sites-available/ollama-guard /etc/nginx/sites-enabled/

# 3. Start Nginx
sudo systemctl start nginx

# 4. Verify
curl http://localhost/health
```

---

## 🧪 Testing

### Health Check
```bash
curl http://localhost/health | jq
```

### Backend Status
```bash
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

### API Call
```bash
curl -X POST http://localhost/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello","stream":false}'
```

### Load Test
```bash
for i in {1..10}; do
  curl -s http://localhost/health &
done
wait
```

---

## 📊 Architecture

```
┌──────────────────────────┐
│  Internet Clients        │
└────────────┬─────────────┘
             │ (Port 80/443)
    ┌────────▼────────┐
    │  Nginx          │
    │  - Load Balance │
    │  - IP Filter    │
    │  - Rate Limit   │
    │  - SSL/TLS      │
    └────────┬────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
  Proxy1   Proxy2   Proxy3
  :8080    :8081    :8082
  4 Work   4 Work   4 Work
  128 Con  128 Con  128 Con
    │        │        │
    └────────┼────────┘
             │
    ┌────────▼────────┐
    │  Ollama Backend │
    └─────────────────┘
```

---

## 🔧 Configuration

### Enable IP Whitelist
Edit `nginx-ollama-production.conf`:
```nginx
geo $ip_allowed {
    default 0;
    192.168.1.0/24 1;   # Your office
    10.0.0.0/8 1;       # Your VPN
}

# In server block, uncomment:
if ($ip_allowed = 0) {
    return 403;
}
```

### Adjust Rate Limit
```nginx
# Change from 10r/s to 20r/s
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;
```

### Add More Proxies
```bash
./run_proxy.sh --port 8083 --workers 8 &

# Add to nginx.conf:
# server 127.0.0.1:8083;

sudo nginx -s reload
```

---

## 📈 Performance

### Default Setup
- Capacity: ~1,500 concurrent connections
- Throughput: Limited by Ollama backend
- Response time: 150-700ms (with guards)
- Deployment time: 5 minutes

### Scaling
| Load | Proxies | Workers | Config |
|------|---------|---------|--------|
| Light | 3 | 2 | dev |
| Medium | 3 | 4 | default |
| Heavy | 3-5 | 8 | production |

---

## 🔍 Monitoring

### Status
```bash
./deploy-nginx.sh status
```

### Logs (Real-time)
```bash
tail -f /var/log/nginx/ollama_guard_access.log
tail -f /var/log/nginx/ollama_guard_error.log
```

### Request Distribution
```bash
sudo tail -1000 /var/log/nginx/ollama_guard_access.log | \
  awk '{print $7}' | sort | uniq -c
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
lsof -i :80
lsof -i :8080
kill -9 <PID>
```

### Nginx Won't Start
```bash
sudo nginx -t          # Test config
tail -20 /var/log/nginx/error.log
```

### Proxies Not Responding
```bash
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

### High Error Rate
```bash
tail -100 /var/log/nginx/error.log
./deploy-nginx.sh test
```

See `TROUBLESHOOTING.md` for more issues.

---

## 🔐 Security

### Implemented
- ✅ SSL/TLS encryption
- ✅ IP access control
- ✅ Rate limiting
- ✅ Security headers
- ✅ Audit logging

### Best Practices
- Use Let's Encrypt for SSL
- Configure IP whitelist
- Monitor logs regularly
- Keep systems updated
- Regular audits

---

## 📋 Pre-deployment Checklist

- [ ] Prerequisites: Python 3.9+, Nginx, Uvicorn
- [ ] Ollama backend running and accessible
- [ ] Ports available: 80, 443, 8080, 8081, 8082
- [ ] Sufficient disk space for logs
- [ ] Network connectivity verified
- [ ] SSL certificates ready (or use self-signed)

---

## ✅ Post-deployment Checklist

- [ ] `./deploy-nginx.sh status` shows all running
- [ ] `curl http://localhost/health` returns 200
- [ ] Backend ports 8080/8081/8082 responding
- [ ] Health endpoint accessible through Nginx
- [ ] Logs being written to `/var/log/nginx/`
- [ ] IP filtering tested (if configured)
- [ ] Rate limiting tested
- [ ] Load test completed
- [ ] Monitoring setup done

---

## 🎯 Next Steps

1. **Immediate** (5 min)
   - Run: `sudo ./deploy-nginx.sh start`
   - Test: `curl http://localhost/health`

2. **Short-term** (30 min)
   - Read: `NGINX_SETUP_COMPLETE.md`
   - Configure IP filtering (if needed)
   - Run: `./deploy-nginx.sh test`

3. **Long-term**
   - Monitor logs regularly
   - Adjust workers for your load
   - Plan for scaling
   - Maintain security updates

---

## 📞 Support

### Documentation
- `NGINX_SETUP_COMPLETE.md` - Complete guide
- `NGINX_QUICKREF.md` - Quick reference
- `NGINX_DEPLOYMENT.md` - Detailed guide
- `TROUBLESHOOTING.md` - Problem solving

### Commands
```bash
./deploy-nginx.sh test       # Run diagnostics
./deploy-nginx.sh status     # Check status
./deploy-nginx.sh restart    # Restart all

curl http://localhost/health # Health check
tail -f /var/log/nginx/ollama_guard_access.log  # View logs
```

---

## 🎊 Summary

You have everything needed to:
- ✅ Deploy Ollama Guard Proxy with Nginx
- ✅ Load balance across multiple instances
- ✅ Filter requests by IP (whitelist/blacklist)
- ✅ Rate limit per IP
- ✅ Monitor and troubleshoot
- ✅ Scale horizontally

**Start now**: `sudo ./deploy-nginx.sh start`

---

**Version**: 1.0  
**Status**: Production Ready  
**Deployment Time**: 5 minutes  
**Support**: Full documentation included
