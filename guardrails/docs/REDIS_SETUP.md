# Redis Cache Setup Guide

Complete guide for setting up and configuring Redis distributed caching for the Ollama Guard Proxy.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Docker Deployment](#docker-deployment)
6. [Performance Tuning](#performance-tuning)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Production Best Practices](#production-best-practices)

## Overview

### Why Redis?

The Ollama Guard Proxy uses Redis for distributed caching to:
- **Share cache across multiple instances**: Scale horizontally with consistent caching
- **Persist cache across restarts**: Maintain cache between deployments
- **Reduce memory usage**: Offload cache from application memory
- **Improve performance**: Sub-millisecond cache access with Redis
- **Production-ready**: Battle-tested caching infrastructure

### Cache Architecture

```
┌─────────────────┐
│  Ollama Guard   │
│     Proxy       │
│  (Instance 1)   │
└────────┬────────┘
         │
         ├─────────┐
         │         │
    ┌────▼────┐    │    ┌─────────────────┐
    │  Redis  │◄───┼───►│  Ollama Guard   │
    │  Cache  │    │    │     Proxy       │
    └─────────┘    │    │  (Instance 2)   │
                   │    └─────────────────┘
                   │
         ┌─────────▼────────┐
         │  Ollama Guard    │
         │     Proxy        │
         │  (Instance 3)    │
         └──────────────────┘
```

### Features

- **Automatic Fallback**: If Redis is unavailable, falls back to in-memory LRU cache
- **Connection Pooling**: Efficient connection management (default: 50 connections)
- **TTL Support**: Configurable cache expiration (default: 3600 seconds)
- **Health Monitoring**: Built-in health checks and statistics
- **Zero-Downtime**: Cache operations don't block proxy requests

## Quick Start

### Using Docker Compose (Recommended)

1. **Start Redis with the proxy**:
   ```bash
   cd guardrails
   docker-compose up -d
   ```

2. **Verify Redis is running**:
   ```bash
   docker-compose ps redis
   redis-cli ping
   ```

3. **Check cache statistics**:
   ```bash
   curl http://localhost:8080/cache/stats
   ```

### Standalone Redis Deployment

1. **Start standalone Redis**:
   ```bash
   docker-compose -f docker-compose-redis.yml up -d
   ```

2. **Access Redis Commander** (optional web UI):
   ```
   http://localhost:8081
   ```

3. **Configure proxy to use Redis**:
   ```bash
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   ./run_proxy.sh start
   ```

## Installation

### Option 1: Docker (Recommended)

**Included in main docker-compose.yml**:
```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: ollama-guard-redis
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

### Option 2: System Installation

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install redis-server redis-tools
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

**macOS (Homebrew)**:
```bash
brew install redis
brew services start redis
```

**RHEL/CentOS**:
```bash
sudo yum install redis
sudo systemctl enable redis
sudo systemctl start redis
```

### Option 3: Build from Source

```bash
wget https://download.redis.io/redis-stable.tar.gz
tar -xzvf redis-stable.tar.gz
cd redis-stable
make
sudo make install
redis-server --version
```

### Verify Installation

```bash
# Test connection
redis-cli ping
# Expected output: PONG

# Get server info
redis-cli INFO server

# Monitor commands (Ctrl+C to stop)
redis-cli MONITOR
```

## Configuration

### Environment Variables

Configure Redis connection via environment variables:

```bash
# Enable/disable Redis caching
export REDIS_ENABLED=true                # true or false

# Redis connection
export REDIS_HOST=localhost              # Redis server hostname
export REDIS_PORT=6379                   # Redis server port
export REDIS_DB=0                        # Redis database number (0-15)
export REDIS_PASSWORD=""                 # Redis password (optional)

# Connection pooling
export REDIS_MAX_CONNECTIONS=50          # Maximum connections in pool
export REDIS_SOCKET_CONNECT_TIMEOUT=5    # Connection timeout (seconds)
export REDIS_SOCKET_TIMEOUT=5            # Socket timeout (seconds)

# Cache behavior
export CACHE_ENABLED=true                # Enable caching
export CACHE_BACKEND=auto                # auto, redis, or memory
export CACHE_TTL=3600                    # Cache TTL in seconds
export CACHE_MAX_SIZE=1000               # Max items (memory cache only)
```

### YAML Configuration

Edit `config.yaml`:

```yaml
cache:
  enabled: true
  backend: auto           # auto, redis, memory
  ttl: 3600              # seconds
  max_size: 1000         # memory cache only
  
redis:
  host: localhost
  port: 6379
  db: 0
  password: ""           # optional
  max_connections: 50
  socket_connect_timeout: 5
  socket_timeout: 5
  decode_responses: true
  retry_on_timeout: true
  health_check_interval: 30
```

### Redis Server Configuration

Edit `redis.conf` for production:

```conf
# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence (AOF recommended for cache)
appendonly yes
appendfsync everysec

# Performance
tcp-backlog 511
timeout 300
tcp-keepalive 300

# Security (production)
bind 127.0.0.1
protected-mode yes
requirepass your_strong_password_here

# Logging
loglevel notice
logfile /var/log/redis/redis.log
```

Apply configuration:
```bash
redis-server /path/to/redis.conf
```

## Docker Deployment

### Full Stack with Redis

**docker-compose.yml** (included):
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: ollama-guard-redis
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
    ports:
      - "127.0.0.1:6379:6379"
    networks:
      - ollama-guard
    mem_limit: 256m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
  
  ollama-guard-proxy:
    build: .
    container_name: ollama-guard-proxy
    depends_on:
      redis:
        condition: service_healthy
    environment:
      REDIS_ENABLED: "true"
      REDIS_HOST: redis
      REDIS_PORT: 6379
      CACHE_BACKEND: auto
      CACHE_TTL: 3600
    networks:
      - ollama-guard
    restart: unless-stopped

volumes:
  redis_data:

networks:
  ollama-guard:
    driver: bridge
```

### Standalone Redis with Web UI

**docker-compose-redis.yml**:
```bash
docker-compose -f docker-compose-redis.yml up -d
```

Includes:
- Redis server on `localhost:6379`
- Redis Commander web UI on `http://localhost:8081`

### macOS Apple Silicon

**docker-compose-macos.yml** with optimized Redis:
```yaml
redis:
  image: redis:7-alpine
  platform: linux/arm64/v8
  mem_limit: 512m
  # ... (same configuration as above)
```

Start on macOS:
```bash
docker-compose -f docker-compose-macos.yml up -d
```

## Performance Tuning

### Connection Pool Sizing

**General formula**: `connections = workers * concurrency_per_worker * safety_factor`

Example configurations:

```bash
# Low traffic (1-2 workers)
export REDIS_MAX_CONNECTIONS=10

# Medium traffic (4 workers, 50 concurrent each)
export REDIS_MAX_CONNECTIONS=50   # Default

# High traffic (8 workers, 100 concurrent each)
export REDIS_MAX_CONNECTIONS=200
```

### Cache TTL Optimization

Balance between cache hit rate and freshness:

```bash
# Short TTL for frequently changing data
export CACHE_TTL=300        # 5 minutes

# Medium TTL for stable data
export CACHE_TTL=3600       # 1 hour (default)

# Long TTL for rarely changing data
export CACHE_TTL=86400      # 24 hours
```

### Memory Optimization

**Redis memory limits**:
```conf
# Small deployment
maxmemory 256mb

# Medium deployment
maxmemory 512mb

# Large deployment
maxmemory 2gb
```

**Monitor memory usage**:
```bash
redis-cli INFO memory | grep used_memory_human
redis-cli INFO memory | grep maxmemory_human
```

### Network Optimization

**Socket keepalive** (prevent connection drops):
```conf
tcp-keepalive 300
```

**Connection timeout** (fast failure):
```bash
export REDIS_SOCKET_CONNECT_TIMEOUT=2
export REDIS_SOCKET_TIMEOUT=2
```

### Persistence Trade-offs

| Mode | Speed | Durability | Use Case |
|------|-------|------------|----------|
| No persistence | Fastest | None | Pure cache, data loss OK |
| AOF everysec | Fast | Good | Recommended for cache |
| AOF always | Slow | Best | Critical data (not typical for cache) |
| RDB | Fast writes, slow snapshots | Medium | Periodic backups |

**Recommended for cache**:
```conf
appendonly yes
appendfsync everysec
```

## Monitoring

### Health Check Endpoint

```bash
# Check cache health
curl http://localhost:8080/cache/health

# Expected output:
{
  "status": "healthy",
  "backend": "redis",
  "redis_connected": true,
  "redis_ping": "PONG"
}
```

### Cache Statistics

```bash
# Get cache stats
curl http://localhost:8080/cache/stats

# Expected output:
{
  "backend": "redis",
  "hits": 1250,
  "misses": 340,
  "hit_rate": 78.62,
  "total_requests": 1590,
  "redis_info": {
    "connected_clients": 5,
    "used_memory": "2.45M",
    "total_keys": 450
  }
}
```

### Redis CLI Monitoring

**Real-time monitoring**:
```bash
# Monitor all commands
redis-cli MONITOR

# Watch key operations
redis-cli --bigkeys

# Get server stats
redis-cli INFO stats

# Check connected clients
redis-cli CLIENT LIST
```

### Key Metrics to Watch

```bash
# Memory usage
redis-cli INFO memory | grep used_memory_human

# Keyspace stats
redis-cli INFO keyspace

# Hit rate
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Connected clients
redis-cli INFO clients | grep connected_clients

# Operations per second
redis-cli INFO stats | grep instantaneous_ops_per_sec
```

### Prometheus Metrics (Optional)

Export Redis metrics to Prometheus:
```bash
# Install redis_exporter
docker run -d \
  --name redis_exporter \
  -p 9121:9121 \
  oliver006/redis_exporter:latest \
  --redis.addr=redis://localhost:6379
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Redis

**Diagnosis**:
```bash
# Test Redis server
redis-cli -h localhost -p 6379 ping

# Check if Redis is running
docker-compose ps redis           # Docker
sudo systemctl status redis       # System service

# Check network connectivity
telnet localhost 6379
nc -zv localhost 6379
```

**Solutions**:
1. Verify Redis is running
2. Check firewall rules
3. Verify `bind` address in redis.conf
4. Check Docker network connectivity

### Authentication Errors

**Problem**: `NOAUTH Authentication required`

**Solution**:
```bash
# Set password in environment
export REDIS_PASSWORD=your_password

# Or update redis.conf
requirepass your_password

# Test with password
redis-cli -a your_password ping
```

### Memory Issues

**Problem**: Redis running out of memory

**Diagnosis**:
```bash
redis-cli INFO memory | grep maxmemory
redis-cli INFO memory | grep used_memory
```

**Solutions**:
1. Increase `maxmemory` limit
2. Enable eviction policy:
   ```conf
   maxmemory 512mb
   maxmemory-policy allkeys-lru
   ```
3. Reduce cache TTL
4. Clear old data: `redis-cli FLUSHDB`

### Slow Performance

**Problem**: High cache latency

**Diagnosis**:
```bash
# Check slow log
redis-cli SLOWLOG GET 10

# Monitor latency
redis-cli --latency

# Check fragmentation
redis-cli INFO memory | grep mem_fragmentation_ratio
```

**Solutions**:
1. Increase connection pool size
2. Enable pipeline mode
3. Check network latency
4. Optimize redis.conf settings

### Fallback to Memory Cache

**Problem**: Proxy using memory cache instead of Redis

**Check logs**:
```bash
tail -f logs/proxy.log | grep -i redis
```

**Common causes**:
1. Redis not running
2. Wrong connection details
3. Network issues
4. Authentication failure

**Verify configuration**:
```bash
# Test connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

# Check environment
env | grep REDIS

# Check config.yaml
cat config.yaml | grep -A 10 redis
```

## Production Best Practices

### Security

1. **Enable authentication**:
   ```conf
   requirepass strong_password_here
   ```

2. **Bind to specific interface**:
   ```conf
   bind 127.0.0.1  # localhost only
   bind 0.0.0.0    # all interfaces (with firewall!)
   ```

3. **Disable dangerous commands**:
   ```conf
   rename-command FLUSHDB ""
   rename-command FLUSHALL ""
   rename-command CONFIG ""
   ```

4. **Enable TLS** (Redis 6+):
   ```conf
   tls-port 6380
   tls-cert-file /path/to/cert.pem
   tls-key-file /path/to/key.pem
   ```

### High Availability

**Redis Sentinel** (recommended for production):
```yaml
version: '3.8'
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --masterauth password --requirepass password
  
  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    depends_on:
      - redis-master
```

**Redis Cluster** (for very large deployments):
- Use when single Redis instance isn't enough
- Provides automatic sharding
- Requires client-side cluster support

### Backup and Recovery

**Automated backups**:
```bash
# Create backup script
#!/bin/bash
BACKUP_DIR=/backups/redis
DATE=$(date +%Y%m%d_%H%M%S)
redis-cli --rdb $BACKUP_DIR/dump_$DATE.rdb
find $BACKUP_DIR -mtime +7 -delete  # Keep 7 days
```

**Restore from backup**:
```bash
# Stop Redis
sudo systemctl stop redis

# Replace dump.rdb
sudo cp backup/dump_20240115.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis
```

### Monitoring and Alerting

**Key alerts to set up**:
1. Redis process down
2. Memory usage > 90%
3. Connection pool exhausted
4. High eviction rate
5. Slow queries > threshold

**Example Prometheus alert**:
```yaml
- alert: RedisDown
  expr: redis_up == 0
  for: 1m
  annotations:
    summary: "Redis is down"

- alert: RedisMemoryHigh
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
  for: 5m
  annotations:
    summary: "Redis memory usage > 90%"
```

### Capacity Planning

**Estimate memory requirements**:
```
Memory per cache entry ≈ 1-5 KB (depends on scan results)
Expected cache entries = request_rate * TTL * (1 - hit_rate)

Example:
- 100 requests/sec
- TTL = 3600 seconds (1 hour)
- Hit rate = 70% (30% misses)
- Entry size = 2 KB

Memory needed = 100 * 3600 * 0.3 * 2KB ≈ 216 MB
+ overhead (30%) ≈ 280 MB
```

**Scale up when**:
- Memory usage consistently > 80%
- Connection pool frequently exhausted
- Cache hit rate dropping
- Evictions happening frequently

## Summary

### Quick Reference

**Start Redis**:
```bash
# Docker
docker-compose up -d redis

# System
sudo systemctl start redis
```

**Configure Proxy**:
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export CACHE_BACKEND=auto
./run_proxy.sh start
```

**Monitor**:
```bash
# Health
curl http://localhost:8080/cache/health

# Stats
curl http://localhost:8080/cache/stats

# Redis
redis-cli INFO stats
```

### Next Steps

1. ✅ Install Redis (Docker or system)
2. ✅ Configure connection settings
3. ✅ Start proxy with Redis enabled
4. ✅ Monitor cache performance
5. ✅ Tune TTL and memory settings
6. ✅ Set up monitoring and alerts (production)
7. ✅ Configure backup/restore (production)

For more information:
- [Main Optimization Guide](OPTIMIZATION_SUMMARY.md)
- [macOS Quick Start](QUICKSTART_MACOS.md)
- [Configuration Reference](../config.yaml)
