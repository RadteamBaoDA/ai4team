# Deployment Checklist

## Pre-Deployment Validation

### 1. Environment Setup
- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] For Apple Silicon: MLX installed (optional): `pip install mlx mlx-lm`

### 2. Configuration
- [ ] Environment variables configured (see ENV_VARS_QUICK_REF.md)
- [ ] Model name specified: `MODEL_NAME` or default
- [ ] Device preference set: `DEVICE_PREFERENCE` (auto/cuda/mps/cpu)
- [ ] Concurrency limits configured: `MAX_PARALLEL_REQUESTS`, `MAX_QUEUE_SIZE`
- [ ] Batch size optimized for hardware: `BATCH_SIZE`
- [ ] Port configured (if not default 8000): `PORT`

### 3. Model Access
- [ ] Internet connection available for model download, OR
- [ ] Local model path configured: `LOCAL_MODEL_PATH`
- [ ] Model downloaded and accessible
- [ ] Sufficient disk space for model storage (~500MB+)

### 4. Hardware Validation
- [ ] CPU cores sufficient (2+ recommended)
- [ ] RAM sufficient (4GB+ for CPU, 8GB+ for GPU)
- [ ] GPU available (if using CUDA/MPS)
- [ ] GPU drivers installed (if using CUDA)
- [ ] Apple Silicon detected (for MPS/MLX)

### 5. Testing
- [ ] Test script runs successfully: `python test_multi_backend.py`
- [ ] Service starts: `./start_reranker.sh dev`
- [ ] Health endpoint accessible: `curl http://localhost:8000/health`
- [ ] Backend correctly detected (check health response)
- [ ] Basic rerank request works (see examples below)
- [ ] Performance acceptable (run performance_test.sh)

## Single Server Deployment

### Development Mode
```bash
# Start in development mode (auto-reload enabled)
./start_reranker.sh dev

# Verify
curl http://localhost:8000/health
```

- [ ] Service started successfully
- [ ] Logs show correct backend
- [ ] Health check returns 200 OK
- [ ] Test request succeeds

### Production Mode (Single Instance)
```bash
# Start as daemon
./start_reranker.sh daemon

# Check status
./manage_reranker.sh status

# Test
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

- [ ] Service running as daemon
- [ ] PID file created
- [ ] Logs being written
- [ ] Health check passes
- [ ] Metrics endpoint accessible
- [ ] No errors in logs

### Configuration Validation
```bash
# Check backend
curl -s http://localhost:8000/health | jq '.model.backend, .model.device'

# Check concurrency settings
curl -s http://localhost:8000/health | jq '.controller'

# Run load test
./performance_test.sh load 100 4

# Check metrics after load
curl -s http://localhost:8000/metrics | jq
```

- [ ] Correct backend in use (pytorch/mlx)
- [ ] Correct device in use (cuda/mps/cpu/mlx)
- [ ] Concurrency settings match configuration
- [ ] Load test completes successfully
- [ ] Latency acceptable (< 500ms p95)
- [ ] Success rate > 99%

## Multi-Server Deployment

### Server Instances
For each server instance:

```bash
# Server 1
PORT=8000 MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh daemon

# Server 2
PORT=8001 MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh daemon

# Server 3
PORT=8002 MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh daemon
```

- [ ] All server instances started
- [ ] Each on different port
- [ ] All health checks pass
- [ ] No port conflicts

### Load Balancer Setup

#### nginx Configuration
```nginx
upstream reranker_backend {
    least_conn;
    server localhost:8000 max_fails=3 fail_timeout=30s;
    server localhost:8001 max_fails=3 fail_timeout=30s;
    server localhost:8002 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://reranker_backend;
        proxy_next_upstream error timeout http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
    
    location /health {
        access_log off;
        proxy_pass http://reranker_backend;
    }
}
```

- [ ] Load balancer configured
- [ ] Health checks configured
- [ ] Timeouts set appropriately
- [ ] Upstream servers added
- [ ] Load balancer started
- [ ] Requests distributed across servers

### Validation
```bash
# Test each server directly
for port in 8000 8001 8002; do
    echo "Testing :$port"
    curl -s http://localhost:$port/health | jq -r '.status'
done

# Test through load balancer
curl -s http://localhost/health | jq

# Load test through load balancer
./performance_test.sh load 300 10

# Check metrics on all servers
for port in 8000 8001 8002; do
    echo "Server :$port metrics:"
    curl -s http://localhost:$port/metrics | jq '.total_requests, .success_rate'
done
```

- [ ] All servers responding
- [ ] Load balancer distributing requests
- [ ] No single point of failure
- [ ] Aggregate capacity correct (N × parallelism)
- [ ] Failover works (test by stopping one server)

## Apple Silicon Optimization

### MLX Installation
```bash
# Install MLX
pip install mlx mlx-lm

# Verify
python -c "import mlx.core; print('MLX available')"
```

- [ ] MLX installed successfully
- [ ] Import test passes
- [ ] No compatibility issues

### Optimized Configuration
```bash
# For M1/M2 (8-core GPU)
USE_MLX=true \
MAX_PARALLEL_REQUESTS=4 \
BATCH_SIZE=16 \
./start_reranker.sh daemon

# For M2 Max/M3 Max (16+ core GPU)
USE_MLX=true \
MAX_PARALLEL_REQUESTS=6 \
BATCH_SIZE=32 \
./start_reranker.sh daemon
```

- [ ] MLX backend enabled
- [ ] Batch size optimized
- [ ] Parallelism tuned

### Validation
```bash
# Check backend
curl -s http://localhost:8000/health | jq '.model.backend, .model.device'
# Should show: "mlx", "mlx"

# Performance test
./performance_test.sh throughput 200 8

# Compare with MPS
USE_MLX=false DEVICE_PREFERENCE=mps ./start_reranker.sh restart
./performance_test.sh throughput 200 8
```

- [ ] MLX backend active (not pytorch)
- [ ] Device shows "mlx"
- [ ] Performance better than MPS/CPU
- [ ] No memory issues
- [ ] No errors in logs

## Monitoring Setup

### Health Monitoring
```bash
# Continuous monitoring
watch -n 5 'curl -s http://localhost:8000/health | jq'

# Script for alerts
#!/bin/bash
STATUS=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$STATUS" != "healthy" ]; then
    echo "Alert: Service unhealthy!"
fi
```

- [ ] Health endpoint monitored
- [ ] Alerts configured for failures
- [ ] Monitoring frequency appropriate

### Metrics Collection
```bash
# Periodic metrics collection
*/5 * * * * curl -s http://localhost:8000/metrics >> /var/log/reranker-metrics.log

# Aggregate multi-server metrics
python3 aggregate_metrics.py
```

- [ ] Metrics being collected
- [ ] Log rotation configured
- [ ] Aggregation script working (multi-server)

### Log Management
```bash
# Check logs
./manage_reranker.sh tail

# Log rotation
# Add to /etc/logrotate.d/reranker
/path/to/reranker/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

- [ ] Logs being written
- [ ] Log location known
- [ ] Log rotation configured
- [ ] Disk space sufficient

## Performance Tuning

### Baseline Measurement
```bash
# Initial load test
./performance_test.sh load 100 4

# Record metrics
curl -s http://localhost:8000/metrics | jq > baseline_metrics.json
```

- [ ] Baseline established
- [ ] Latency recorded
- [ ] Throughput recorded
- [ ] Success rate recorded

### Tuning Steps
1. **Increase Parallelism**
   ```bash
   MAX_PARALLEL_REQUESTS=8 ./start_reranker.sh restart
   ./performance_test.sh load 100 8
   ```
   - [ ] Latency improved or stable
   - [ ] No memory issues

2. **Increase Batch Size**
   ```bash
   BATCH_SIZE=32 ./start_reranker.sh restart
   ./performance_test.sh throughput 200 8
   ```
   - [ ] Throughput improved
   - [ ] No OOM errors

3. **Enable Caching**
   ```bash
   ENABLE_PREDICTION_CACHE=true ./start_reranker.sh restart
   # Run same queries twice
   ```
   - [ ] Cache hit rate > 50%
   - [ ] Latency improved for cached requests

4. **Adjust Queue Size**
   ```bash
   MAX_QUEUE_SIZE=20 ./start_reranker.sh restart
   ./performance_test.sh stress 500 16
   ```
   - [ ] Fewer rejected requests
   - [ ] Wait time acceptable

### Final Validation
```bash
# Comprehensive test
./performance_test.sh load 500 10

# Metrics
curl -s http://localhost:8000/metrics | jq
```

- [ ] All tests pass
- [ ] Latency p95 < target
- [ ] Success rate > 99%
- [ ] Memory stable
- [ ] CPU utilization appropriate

## Production Readiness

### Service Management
- [ ] Start script works: `./start_reranker.sh daemon`
- [ ] Stop script works: `./manage_reranker.sh stop`
- [ ] Restart script works: `./manage_reranker.sh restart`
- [ ] Status check works: `./manage_reranker.sh status`
- [ ] Graceful shutdown works

### Systemd Integration (Optional)
```bash
# Create systemd service
sudo cp reranker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable reranker
sudo systemctl start reranker
sudo systemctl status reranker
```

- [ ] Systemd service created
- [ ] Service enabled (auto-start)
- [ ] Service running
- [ ] Logs in journalctl

### Backup & Recovery
- [ ] Model files backed up
- [ ] Configuration backed up
- [ ] Recovery procedure documented
- [ ] Tested recovery from backup

### Security
- [ ] Service not running as root
- [ ] Firewall configured (if needed)
- [ ] API authentication (if needed)
- [ ] HTTPS configured (if exposed externally)

### Documentation
- [ ] Deployment documented
- [ ] Configuration documented
- [ ] Monitoring documented
- [ ] Troubleshooting guide available
- [ ] Contact information for support

## Post-Deployment

### Smoke Tests
```bash
# Test all endpoints
curl -X POST http://localhost:8000/rerank \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "documents": ["doc1", "doc2"], "top_k": 1}'

curl -X POST http://localhost:8000/v1/rerank \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "documents": ["doc1", "doc2"], "top_n": 1}'

curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

- [ ] /rerank endpoint works
- [ ] /v1/rerank endpoint works
- [ ] /health endpoint works
- [ ] /metrics endpoint works

### Monitoring First 24 Hours
- [ ] Check logs every hour
- [ ] Monitor metrics every hour
- [ ] Check health status continuously
- [ ] Verify no errors or warnings
- [ ] Confirm performance stable

### Sign-Off
- [ ] Stakeholders notified
- [ ] Documentation delivered
- [ ] Support team briefed
- [ ] Monitoring confirmed working
- [ ] Production ready

## Rollback Plan

If issues occur:

1. **Stop service**
   ```bash
   ./manage_reranker.sh stop
   ```

2. **Check logs**
   ```bash
   ./manage_reranker.sh tail
   ```

3. **Restore previous version** (if upgraded)
   ```bash
   git checkout <previous-commit>
   ./start_reranker.sh daemon
   ```

4. **Restore configuration** (if changed)
   ```bash
   cp config.backup .env
   ./start_reranker.sh restart
   ```

- [ ] Rollback procedure tested
- [ ] Rollback time < 5 minutes
- [ ] Rollback documented

## Summary

### Deployment Type
- [ ] Single server - development
- [ ] Single server - production
- [ ] Multi-server - production
- [ ] Apple Silicon optimized

### Final Checklist
- [ ] All tests passed
- [ ] Performance acceptable
- [ ] Monitoring active
- [ ] Documentation complete
- [ ] Team trained
- [ ] Production ready

### Contact Information
- **Deployment Date**: _______________
- **Deployed By**: _______________
- **Support Contact**: _______________
- **Escalation Contact**: _______________

---

**Notes:**
- Keep this checklist for reference
- Update as configuration changes
- Review regularly for optimization opportunities
