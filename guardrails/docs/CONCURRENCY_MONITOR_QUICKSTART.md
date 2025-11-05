# Uvicorn Concurrency Monitoring - Quick Start

## 30-Second Setup

```bash
# Terminal 1: Start proxy with debug monitoring
./run_proxy.sh run --debug

# Terminal 2: Monitor in real-time (updates every 2 seconds)
./scripts/monitor_uvicorn.sh --watch

# Terminal 3: Generate test load
for i in {1..10}; do
  curl http://localhost:9999/health &
done
```

## What You'll See

**Monitor Output:**
```
Active Concurrent:  10
Peak Concurrent:    10
Total Requests:     50
Failed Requests:    0
Queue Depth:        0

Active Endpoints:
  • /health: 10
```

**Debug Logs (proxy terminal):**
```
[CONCURRENCY] Active: 10/10 | Total: 50 | Failed: 0 | Uptime: 2m 15s
[ENDPOINTS] /health: 10
[SYSTEM] CPU: 35.2% | Memory: 512.4MB | Threads: 8
```

## Commands

### Start Monitoring

```bash
# Watch mode (continuous, updates every 2s)
./scripts/monitor_uvicorn.sh --watch

# Single snapshot
./scripts/monitor_uvicorn.sh

# JSON output
./scripts/monitor_uvicorn.sh --json

# Custom update interval
./scripts/monitor_uvicorn.sh --watch --interval 1
```

### Start Proxy with Monitoring

```bash
# Full debug mode
./run_proxy.sh run --debug

# Background with monitoring
export DEBUG=true
./run_proxy.sh start

# Check status (shows if monitoring enabled)
./run_proxy.sh status
```

## Key Metrics Explained

| Metric | Meaning | Healthy | Concern |
|--------|---------|---------|---------|
| **Active Concurrent** | Requests being processed now | Low (1-5) | High (>20) |
| **Peak Concurrent** | Max seen since startup | Depends on load | N/A |
| **Total Requests** | Cumulative count | Growing | Stalled |
| **Failed Requests** | Errors encountered | 0 | Any non-zero |
| **Queue Depth** | Requests waiting | 0 | Growing trend |

## Common Tasks

### Task 1: Find Performance Limit

```bash
# Terminal 1
./run_proxy.sh run --debug

# Terminal 2
./scripts/monitor_uvicorn.sh --watch

# Terminal 3: Gradually increase load
for i in {1..100}; do
  curl http://localhost:9999/health &
done

# Observe when queue depth starts growing
# That's your performance limit
```

### Task 2: Check Endpoint Bottleneck

```bash
# Monitor will show:
# [ENDPOINTS] /v1/chat/completions: 15 | /health: 2

# /chat/completions is the bottleneck (most load)
# Consider optimizing that endpoint
```

### Task 3: Export Metrics

```bash
# Single export
./scripts/monitor_uvicorn.sh --json > metrics.json

# Periodic export
while true; do
  ./scripts/monitor_uvicorn.sh --json >> metrics_history.json
  sleep 30
done
```

### Task 4: Debug High CPU

```bash
# Terminal 1: Start with detailed monitoring
export DEBUG=true
export MONITOR_UPDATE_INTERVAL=1
./run_proxy.sh run

# Terminal 2: Watch system metrics
./scripts/monitor_uvicorn.sh --watch

# Terminal 3: Generate load and observe CPU spike
# Look at which endpoint causes spike

# Expected output shows CPU > 80%:
# [SYSTEM] CPU: 92.3% | Memory: 512.4MB | Threads: 8
```

## Real-time Output Examples

### Example 1: Low Load

```
Active Concurrent:  1
Peak Concurrent:    3
Total Requests:     15
Failed Requests:    0

Active Endpoints:
  • /health: 1

System Metrics:
  CPU: 5.2% | Memory: 450MB | Threads: 4
```

### Example 2: Moderate Load

```
Active Concurrent:  5
Peak Concurrent:    8
Total Requests:     125
Failed Requests:    0
Queue Depth:        1

Active Endpoints:
  • /v1/chat/completions: 4
  • /health: 1

System Metrics:
  CPU: 45.8% | Memory: 620MB | Threads: 6
```

### Example 3: High Load (Bottleneck)

```
Active Concurrent:  12
Peak Concurrent:    12
Total Requests:     250
Failed Requests:    0
Queue Depth:        8

Active Endpoints:
  • /v1/chat/completions: 12

System Metrics:
  CPU: 88.4% | Memory: 912MB | Threads: 8
```

## Environment Variables (Optional)

```bash
# Default: debug logs every 5 seconds
# Speed up to 1 second
export MONITOR_UPDATE_INTERVAL=1

# Disable monitoring (for production)
export DEBUG=false
export ENABLE_CONCURRENCY_MONITOR=false

# Verbose logging
export LOG_LEVEL=debug
```

## Log File Location

Debug logs with metrics are written to:
```
logs/proxy.log
```

View them:
```bash
# Live tail
tail -f logs/proxy.log

# Find concurrency metrics
grep "\[CONCURRENCY\]" logs/proxy.log | tail -20

# Find endpoints
grep "\[ENDPOINTS\]" logs/proxy.log | tail -20

# Find system metrics
grep "\[SYSTEM\]" logs/proxy.log | tail -20
```

## Troubleshooting

### "No concurrency metrics found"

**Solution:**
```bash
# Make sure DEBUG is true
export DEBUG=true

# Restart proxy
./run_proxy.sh restart

# Generate traffic
curl http://localhost:9999/health

# Try again
./scripts/monitor_uvicorn.sh
```

### Monitor not updating

**Solution:**
```bash
# Check proxy is running
ps aux | grep uvicorn

# Check log file
ls -lh logs/proxy.log

# Generate traffic
curl http://localhost:9999/health

# View logs
tail -20 logs/proxy.log
```

### High CPU/Memory readings

**Normal reasons:**
- First request loads models (higher initial CPU)
- Multiple concurrent requests (higher baseline)
- Debug logging overhead (~5% CPU)

**Solutions:**
- Increase monitor interval: `--monitor-interval 10`
- Disable in production: `export DEBUG=false`

## Next Steps

1. ✅ Start proxy: `./run_proxy.sh run --debug`
2. ✅ Monitor: `./scripts/monitor_uvicorn.sh --watch`
3. ✅ Test: `curl http://localhost:9999/health`
4. ✅ Observe metrics in real-time
5. ✅ Analyze bottlenecks
6. ✅ Optimize configuration

## For Detailed Info

- Full guide: `docs/UVICORN_CONCURRENCY_MONITOR.md`
- Integration: `docs/CONCURRENCY_MONITORING_INTEGRATION.md`
- Help: `./scripts/monitor_uvicorn.sh --help`
