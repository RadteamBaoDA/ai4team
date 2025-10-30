# Redis Cache - Quick Reference

One-page reference for Redis cache configuration and commands.

## Quick Start

```bash
# Start with Docker Compose
docker-compose up -d

# Start standalone Redis
docker-compose -f docker-compose-redis.yml up -d

# Start proxy with Redis (macOS)
./run_proxy_macos.sh start

# Start proxy with Redis (Linux)
./run_proxy.sh start
```

## Environment Variables

```bash
# Cache Settings
export CACHE_ENABLED=true          # Enable/disable caching
export CACHE_BACKEND=auto          # auto, redis, memory
export CACHE_TTL=3600              # Cache TTL (seconds)
export CACHE_MAX_SIZE=1000         # Max items (memory cache)

# Redis Connection
export REDIS_ENABLED=true          # Enable Redis
export REDIS_HOST=localhost        # Redis hostname
export REDIS_PORT=6379             # Redis port
export REDIS_DB=0                  # Database number (0-15)
export REDIS_PASSWORD=""           # Password (optional)

# Redis Performance
export REDIS_MAX_CONNECTIONS=50    # Connection pool size
export REDIS_SOCKET_CONNECT_TIMEOUT=5  # Connect timeout
export REDIS_SOCKET_TIMEOUT=5      # Socket timeout
```

## Common Commands

### Redis Server

```bash
# Start/Stop
redis-server                       # Start server
redis-server /path/to/redis.conf   # Start with config
redis-cli shutdown                 # Stop server

# Test Connection
redis-cli ping                     # Should return PONG
redis-cli -h <host> -p <port> ping
redis-cli -a <password> ping       # With authentication

# Server Info
redis-cli INFO server              # Server version, uptime
redis-cli INFO memory              # Memory usage
redis-cli INFO stats               # Statistics
redis-cli INFO keyspace            # Database keys
```

### Monitoring

```bash
# Real-time Monitoring
redis-cli MONITOR                  # Watch all commands
redis-cli --stat                   # Server stats every second
redis-cli --latency                # Measure latency

# Key Operations
redis-cli KEYS "cache:*"           # List cache keys
redis-cli DBSIZE                   # Count keys
redis-cli --bigkeys                # Find large keys
redis-cli TTL <key>                # Check TTL

# Memory
redis-cli MEMORY USAGE <key>       # Memory per key
redis-cli MEMORY STATS             # Memory statistics
redis-cli INFO memory | grep used_memory_human
```

### Cache Operations

```bash
# Get/Set
redis-cli GET <key>                # Get value
redis-cli SET <key> <value>        # Set value
redis-cli SETEX <key> <ttl> <val>  # Set with TTL
redis-cli DEL <key>                # Delete key

# Inspect
redis-cli EXISTS <key>             # Check if exists
redis-cli TYPE <key>               # Get type
redis-cli TTL <key>                # Get TTL (-1 = no expiry)

# Clear
redis-cli FLUSHDB                  # Clear current database
redis-cli FLUSHALL                 # Clear all databases
```

### Performance

```bash
# Slow Log
redis-cli SLOWLOG GET 10           # Last 10 slow queries
redis-cli SLOWLOG LEN              # Slow query count
redis-cli SLOWLOG RESET            # Clear slow log

# Clients
redis-cli CLIENT LIST              # Connected clients
redis-cli CLIENT KILL <ip:port>    # Kill client
redis-cli INFO clients             # Client stats

# Benchmark
redis-benchmark -q -n 10000        # Quick benchmark
redis-benchmark -t set,get -n 100000  # Test SET/GET
```

## Docker Commands

```bash
# Container Management
docker-compose up -d redis                    # Start Redis
docker-compose stop redis                     # Stop Redis
docker-compose restart redis                  # Restart Redis
docker-compose logs redis                     # View logs
docker-compose logs -f redis                  # Follow logs

# Access Redis CLI
docker exec -it ollama-guard-redis redis-cli
docker exec -it ollama-guard-redis redis-cli ping

# Check Container
docker-compose ps redis                       # Status
docker stats ollama-guard-redis               # Resources
docker inspect ollama-guard-redis             # Full info
```

## Proxy Endpoints

```bash
# Health Check
curl http://localhost:8080/cache/health

# Response:
{
  "status": "healthy",
  "backend": "redis",
  "redis_connected": true,
  "redis_ping": "PONG"
}

# Cache Statistics
curl http://localhost:8080/cache/stats

# Response:
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

## Configuration Files

### config.yaml

```yaml
cache:
  enabled: true
  backend: auto          # auto, redis, memory
  ttl: 3600             # seconds
  max_size: 1000        # memory cache only
  
redis:
  host: localhost
  port: 6379
  db: 0
  password: ""          # optional
  max_connections: 50
  socket_connect_timeout: 5
  socket_timeout: 5
```

### redis.conf (Key Settings)

```conf
# Memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
appendonly yes
appendfsync everysec

# Network
bind 127.0.0.1
port 6379
tcp-backlog 511
timeout 300

# Security (Production)
protected-mode yes
requirepass <your_password>

# Performance
tcp-keepalive 300
lazyfree-lazy-eviction yes
```

## Troubleshooting

### Connection Failed

```bash
# 1. Check if Redis is running
docker-compose ps redis
redis-cli ping

# 2. Check port
netstat -an | grep 6379
lsof -i :6379

# 3. Test connection
telnet localhost 6379
nc -zv localhost 6379

# 4. Check logs
docker-compose logs redis | tail -50
```

### Authentication Error

```bash
# Error: NOAUTH Authentication required

# Solution 1: Set password in environment
export REDIS_PASSWORD=your_password

# Solution 2: Update config.yaml
redis:
  password: your_password

# Test with password
redis-cli -a your_password ping
```

### Out of Memory

```bash
# Check memory usage
redis-cli INFO memory | grep used_memory_human
redis-cli INFO memory | grep maxmemory_human

# Solution 1: Increase limit (redis.conf)
maxmemory 512mb

# Solution 2: Enable eviction
maxmemory-policy allkeys-lru

# Solution 3: Clear cache
redis-cli FLUSHDB

# Restart Redis
docker-compose restart redis
```

### Slow Performance

```bash
# Check slow queries
redis-cli SLOWLOG GET 10

# Check latency
redis-cli --latency
redis-cli --latency-history

# Check memory fragmentation
redis-cli INFO memory | grep mem_fragmentation_ratio

# Solutions:
# - Increase connection pool
# - Reduce cache TTL
# - Check network latency
# - Restart Redis (defragment)
```

## Performance Tuning

### Connection Pool Sizing

```bash
# Formula: workers × concurrency × safety_factor
# Example: 4 workers × 10 concurrent × 1.25 = 50 connections

# Low traffic
export REDIS_MAX_CONNECTIONS=10

# Medium traffic (default)
export REDIS_MAX_CONNECTIONS=50

# High traffic
export REDIS_MAX_CONNECTIONS=200
```

### TTL Optimization

```bash
# Short TTL (frequently changing data)
export CACHE_TTL=300        # 5 minutes

# Medium TTL (stable data, default)
export CACHE_TTL=3600       # 1 hour

# Long TTL (rarely changing)
export CACHE_TTL=86400      # 24 hours
```

### Memory Limits

```conf
# Small deployment
maxmemory 256mb

# Medium deployment
maxmemory 512mb

# Large deployment
maxmemory 2gb

# Always set eviction policy
maxmemory-policy allkeys-lru
```

## Monitoring Metrics

### Key Metrics

```bash
# Hit Rate
echo "STATS hits: $(redis-cli INFO stats | grep keyspace_hits)"
echo "STATS misses: $(redis-cli INFO stats | grep keyspace_misses)"

# Memory
redis-cli INFO memory | grep used_memory_human
redis-cli INFO memory | grep mem_fragmentation_ratio

# Keys
redis-cli DBSIZE

# Clients
redis-cli INFO clients | grep connected_clients

# Operations/sec
redis-cli INFO stats | grep instantaneous_ops_per_sec

# Evictions
redis-cli INFO stats | grep evicted_keys
```

### Watch Dashboard (Live)

```bash
# Create simple monitoring script
watch -n 1 'redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses|instantaneous_ops_per_sec|evicted_keys"'

# Or use redis-cli built-in
redis-cli --stat 1
```

## Backup & Recovery

### Manual Backup

```bash
# Create backup (RDB)
redis-cli SAVE                     # Blocking save
redis-cli BGSAVE                   # Background save

# Check last save
redis-cli LASTSAVE

# Backup location (default)
/var/lib/redis/dump.rdb            # Linux
/usr/local/var/db/redis/dump.rdb   # macOS
```

### Restore

```bash
# 1. Stop Redis
redis-cli SHUTDOWN

# 2. Replace dump file
cp backup/dump_20240115.rdb /var/lib/redis/dump.rdb

# 3. Start Redis
redis-server
```

### Automated Backup Script

```bash
#!/bin/bash
BACKUP_DIR=/backups/redis
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
redis-cli --rdb $BACKUP_DIR/dump_$DATE.rdb

# Keep last 7 days
find $BACKUP_DIR -name "dump_*.rdb" -mtime +7 -delete

# Verify
if [ -f "$BACKUP_DIR/dump_$DATE.rdb" ]; then
  echo "Backup created: dump_$DATE.rdb"
else
  echo "Backup failed!"
  exit 1
fi
```

## Security Checklist

```bash
# ✓ Enable authentication
requirepass <strong_password>

# ✓ Bind to specific interface
bind 127.0.0.1                    # Localhost only
bind 10.0.1.5                     # Specific IP

# ✓ Enable protected mode
protected-mode yes

# ✓ Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""

# ✓ Use TLS (Redis 6+)
tls-port 6380
tls-cert-file /path/to/cert.pem
tls-key-file /path/to/key.pem

# ✓ Limit connections
maxclients 1000

# ✓ Set memory limit
maxmemory 512mb
maxmemory-policy allkeys-lru
```

## Useful Scripts

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

if redis-cli -h $REDIS_HOST -p $REDIS_PORT ping &>/dev/null; then
  echo "✓ Redis is healthy"
  exit 0
else
  echo "✗ Redis is down"
  exit 1
fi
```

### Cache Clear Script

```bash
#!/bin/bash
# clear_cache.sh

read -p "Clear ALL cache keys? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  redis-cli FLUSHDB
  echo "✓ Cache cleared"
else
  echo "Cancelled"
fi
```

### Statistics Script

```bash
#!/bin/bash
# cache_stats.sh

echo "=== Redis Cache Statistics ==="
echo ""
echo "Server:"
redis-cli INFO server | grep -E "redis_version|uptime_in_seconds"
echo ""
echo "Memory:"
redis-cli INFO memory | grep -E "used_memory_human|mem_fragmentation_ratio"
echo ""
echo "Stats:"
redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses|evicted_keys"
echo ""
echo "Keys:"
echo "  Total: $(redis-cli DBSIZE)"
```

## References

- **Full Setup Guide**: [REDIS_SETUP.md](REDIS_SETUP.md)
- **Implementation Details**: [REDIS_INTEGRATION.md](REDIS_INTEGRATION.md)
- **Configuration**: [../config.yaml](../config.yaml)
- **Redis Docs**: https://redis.io/documentation

---

**Quick Help**:
```bash
# Start everything
docker-compose up -d

# Check health
curl http://localhost:8080/cache/health

# View stats
curl http://localhost:8080/cache/stats

# Monitor Redis
redis-cli MONITOR
```
