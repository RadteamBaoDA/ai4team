# Uvicorn Concurrency Monitor - Real-time Task Tracking

## Overview

The Uvicorn Concurrency Monitor provides real-time tracking of concurrent connections and active tasks across all endpoints. It helps identify performance bottlenecks and understand request patterns.

## Features

✅ **Real-time Concurrency Tracking**
- Current active concurrent connections
- Peak concurrent connections reached
- Per-endpoint active task counts

✅ **Request Metrics**
- Total requests processed
- Failed requests count
- Request queue depth (if backlog exists)
- Per-endpoint completion counts

✅ **System Metrics** (when psutil available)
- CPU usage percentage
- Memory usage (MB)
- Thread count

✅ **Multiple Monitoring Modes**
- Single snapshot report
- Continuous watch mode with live updates
- JSON output for integration
- Colored terminal output

## Quick Start

### 1. Enable Debug Logging (Required for Monitoring)

```bash
# Start proxy with debug logging and monitoring
./run_proxy.sh run --debug

# Or set environment variables
export DEBUG=true
export ENABLE_CONCURRENCY_MONITOR=true
./run_proxy.sh start
```

### 2. View Current Metrics

```bash
# Single snapshot
./scripts/monitor_uvicorn.sh

# Continuous watch (updates every 2 seconds)
./scripts/monitor_uvicorn.sh --watch

# Custom update interval
./scripts/monitor_uvicorn.sh --watch --interval 1
```

### 3. JSON Output for Integration

```bash
# Get metrics in JSON format
./scripts/monitor_uvicorn.sh --json
```

## Output Format

### Human Readable

```
╔════════════════════════════════════════════════════════╗
║  Uvicorn Concurrency Monitor
╠════════════════════════════════════════════════════════╣
║  Active Concurrent:  4
║  Peak Concurrent:    12
║  Total Requests:     256
║  Failed Requests:    0
║  Queue Depth:        2
╠════════════════════════════════════════════════════════╣
║  Active Endpoints:
║    • /v1/chat/completions: 3
║    • /v1/completions: 1
╠════════════════════════════════════════════════════════╣
║  System Metrics:
║    CPU: 42.5% | Memory: 512.3 MB | Threads: 8
╚════════════════════════════════════════════════════════╝
```

### JSON Output

```json
{
  "active_concurrent": 4,
  "peak_concurrent": 12,
  "total_requests": 256,
  "failed_requests": 0,
  "queue_depth": 2,
  "cpu_percent": 42.5,
  "memory_mb": 512.3
}
```

## Debug Log Format

The concurrency monitor writes debug logs to the proxy log file in three categories:

### CONCURRENCY Logs
```
[CONCURRENCY] Active: 4/12 | Total: 256 | Failed: 0 | Queue: 2 | Uptime: 1h 23m 45s
```

Shows:
- `Active: 4/12` - 4 current active tasks, 12 peak
- `Total: 256` - Total requests processed
- `Failed: 0` - Failed requests
- `Queue: 2` - Current queue depth
- `Uptime` - How long server has been running

### ENDPOINTS Logs
```
[ENDPOINTS] /v1/chat/completions: 3 | /v1/completions: 1 | /health: 0
```

Shows:
- Active task count per endpoint
- Endpoints with 0 tasks not shown
- Updated in real-time

### SYSTEM Logs
```
[SYSTEM] CPU: 42.5% | Memory: 512.3MB | Threads: 8
```

Shows:
- CPU usage percentage
- Memory usage in MB
- Thread count

## Configuration

### Environment Variables

```bash
# Enable/disable concurrency monitoring
export ENABLE_CONCURRENCY_MONITOR=true

# Update interval (seconds)
export MONITOR_UPDATE_INTERVAL=5.0

# Enable debug logging (required for monitoring)
export DEBUG=true
```

### Command Line Options

```bash
# Enable debug with custom interval
./run_proxy.sh run --debug --monitor-interval 2

# Set log level and monitoring
./run_proxy.sh run --log-level debug --monitor-interval 1
```

## Use Cases

### 1. Performance Tuning

Monitor concurrent connections to determine optimal worker/concurrency settings:

```bash
# Start with monitoring
./run_proxy.sh run --debug

# In another terminal, monitor in real-time
./scripts/monitor_uvicorn.sh --watch

# Apply load and observe peak concurrent
# Use results to tune: --workers and concurrency settings
```

### 2. Load Testing

```bash
# Terminal 1: Start proxy with monitoring
./run_proxy.sh run --debug --monitor-interval 1

# Terminal 2: Run load test
./scripts/load_test.sh

# Terminal 3: Monitor in real-time
./scripts/monitor_uvicorn.sh --watch --interval 1
```

### 3. Troubleshooting High Latency

When experiencing latency issues:

```bash
# Enable detailed monitoring
export DEBUG=true
export MONITOR_UPDATE_INTERVAL=2

./run_proxy.sh start

# Monitor for queue depth
./scripts/monitor_uvicorn.sh --watch

# High queue depth indicates system is overwhelmed
# Look for which endpoints are bottlenecks
```

### 4. Integration with Monitoring Systems

```bash
# Get JSON metrics for periodic collection
./scripts/monitor_uvicorn.sh --json > /tmp/metrics.json

# Parse with jq
./scripts/monitor_uvicorn.sh --json | jq '.active_concurrent'
```

## Interpreting Metrics

### Active Concurrent
- **Definition:** Current number of connections actively being processed
- **Healthy Range:** Depends on hardware, typically < peak × 0.2
- **High Value:** System is busy or has bottleneck

### Peak Concurrent
- **Definition:** Maximum concurrent connections seen since startup
- **Use For:** Capacity planning and worker configuration

### Queue Depth
- **Definition:** Number of requests waiting for processing
- **Healthy:** 0 or very low (< 5)
- **High Value:** System cannot keep up with incoming requests
- **Action:** Increase workers or optimize endpoint performance

### Failed Requests
- **Definition:** Requests that raised exceptions
- **Healthy:** 0 or very low
- **High Value:** Check application logs for errors

### System Metrics
- **CPU < 80%:** Room for more concurrency
- **CPU > 90%:** System is maxed out
- **Memory Trend:** Growing = potential memory leak
- **Threads Growing:** Normal under load, should stabilize

## Advanced Usage

### 1. Monitor Specific Process

```bash
# Monitor by PID
./scripts/monitor_uvicorn.sh --pid 12345

# Or let it auto-detect from proxy.pid
./scripts/monitor_uvicorn.sh
```

### 2. Custom Update Interval

```bash
# Fast updates (every 1 second)
./scripts/monitor_uvicorn.sh --watch --interval 1

# Slow updates (every 10 seconds)
./scripts/monitor_uvicorn.sh --watch --interval 10
```

### 3. No Colors (For Logs)

```bash
# Save colored output to file
./scripts/monitor_uvicorn.sh --no-color > metrics.txt

# Useful for CI/CD pipelines
./scripts/monitor_uvicorn.sh --json --no-color | jq '.'
```

### 4. Continuous Logging

```bash
# Log metrics every 5 seconds to file
while true; do
  ./scripts/monitor_uvicorn.sh --json >> metrics_history.json
  sleep 5
done
```

## Metrics Collection

### Enable Monitoring on Startup

```bash
# Start with full debug + monitoring
./run_proxy.sh start

# Check status
./run_proxy.sh status

# View logs with metrics
./run_proxy.sh logs
```

### View Historical Metrics

```bash
# Show all concurrency lines from log
grep "\[CONCURRENCY\]" logs/proxy.log

# Show by endpoint
grep "\[ENDPOINTS\]" logs/proxy.log

# Show system metrics history
grep "\[SYSTEM\]" logs/proxy.log
```

### Export Metrics

```bash
# Extract metrics to CSV
grep "\[CONCURRENCY\]" logs/proxy.log | \
  awk -F'[|:]' '{print $2,$3,$4}' > metrics.csv
```

## Troubleshooting

### No Metrics in Logs

**Problem:** `./monitor_uvicorn.sh` says "No concurrency metrics found"

**Solution:**
1. Ensure DEBUG is enabled:
   ```bash
   export DEBUG=true
   ./run_proxy.sh restart
   ```

2. Check log file exists:
   ```bash
   tail logs/proxy.log
   ```

3. Generate some traffic:
   ```bash
   curl http://localhost:9999/health
   ```

4. Try monitoring again:
   ```bash
   ./scripts/monitor_uvicorn.sh
   ```

### Monitor Not Starting

**Problem:** "Proxy is not running (no PID file)"

**Solution:**
```bash
# Verify proxy is running
ps aux | grep uvicorn

# Check PID file
cat logs/proxy.pid

# Or monitor specific PID
./scripts/monitor_uvicorn.sh --pid 12345
```

### High CPU Usage in Monitor

The monitor updates every N seconds (default 5). If CPU is high:
- Increase interval: `--monitor-interval 10`
- Disable system metrics: Use log parsing instead

## Performance Impact

The concurrency monitor has minimal overhead:
- **Debug logging:** ~2-5% CPU increase
- **Monitor updates:** Updates every 5 seconds (configurable)
- **Memory:** <10MB additional
- **Network:** None (local monitoring only)

For production, consider:
- Longer update interval (10s or more)
- Only enable when troubleshooting
- Disable in high-performance scenarios

## Integration Examples

### With Prometheus

```bash
# Export metrics to Prometheus format
./scripts/monitor_uvicorn.sh --json | jq '.active_concurrent' | \
  echo "uvicorn_active_concurrent $(< /dev/stdin)" >> prometheus.txt
```

### With Datadog

```bash
# Submit metric to Datadog
METRIC=$(./scripts/monitor_uvicorn.sh --json | jq '.active_concurrent')
curl -X POST https://api.datadoghq.com/api/v1/series \
  -H "DD-API-KEY: $DD_API_KEY" \
  -d "{\"series\": [{\"metric\": \"uvicorn.active_concurrent\", \"points\": [[$(date +%s), $METRIC]]}]}"
```

### With InfluxDB

```bash
# Send metrics to InfluxDB
./scripts/monitor_uvicorn.sh --json | jq '.[]' | while read -r key value; do
  curl -X POST http://localhost:8086/write?db=proxy \
    -d "concurrency,$key=$value $(($(date +%s)*1000000000))"
done
```

## Related Documentation

- `CONCURRENCY_MONITOR_DEBUG.md` - Debug log format reference
- `run_proxy.sh --help` - Proxy script options
- `monitor_uvicorn.sh --help` - Monitor script options

## Version History

- **v1.0** (Current) - Initial release with real-time concurrency tracking

