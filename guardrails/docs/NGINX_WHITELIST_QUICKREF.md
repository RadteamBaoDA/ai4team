# Nginx-Only Proxy Configuration - Quick Reference

## TL;DR - 30 Seconds Setup

```bash
# Find Nginx IP
nginx_ip="127.0.0.1"  # or your nginx server IP

# Start proxy with whitelist
export NGINX_WHITELIST="$nginx_ip"
./run_proxy.sh start

# Verify
curl http://localhost:8080/config | jq '.nginx_whitelist'
```

## Configuration Methods

### Method 1: Environment Variable (Simple)

```bash
# Single IP
export NGINX_WHITELIST="127.0.0.1"

# Multiple IPs
export NGINX_WHITELIST="127.0.0.1,192.168.1.10"

# With CIDR
export NGINX_WHITELIST="192.168.1.0/24,10.0.0.5"

./run_proxy.sh start
```

### Method 2: YAML File (Production)

```yaml
# config.yaml
nginx_whitelist:
  - "127.0.0.1"
  - "192.168.1.10"
  - "192.168.1.0/24"

enable_input_guard: true
enable_output_guard: true
```

```bash
export CONFIG_FILE="config.yaml"
./run_proxy.sh start
```

## Common Scenarios

### Scenario 1: Local Testing
```bash
export NGINX_WHITELIST="127.0.0.1"
./run_proxy.sh start
```

### Scenario 2: Single Remote Nginx
```bash
export NGINX_WHITELIST="192.168.1.10"  # Nginx server IP
./run_proxy.sh start
```

### Scenario 3: Multiple Nginx Servers
```bash
export NGINX_WHITELIST="192.168.1.10,192.168.1.11,192.168.1.12"
./run_proxy.sh start
```

### Scenario 4: Kubernetes Cluster (Pod Subnet)
```yaml
# config.yaml
nginx_whitelist:
  - "10.244.0.0/16"  # Kubernetes pod subnet
```

## Testing

```bash
# Direct access (should fail - 403)
curl http://localhost:8080/api/generate -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'

# Through nginx (should work)
curl http://api.example.com/api/generate -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'

# Simulate nginx request (for testing)
curl http://localhost:8080/api/generate -X POST \
  -H "X-Forwarded-For: 192.168.1.10" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"test"}'
```

## Verification

```bash
# Check whitelist status
curl http://localhost:8080/config | jq '.nginx_whitelist'

# Check health
curl http://localhost:8080/health | jq '.whitelist'

# View logs
./run_proxy.sh logs | grep "whitelist"
```

## Nginx Configuration

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
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Disable Whitelist (For Testing Only)

```bash
# Empty whitelist = allow all
export NGINX_WHITELIST=""
./run_proxy.sh start
```

## Troubleshooting

```bash
# Check if whitelist is enabled
curl http://localhost:8080/config | jq '.nginx_whitelist.enabled'

# Verify nginx IP
echo $NGINX_WHITELIST

# Restart proxy
./run_proxy.sh restart

# Check logs for rejections
./run_proxy.sh logs | grep "403\|access_denied"
```

## Key Points

✅ **Whitelist enabled** = Only specified IPs can access  
✅ **Supports** individual IPs, multiple IPs, CIDR ranges  
✅ **Headers used** = X-Forwarded-For, X-Real-IP  
✅ **Returns 403** if IP not whitelisted  
✅ **Easy config** = Environment variable or YAML  
✅ **Production ready** = Works with Nginx reverse proxy  

---

**Proxy is now Nginx-only! 🔒**
