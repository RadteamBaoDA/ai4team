# Concurrency Monitoring - Integration Guide

## Implementation Overview

The concurrency monitoring system tracks task execution across the uvicorn proxy through three main components:

### 1. **ConcurrencyMonitor** (`utils/concurrency_monitor.py`)
Python module that:
- Tracks active/completed tasks per endpoint
- Monitors peak concurrent connections
- Logs metrics in real-time to debug logs
- Provides JSON metrics export

### 2. **monitor_uvicorn.sh** (Shell Script)
Bash utility that:
- Parses debug logs for concurrency metrics
- Displays human-readable output
- Supports watch mode with auto-updates
- Exports JSON for integration

### 3. **Enhanced run_proxy.sh** (Script)
Updated startup script with:
- Concurrency monitor integration
- Debug flag support
- Monitor interval configuration
- Environment variable export

## Debug Log Output Examples

### Concurrency Metrics Line

```
[CONCURRENCY] Active: 4/12 | Total: 256 | Failed: 0 | Queue: 2 | Uptime: 1h 23m 45s
```

**Parsed Values:**
- `Active: 4/12` → Active=4, Peak=12
- `Total: 256` → Total requests
- `Failed: 0` → Failed count
- `Queue: 2` → Queue depth
- `Uptime: 1h 23m 45s` → System uptime

### Endpoints Metrics Line

```
[ENDPOINTS] /v1/chat/completions: 3 | /v1/completions: 1 | /v1/models: 0
```

**Shows:**
- Per-endpoint active task counts
- Real-time breakdown of load

### System Metrics Line

```
[SYSTEM] CPU: 42.5% | Memory: 512.3MB | Threads: 8
```

**Shows:**
- CPU percentage
- Memory usage in MB
- Thread count

## Real-time Usage

### Basic Monitoring

```bash
# Terminal 1: Start proxy with debug
./run_proxy.sh run --debug

# Terminal 2: Monitor in real-time
./scripts/monitor_uvicorn.sh --watch

# Terminal 3: Generate load
for i in {1..10}; do
  curl -X POST http://localhost:9999/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"llama","messages":[{"role":"user","content":"test"}]}' &
done
```

**Expected Output:**

```
╔════════════════════════════════════════════════════════╗
║  Uvicorn Concurrency Monitor
╠════════════════════════════════════════════════════════╣
║  Active Concurrent:  10
║  Peak Concurrent:    10
║  Total Requests:     10
║  Failed Requests:    0
╠════════════════════════════════════════════════════════╣
║  Active Endpoints:
║    • /v1/chat/completions: 10
╠════════════════════════════════════════════════════════╣
║  System Metrics:
║    CPU: 75.3% | Memory: 892.4 MB | Threads: 12
╚════════════════════════════════════════════════════════╝
```

## Integration Patterns

### Pattern 1: Load Testing with Metrics

```bash
#!/bin/bash

# Start monitoring in background
./scripts/monitor_uvicorn.sh --watch --interval 1 > load_test_metrics.txt &
MONITOR_PID=$!

# Run load test
ab -n 1000 -c 50 http://localhost:9999/health

# Get final metrics
echo "=== Final Metrics ===" >> load_test_metrics.txt
./scripts/monitor_uvicorn.sh >> load_test_metrics.txt

# Stop monitoring
kill $MONITOR_PID
```

### Pattern 2: Continuous Metric Collection

```bash
#!/bin/bash

# Collect metrics every 30 seconds
while true; do
  {
    echo "$(date): Metrics snapshot"
    ./scripts/monitor_uvicorn.sh --json
    echo ""
  } >> metrics_continuous.json
  sleep 30
done
```

### Pattern 3: Alert on High Queue Depth

```bash
#!/bin/bash

while true; do
  METRICS=$(./scripts/monitor_uvicorn.sh --json)
  QUEUE=$(echo "$METRICS" | jq '.queue_depth')
  
  if [ "$QUEUE" -gt 10 ]; then
    echo "ALERT: Queue depth is $QUEUE!"
    # Send alert
    # notify_admin "Queue depth critical: $QUEUE"
  fi
  
  sleep 5
done
```

### Pattern 4: Parse Log History

```bash
#!/bin/bash

# Extract all metrics from log
grep "\[CONCURRENCY\]" logs/proxy.log | tail -20 | while read line; do
  ACTIVE=$(echo "$line" | grep -oP 'Active: \K\d+(?=/)')
  PEAK=$(echo "$line" | grep -oP 'Peak: \K\d+')
  TOTAL=$(echo "$line" | grep -oP 'Total: \K\d+')
  
  echo "Active: $ACTIVE, Peak: $PEAK, Total: $TOTAL"
done
```

## Configuration Combinations

### Development - Maximum Visibility

```bash
export DEBUG=true
export MONITOR_UPDATE_INTERVAL=1.0
export LOG_LEVEL=debug

./run_proxy.sh run --debug --monitor-interval 1
```

**Result:**
- Real-time monitoring every second
- Full debug output
- Detailed endpoint tracking

### Production - Minimal Overhead

```bash
export DEBUG=false
export ENABLE_CONCURRENCY_MONITOR=false
export LOG_LEVEL=info

./run_proxy.sh start
```

**Result:**
- No monitoring overhead
- Only error logs
- Optimal performance

### Troubleshooting - Focused Monitoring

```bash
export DEBUG=true
export MONITOR_UPDATE_INTERVAL=5.0
export LOG_LEVEL=warning

./run_proxy.sh run
```

**Result:**
- Monitor every 5 seconds
- Only warnings and errors
- Reduced log volume

## Debug Log Parsing Examples

### Extract Peak Concurrent

```bash
grep "\[CONCURRENCY\]" logs/proxy.log | \
  grep -oP 'Peak: \K\d+' | \
  sort -n | \
  tail -1
```

### Find High CPU Episodes

```bash
grep "\[SYSTEM\]" logs/proxy.log | \
  awk -F'CPU: |%' '{if($2 > 80) print $0}'
```

### Count Failed Requests

```bash
grep "\[CONCURRENCY\]" logs/proxy.log | \
  grep -oP 'Failed: \K\d+' | \
  awk '{sum+=$1} END {print sum}'
```

### Identify Bottleneck Endpoints

```bash
grep "\[ENDPOINTS\]" logs/proxy.log | \
  tail -5 | \
  grep -oP '[^|]+(?=:)' | \
  sort | uniq -c | \
  sort -rn
```

## Metrics Interpretation Guide

### Scenario 1: Healthy System

```
Active Concurrent:  2-3
Peak Concurrent:    15 (occasional spike)
Total Requests:     1000+ (cumulative)
Failed Requests:    0
Queue Depth:        0-1 (empty most of time)
CPU:               20-40%
Memory:            Stable ~500MB
```

**Interpretation:** System is handling load well, sufficient capacity.

### Scenario 2: Bottleneck Detected

```
Active Concurrent:  8
Peak Concurrent:    8
Total Requests:     100
Failed Requests:    0
Queue Depth:        5-10 (growing)
CPU:               85-95%
Memory:            Growing → Potential leak
```

**Interpretation:** System near capacity, queue building. Consider:
- Increase workers
- Optimize slow endpoint
- Check memory leak

### Scenario 3: Error Condition

```
Active Concurrent:  1
Peak Concurrent:    5
Total Requests:     50
Failed Requests:    15 (30% failure rate)
Queue Depth:        2-3
CPU:               40%
Memory:            500MB
```

**Interpretation:** High error rate. Check:
- Application logs
- External service availability
- Resource limits

## Quick Reference - Commands

```bash
# Start with monitoring
./run_proxy.sh run --debug

# Monitor in real-time
./scripts/monitor_uvicorn.sh --watch

# Get JSON metrics
./scripts/monitor_uvicorn.sh --json

# Check status with metrics
./run_proxy.sh status

# View logs with metrics
./run_proxy.sh logs

# Parse peak concurrent
grep "\[CONCURRENCY\]" logs/proxy.log | grep -oP 'Peak: \K\d+'

# Export metrics to file
./scripts/monitor_uvicorn.sh --json > metrics_$(date +%s).json
```

## Performance Baseline

Baseline metrics for reference (single proxy instance):

| Metric | CPU Only | GPU |
|--------|----------|-----|
| Idle CPU | 5-10% | 8-15% |
| Idle Memory | 400-500MB | 800-1200MB |
| Single Request Peak | 15-25% | 35-50% |
| 10 Concurrent | 60-80% | 90%+ |
| Error-free Queue | 0-1 | 0-2 |

## Troubleshooting Integration

### Monitor Shows "No metrics found"

1. Check DEBUG is enabled:
   ```bash
   echo $DEBUG
   # Should output: true
   ```

2. Generate traffic:
   ```bash
   curl http://localhost:9999/health
   ```

3. Try again:
   ```bash
   ./scripts/monitor_uvicorn.sh
   ```

### Metrics Not Updating

1. Check if proxy is running:
   ```bash
   ps aux | grep uvicorn
   ```

2. Check log file size:
   ```bash
   ls -lh logs/proxy.log
   ```

3. Check recent log content:
   ```bash
   tail -50 logs/proxy.log | grep CONCURRENCY
   ```

### High False Positive Queue Alerts

The queue depth shows requests waiting. Normal ranges:
- 0 = No queue
- 1-2 = Transient load
- 3-5 = Sustained load
- 5+ = Backlog forming

Adjust alert thresholds accordingly.

## Next Steps

1. **Enable monitoring:** `./run_proxy.sh run --debug`
2. **Start watching:** `./scripts/monitor_uvicorn.sh --watch`
3. **Generate load:** `curl http://localhost:9999/health`
4. **Observe metrics:** Watch real-time updates
5. **Analyze patterns:** Look for trends
6. **Optimize:** Adjust configuration based on results

## Related Files

- `utils/concurrency_monitor.py` - Monitor implementation
- `scripts/monitor_uvicorn.sh` - Monitor CLI
- `scripts/run_proxy.sh` - Proxy launcher (updated)
- `UVICORN_CONCURRENCY_MONITOR.md` - User guide
- `logs/proxy.log` - Metrics output

