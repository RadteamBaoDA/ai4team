# Environment Variables Quick Reference

## Backend & Device Selection

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `USE_MLX` | `auto-detect` | `true`, `false` | Enable MLX backend for Apple Silicon |
| `DEVICE_PREFERENCE` | `auto` | `auto`, `cuda`, `mps`, `cpu` | PyTorch device preference |

**Examples:**
```bash
# Force CPU (testing/debugging)
DEVICE_PREFERENCE=cpu ./start_reranker.sh dev

# Use CUDA GPU
DEVICE_PREFERENCE=cuda ./start_reranker.sh daemon

# Apple Silicon with MLX
USE_MLX=true ./start_reranker.sh daemon

# Apple Silicon with MPS (no MLX)
USE_MLX=false DEVICE_PREFERENCE=mps ./start_reranker.sh daemon
```

## Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `BAAI/bge-reranker-base` | HuggingFace model identifier |
| `LOCAL_MODEL_PATH` | `None` | Path to local model directory (fallback) |
| `MAX_LENGTH` | `512` | Maximum token length for inputs |

**Examples:**
```bash
# Use different model
MODEL_NAME=BAAI/bge-reranker-large ./start_reranker.sh daemon

# Use local model (offline mode)
LOCAL_MODEL_PATH=/data/models/bge-reranker ./start_reranker.sh daemon

# Adjust token limit
MAX_LENGTH=256 ./start_reranker.sh daemon
```

## Concurrency Control

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `MAX_PARALLEL_REQUESTS` | `4` | 1-32 | Max concurrent inference operations |
| `MAX_QUEUE_SIZE` | `10` | 0-100 | Queue capacity for waiting requests |
| `QUEUE_TIMEOUT_SECONDS` | `30` | 5-300 | Max wait time before rejection |

**Tuning Guide:**

**Low Memory (< 8GB RAM):**
```bash
MAX_PARALLEL_REQUESTS=2
MAX_QUEUE_SIZE=5
QUEUE_TIMEOUT_SECONDS=20
```

**Balanced (8-16GB RAM):**
```bash
MAX_PARALLEL_REQUESTS=4
MAX_QUEUE_SIZE=10
QUEUE_TIMEOUT_SECONDS=30
```

**High Performance (> 16GB RAM + GPU):**
```bash
MAX_PARALLEL_REQUESTS=8
MAX_QUEUE_SIZE=20
QUEUE_TIMEOUT_SECONDS=60
```

**Multi-User Concurrent (Multi-Server):**
```bash
# Per server: conservative settings
MAX_PARALLEL_REQUESTS=4
MAX_QUEUE_SIZE=15
QUEUE_TIMEOUT_SECONDS=45

# Scale with multiple instances:
# 3 servers × 4 parallel = 12 total concurrent
```

## Batch Processing

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `BATCH_SIZE` | `16` | 4-64 | Documents processed per batch |

**Hardware-Specific:**

**CPU Only:**
```bash
BATCH_SIZE=8    # Lower for CPU efficiency
```

**CUDA GPU:**
```bash
BATCH_SIZE=32   # Leverage parallel processing
```

**Apple Silicon MPS:**
```bash
BATCH_SIZE=16   # Balanced for unified memory
```

**Apple Silicon MLX:**
```bash
BATCH_SIZE=32   # MLX efficient with larger batches
```

## Worker Configuration

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `WORKER_TIMEOUT` | `120` | 30-600 | Request processing timeout (seconds) |
| `MAX_RETRIES` | `3` | 0-10 | Retry attempts for failed requests |

**Examples:**
```bash
# Short timeout for low latency
WORKER_TIMEOUT=60 MAX_RETRIES=2

# Long timeout for large documents
WORKER_TIMEOUT=300 MAX_RETRIES=3

# No retries (fail fast)
MAX_RETRIES=0
```

## Caching

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `ENABLE_PREDICTION_CACHE` | `true` | `true`, `false` | Enable result caching |
| `CACHE_TTL_SECONDS` | `300` | 60-3600 | Cache entry expiration |
| `CLEAR_CACHE_INTERVAL` | `3600` | 600-7200 | Periodic cache cleanup interval |

**Use Cases:**

**High Cache Hit (Recommended):**
```bash
# Repeated queries, limited corpus
ENABLE_PREDICTION_CACHE=true
CACHE_TTL_SECONDS=600          # 10 minutes
CLEAR_CACHE_INTERVAL=1800      # 30 minutes
```

**Low Cache Hit:**
```bash
# Unique queries, constantly changing docs
ENABLE_PREDICTION_CACHE=false
```

**Memory Constrained:**
```bash
# Short TTL to limit memory usage
ENABLE_PREDICTION_CACHE=true
CACHE_TTL_SECONDS=180          # 3 minutes
CLEAR_CACHE_INTERVAL=600       # 10 minutes
```

## PyTorch Optimizations

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `ENABLE_TORCH_COMPILE` | `false` | `true`, `false` | Enable torch.compile (PyTorch 2.0+) |
| `ENABLE_MIXED_PRECISION` | `false` | `true`, `false` | Use float16 autocast on CUDA for faster inference |
| `WARMUP_ON_START` | `true` | `true`, `false` | Run a tiny forward pass at startup to reduce first-request latency |
| `QUANTIZATION` | `none` | `none`, `int8`, `bf16` | Model quantization for memory/speed |

**CUDA Optimization:**
```bash
# Only for CUDA GPUs (experimental on MPS)
ENABLE_TORCH_COMPILE=true

# Faster inference with minimal accuracy impact
ENABLE_MIXED_PRECISION=true

# 8-bit quantization (requires bitsandbytes)
QUANTIZATION=int8

# BF16 precision (faster, uses less memory)
QUANTIZATION=bf16
```

## Distributed Cache (Redis)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_ENABLED` | `false` | Enable Redis distributed cache |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_TTL_SECONDS` | `600` | Cache entry expiration (10 minutes) |

**Multi-Server with Redis:**
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Enable on all servers
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
./start_reranker.sh daemon
```

**Benefits:**
- Shared cache across all servers
- Request deduplication (same query processed once)
- Reduced redundant computation
- Lower aggregate load

## Micro-Batching

| Variable | Default | Description |
|----------|---------|-------------|
| `MICRO_BATCH_ENABLED` | `false` | Enable micro-batching for bursty traffic |
| `MICRO_BATCH_WINDOW_MS` | `10.0` | Max wait time to collect requests (ms) |
| `MICRO_BATCH_MAX_SIZE` | `32` | Maximum requests per batch |

**High QPS / Bursty Traffic:**
```bash
# Enable micro-batching for GPU efficiency
MICRO_BATCH_ENABLED=true
MICRO_BATCH_WINDOW_MS=10.0
MICRO_BATCH_MAX_SIZE=32
```

**How it works:**
- Collects concurrent requests within time window
- Processes identical requests once (deduplication)
- Reduces GPU kernel launch overhead
- Higher throughput during traffic spikes

## Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

**Examples:**
```bash
# Development with debug logging
LOG_LEVEL=DEBUG HOST=127.0.0.1 PORT=8000 ./start_reranker.sh dev

# Production on different port
PORT=9000 ./start_reranker.sh daemon

# Verbose logging
LOG_LEVEL=DEBUG ./start_reranker.sh fg
```

## Distributed Mode (Future)

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `ENABLE_DISTRIBUTED` | `false` | `true`, `false` | Enable multi-server coordination |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL | Shared state backend |

**Coming Soon:**
```bash
# Distributed deployment with Redis
ENABLE_DISTRIBUTED=true
REDIS_URL=redis://cache-server:6379
./start_reranker.sh daemon
```

## Complete Configuration Examples

### Development Setup

```bash
# Minimal for local testing
LOG_LEVEL=DEBUG \
HOST=127.0.0.1 \
PORT=8000 \
MAX_PARALLEL_REQUESTS=2 \
BATCH_SIZE=8 \
ENABLE_PREDICTION_CACHE=false \
./start_reranker.sh dev
```

### Production - Single Server

```bash
# Balanced production settings
MODEL_NAME=BAAI/bge-reranker-base \
DEVICE_PREFERENCE=auto \
MAX_PARALLEL_REQUESTS=4 \
MAX_QUEUE_SIZE=10 \
QUEUE_TIMEOUT_SECONDS=30 \
BATCH_SIZE=16 \
WORKER_TIMEOUT=120 \
MAX_RETRIES=3 \
ENABLE_PREDICTION_CACHE=true \
CACHE_TTL_SECONDS=300 \
CLEAR_CACHE_INTERVAL=3600 \
HOST=0.0.0.0 \
PORT=8000 \
LOG_LEVEL=INFO \
./start_reranker.sh daemon
```

### Production - Multi-Server Deployment

```bash
# Server 1 (port 8000)
PORT=8000 \
MAX_PARALLEL_REQUESTS=4 \
MAX_QUEUE_SIZE=15 \
BATCH_SIZE=16 \
./start_reranker.sh daemon

# Server 2 (port 8001)
PORT=8001 \
MAX_PARALLEL_REQUESTS=4 \
MAX_QUEUE_SIZE=15 \
BATCH_SIZE=16 \
./start_reranker.sh daemon

# Server 3 (port 8002)
PORT=8002 \
MAX_PARALLEL_REQUESTS=4 \
MAX_QUEUE_SIZE=15 \
BATCH_SIZE=16 \
./start_reranker.sh daemon

# Total capacity: 3 × 4 = 12 concurrent requests
```

### Apple Silicon M1/M2 (8-core GPU)

```bash
# Optimized for M1/M2
USE_MLX=true \
DEVICE_PREFERENCE=auto \
MAX_PARALLEL_REQUESTS=4 \
BATCH_SIZE=16 \
ENABLE_PREDICTION_CACHE=true \
./start_reranker.sh daemon
```

### Apple Silicon M2 Max/M3 Max (16+ core GPU)

```bash
# Optimized for high-end Apple Silicon
USE_MLX=true \
DEVICE_PREFERENCE=auto \
MAX_PARALLEL_REQUESTS=6 \
BATCH_SIZE=32 \
MAX_QUEUE_SIZE=15 \
ENABLE_PREDICTION_CACHE=true \
./start_reranker.sh daemon
```

### High-Throughput CUDA GPU

```bash
# Optimized for NVIDIA GPU
DEVICE_PREFERENCE=cuda \
MAX_PARALLEL_REQUESTS=8 \
BATCH_SIZE=32 \
MAX_QUEUE_SIZE=20 \
QUEUE_TIMEOUT_SECONDS=60 \
ENABLE_TORCH_COMPILE=true \
ENABLE_PREDICTION_CACHE=true \
./start_reranker.sh daemon
```

### Memory-Constrained Environment

```bash
# Minimal memory usage
DEVICE_PREFERENCE=cpu \
MAX_PARALLEL_REQUESTS=2 \
BATCH_SIZE=8 \
MAX_QUEUE_SIZE=5 \
ENABLE_PREDICTION_CACHE=false \
./start_reranker.sh daemon
```

### Offline/Air-Gapped Deployment

```bash
# Use local model, no internet
LOCAL_MODEL_PATH=/opt/models/bge-reranker-base \
DEVICE_PREFERENCE=cpu \
MAX_PARALLEL_REQUESTS=2 \
./start_reranker.sh daemon
```

## Monitoring Variables in Scripts

Check current configuration:

```bash
# Show all reranker-related variables
env | grep -E "MODEL_|MAX_|DEVICE|BATCH|CACHE|HOST|PORT|LOG"

# Show specific variable
echo $MAX_PARALLEL_REQUESTS

# Show health with config
curl -s http://localhost:8000/health | jq
```

## Performance Tuning Workflow

1. **Start Conservative:**
   ```bash
   MAX_PARALLEL_REQUESTS=2 BATCH_SIZE=8 ./start_reranker.sh daemon
   ```

2. **Monitor Metrics:**
   ```bash
   watch -n 5 'curl -s http://localhost:8000/metrics | jq'
   ```

3. **Run Load Test:**
   ```bash
   ./performance_test.sh load 100 4
   ```

4. **Adjust Based on Results:**
   - High wait times → increase `MAX_PARALLEL_REQUESTS`
   - Memory errors → decrease `BATCH_SIZE`
   - Queue rejections → increase `MAX_QUEUE_SIZE`
   - Cache misses → adjust `CACHE_TTL_SECONDS`

5. **Repeat Until Optimal:**
   ```bash
   # Gradually increase parallelism
   MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh restart
   ./performance_test.sh load 200 8
   
   MAX_PARALLEL_REQUESTS=8 ./start_reranker.sh restart
   ./performance_test.sh load 300 12
   ```

## Validation Checklist

Before deploying to production:

- [ ] Model loads successfully (check logs or `/health`)
- [ ] Correct device selected (CUDA/MPS/MLX/CPU via `/health`)
- [ ] Cache enabled if desired (check `/health`)
- [ ] Load test passes at expected concurrency
- [ ] Latency meets requirements (check `/metrics`)
- [ ] Memory usage stable under load (monitor system)
- [ ] Service survives restarts (test `manage_reranker.sh restart`)
- [ ] Health endpoint accessible from load balancer
- [ ] Logs properly rotated (check log files)

## Common Issues & Solutions

**Issue:** Service using CPU despite GPU available

**Solution:**
```bash
# Check device detection
curl http://localhost:8000/health | jq '.model.device'

# Force CUDA
DEVICE_PREFERENCE=cuda ./start_reranker.sh restart

# For Apple Silicon, install MLX
pip install mlx mlx-lm
USE_MLX=true ./start_reranker.sh restart
```

**Issue:** High queue wait times

**Solution:**
```bash
# Increase parallel capacity
MAX_PARALLEL_REQUESTS=8 ./start_reranker.sh restart

# Or deploy more servers
PORT=8001 ./start_reranker.sh daemon
PORT=8002 ./start_reranker.sh daemon
```

**Issue:** Out of memory errors

**Solution:**
```bash
# Reduce batch size
BATCH_SIZE=8 ./start_reranker.sh restart

# Reduce parallelism
MAX_PARALLEL_REQUESTS=2 ./start_reranker.sh restart

# Disable cache
ENABLE_PREDICTION_CACHE=false ./start_reranker.sh restart
```

## Quick Reference Card

```
┌────────────────────────────────────────────────────────┐
│              RERANKER QUICK REFERENCE                  │
├────────────────────────────────────────────────────────┤
│ Start:    ./start_reranker.sh daemon                  │
│ Stop:     ./manage_reranker.sh stop                   │
│ Status:   ./manage_reranker.sh status                 │
│ Health:   curl localhost:8000/health                  │
│ Metrics:  curl localhost:8000/metrics                 │
├────────────────────────────────────────────────────────┤
│ Key Variables:                                         │
│   MAX_PARALLEL_REQUESTS=4    # Concurrency            │
│   BATCH_SIZE=16              # Batch size             │
│   USE_MLX=true               # Apple Silicon          │
│   DEVICE_PREFERENCE=auto     # Device selection       │
│   ENABLE_PREDICTION_CACHE=true # Caching             │
├────────────────────────────────────────────────────────┤
│ Test:     ./performance_test.sh load 100 4            │
│ Logs:     ./manage_reranker.sh tail                   │
└────────────────────────────────────────────────────────┘
```
