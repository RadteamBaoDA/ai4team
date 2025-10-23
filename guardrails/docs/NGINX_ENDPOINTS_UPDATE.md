# Nginx Configuration Updates - Ollama API Endpoints

## Overview
Updated both Nginx configuration files to support the complete Ollama API with load balancing and security features.

## Files Updated
1. **nginx-guard.conf** - Standard configuration with SSL support
2. **nginx-ollama-production.conf** - Production configuration with IP access control, rate limiting, and advanced security

## New API Endpoints Supported

### Generation Endpoints (with LLM Guard scanning)
| Endpoint | Method | Purpose | Features |
|----------|--------|---------|----------|
| `/api/generate` | POST | Generate completion | Input/Output scanning, Streaming |
| `/api/chat` | POST | Chat completion | Input/Output scanning, Streaming |

### Model Management Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/pull` | POST | Download model from library |
| `/api/push` | POST | Upload model to library |
| `/api/create` | POST | Create model from GGUF/SafeTensors |
| `/api/tags` | GET | List all local models |
| `/api/show` | POST | Show model information |
| `/api/delete` | DELETE | Delete a model |
| `/api/copy` | POST | Copy a model |

### Utility Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/embed` | POST | Generate embeddings |
| `/api/ps` | GET | List running models |
| `/api/version` | GET | Get Ollama version |

### Legacy Endpoints (Deprecated)
| Old Endpoint | Redirects To | Status Code |
|-------------|-------------|------------|
| `/v1/generate` | `/api/generate` | 308 |
| `/v1/chat/completions` | `/api/chat` | 308 |
| `/v1/*` | Pass-through | Fallback |

## Load Balancing Configuration

### Upstream Configuration
```nginx
upstream ollama_guard_cluster {
    least_conn;  # Least connections load balancing
    
    server 127.0.0.1:8080 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8081 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8082 weight=1 max_fails=3 fail_timeout=30s;
}
```

### Health Check
- **Endpoint**: `/health`
- **Rate Limit**: 30 req/sec (higher than general API)
- **Access Logging**: Disabled for performance
- **Connection**: Keep-alive enabled

## Rate Limiting (Production Config)

### Rate Limit Zones
| Zone | Limit | Used For |
|------|-------|----------|
| `api_limit` | 10 req/sec | General API endpoints |
| `health_limit` | 30 req/sec | Health & system endpoints |

### Burst Configuration
| Endpoint Type | Burst | Connection Limit |
|--------------|-------|------------------|
| Generation (generate, chat) | 20 | 10 per IP |
| Model management | 5-10 | Varies |
| System endpoints | 10-50 | Varies |

## Streaming Configuration

### Key Settings for Streaming
```nginx
# Disable buffering
proxy_buffering off;
proxy_request_buffering off;

# Long timeouts for streaming
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;

# Chunked encoding
proxy_set_header Transfer-Encoding chunked;
```

## Security Features

### IP Access Control
```nginx
# Whitelist (optional)
geo $ip_allowed {
    default 0;
    127.0.0.1 1;
    ::1 1;
    # Add trusted networks
}

# Blacklist (optional)
geo $ip_denied {
    default 0;
    # Add blocked IPs
}
```

### Security Headers
- `Strict-Transport-Security` - Force HTTPS
- `X-Content-Type-Options` - Prevent MIME sniffing
- `X-Frame-Options` - Prevent clickjacking
- `X-XSS-Protection` - XSS protection
- `Content-Security-Policy` - CSP enforcement

### SSL/TLS Configuration
- **Protocols**: TLSv1.2, TLSv1.3
- **Ciphers**: ECDHE, AES-GCM, DHE
- **Session Cache**: 10m timeout
- **OCSP Stapling**: Available for production

## Endpoint Configurations

### High-Traffic Endpoints (generate, chat)
- Rate limit: 10 req/sec + 20 burst
- Connections: 10 per IP
- Timeout: 3600s
- Buffering: Disabled

### Long-Duration Endpoints (pull, push, create)
- Rate limit: 10 req/sec + 5 burst
- Timeout: 3600s (1 hour)
- Buffering: Disabled

### Query Endpoints (tags, show, ps, version)
- Rate limit: 10-30 req/sec
- Timeout: 10-30s
- Buffering: Default

## Configuration Deployment

### For nginx-guard.conf (Standard)
```bash
# Copy to system
sudo cp nginx-guard.conf /etc/nginx/conf.d/ollama-guard.conf

# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### For nginx-ollama-production.conf (Production)
```bash
# Copy to system
sudo cp nginx-ollama-production.conf /etc/nginx/conf.d/ollama-guard-prod.conf

# Update SSL certificates in config
# - /etc/nginx/ssl/ollama-guard.crt
# - /etc/nginx/ssl/ollama-guard.key

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

## Testing Endpoints

### Generate Completion
```bash
curl -X POST https://your-server/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2", "prompt": "Hello", "stream": false}'
```

### Chat Completion
```bash
curl -X POST https://your-server/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### List Models
```bash
curl https://your-server/api/tags
```

### Health Check
```bash
curl https://your-server/health
```

### Get Version
```bash
curl https://your-server/api/version
```

## Performance Considerations

### Buffer Sizes
- `client_header_buffer_size`: 16k
- `large_client_header_buffers`: 8 x 64k
- `proxy_buffer_size`: 128k
- `proxy_buffers`: 4 x 256k

### Timeouts
- `client_header_timeout`: 60s
- `client_body_timeout`: 60s
- `proxy_connect_timeout`: 60s
- `proxy_send_timeout`: 300s (general), 3600s (streaming)
- `proxy_read_timeout`: 300s (general), 3600s (streaming)

### Connection Settings
- `keepalive_timeout`: 65s
- `proxy_http_version`: 1.1 (with keep-alive)
- `Connection`: "" (empty for keep-alive)

## Monitoring & Logging

### Log Files
- `access_log`: `/var/log/nginx/ollama_guard_access.log`
- `error_log`: `/var/log/nginx/ollama_guard_error.log`

### Health Check Logging
- Health check endpoint has `access_log off` to reduce noise

### Log Format
```nginx
combined  # Includes method, path, status, response time, user agent
```

## Troubleshooting

### High Latency
- Check `proxy_read_timeout` and `proxy_send_timeout`
- Verify proxy instances are running
- Check Ollama server health

### Rate Limiting Issues
- Adjust burst values in rate limit zones
- Check `limit_req_zone` and `limit_conn_zone` settings

### Streaming Issues
- Verify `proxy_buffering off` is set
- Check `Transfer-Encoding chunked`
- Look for proxy buffer size errors

### SSL Certificate Issues
- Verify certificate paths in config
- Test with `sudo nginx -t`
- Check certificate expiration

## Migration from Old Endpoints

### Option 1: Automatic Redirect (Current)
Old endpoints (`/v1/*`) redirect with 308 status code to new endpoints (`/api/*`)

### Option 2: Manual Migration
Update client code to use new endpoints:
```python
# Old
response = requests.post('http://localhost/v1/generate', json=payload)

# New
response = requests.post('http://localhost/api/generate', json=payload)
```

## Additional Resources
- Ollama API Documentation: https://docs.ollama.com/api
- Nginx Documentation: https://nginx.org/en/docs/
- LLM Guard Documentation: https://llm-guard.ai/
