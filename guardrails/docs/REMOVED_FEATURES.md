# Removed Features - Performance Monitoring and Security

## Summary

All performance monitoring and advanced security features have been removed from the guardrails proxy to simplify the codebase.

## Files Removed

1. **performance.py** - System performance monitoring (CPU, memory, disk, network metrics)
2. **security.py** - Advanced security features (rate limiting, input validation, security headers)
3. **LAZY_LOADING_CONFIGURATION.md** - Documentation for removed lazy loading features

## Code Changes

### ollama_guard_proxy.py

**Removed Imports:**
- `from performance import get_monitor, record_request`
- `from security import RateLimiter, InputValidator, SecurityHeadersMiddleware, rate_limit_middleware`

**Removed Components:**
- Performance monitor initialization and configuration
- Rate limiter initialization and middleware
- Security headers middleware
- Performance metrics recording in request logging
- Performance statistics endpoints

**Removed Endpoints:**
- `/metrics` - Performance metrics endpoint
- Performance-related data from `/health`, `/stats`, and `/config` endpoints

**Changed:**
- `HAS_OPTIMIZATIONS` flag replaced with `HAS_CACHE` (cache-only)
- Simplified error handling without performance tracking

### config.yaml

**Removed Sections:**
- `performance_monitoring` - All performance monitoring configuration
- `security` - All security features configuration

**Retained:**
- Basic rate limiting configuration (legacy format):
  - `rate_limit_enabled`
  - `rate_limit_per_minute`
  - `rate_limit_per_hour`
  - `rate_limit_burst`

### requirements.txt

**Removed Dependencies:**
- `prometheus-client==0.21.0` - Prometheus metrics client
- `psutil==6.1.0` - System and process monitoring

## Features Still Available

✅ **LLM Guard** - Input/output scanning with llm-guard
✅ **Caching** - Redis and in-memory caching for guard results
✅ **Concurrency Management** - Ollama-style queue management
✅ **IP Whitelisting** - Nginx access control
✅ **Language Detection** - Multi-language error messages
✅ **OpenAI Compatibility** - `/v1/chat/completions` and `/v1/completions` endpoints
✅ **Streaming Support** - Server-sent events for real-time responses

## Migration Guide

### If You Were Using Performance Monitoring

Performance monitoring features are no longer available. If you need metrics:

**Option 1: Use External Monitoring**
- Use Prometheus + Node Exporter for system metrics
- Use Nginx access logs for request statistics
- Use Docker stats for container metrics

**Option 2: Application-Level Logging**
- Request duration is still logged via the log_requests middleware
- Check logs for request timing information

### If You Were Using Security Features

**Rate Limiting:**
- No longer enforced at the application level
- Use Nginx rate limiting instead:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
limit_req zone=api_limit burst=10 nodelay;
```

**Security Headers:**
- Configure in Nginx:
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

**Input Validation:**
- Use Nginx's built-in validation or a WAF (Web Application Firewall)
- LLM Guard still provides content-level input scanning

### Configuration Changes

**Old config.yaml:**
```yaml
performance_monitoring:
  enabled: true
  cpu: true
  memory: true
  disk: true
  network: true
  requests: true
  history_size: 100

security:
  rate_limiter:
    enabled: true
    requests_per_minute: 60
    requests_per_hour: 1000
    burst_size: 10
```

**New config.yaml:**
```yaml
# Remove performance_monitoring and security sections entirely
# Use legacy rate limit format if needed (not enforced):
rate_limit_enabled: true
rate_limit_per_minute: 60
rate_limit_per_hour: 1000
rate_limit_burst: 10
```

## Benefits of Removal

1. **Simpler Codebase** - Fewer dependencies and less code to maintain
2. **Faster Startup** - No performance monitoring initialization
3. **Lower Memory Usage** - No metrics collection overhead
4. **Better Separation of Concerns** - Use specialized tools for monitoring
5. **Python 3.12 Compatible** - Removed problematic dependencies

## Recommended Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│         Nginx                   │  ← Rate limiting, security headers
│   - Rate limiting               │  ← SSL/TLS termination
│   - Security headers            │  ← Request filtering
│   - Access logs                 │  ← Basic metrics
└───────────┬─────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│   Guardrails Proxy              │  ← LLM content scanning
│   - Input/output guards         │  ← Caching
│   - Streaming support           │  ← Concurrency management
│   - OpenAI compatibility        │
└───────────┬─────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│         Ollama                  │  ← LLM inference
└─────────────────────────────────┘

External Monitoring:
- Prometheus + Node Exporter (system metrics)
- Loki + Promtail (log aggregation)
- Grafana (visualization)
```

## Testing After Removal

1. **Verify Basic Functionality:**
```bash
# Start proxy
./run_proxy.sh start

# Test health endpoint
curl http://localhost:9999/health

# Test generation
curl -X POST http://localhost:9999/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Hello world"
  }'
```

2. **Check Logs:**
```bash
./run_proxy.sh logs
```

3. **Verify Guard Functionality:**
```bash
# Test input guard (should block)
curl -X POST http://localhost:9999/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "malicious content"
  }'
```

## Support

If you need the removed features:
- Check git history to restore previous versions
- Use external tools (Prometheus, Nginx) for monitoring and security
- Consider using a dedicated API gateway (Kong, Traefik) for advanced features

---

**Date:** October 31, 2025
**Version:** Simplified (no performance/security)
