# Advanced Features Quick Reference

## Installation

```bash
# Base installation
pip install -r requirements.txt

# Optional: Redis support
pip install redis

# Optional: 8-bit quantization (CUDA only)
pip install bitsandbytes

# Optional: Apple Silicon optimization
pip install mlx mlx-lm
```

## Quick Enable Commands

### Redis Distributed Cache
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Enable in reranker
REDIS_ENABLED=true ./start_reranker.sh daemon
```

### Micro-Batching
```bash
MICRO_BATCH_ENABLED=true ./start_reranker.sh daemon
```

### Quantization
```bash
# BF16 (recommended, no extra deps)
QUANTIZATION=bf16 ./start_reranker.sh daemon

# INT8 (requires bitsandbytes)
pip install bitsandbytes
QUANTIZATION=int8 ./start_reranker.sh daemon
```

### All Features (Production)
```bash
docker run -d -p 6379:6379 redis:7-alpine
pip install redis bitsandbytes

REDIS_ENABLED=true \
MICRO_BATCH_ENABLED=true \
QUANTIZATION=bf16 \
ENABLE_MIXED_PRECISION=true \
./start_reranker.sh daemon
```

## Environment Variables

| Feature | Variable | Default | Options |
|---------|----------|---------|---------|
| **Redis Cache** | `REDIS_ENABLED` | `false` | `true`/`false` |
| | `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| | `REDIS_TTL_SECONDS` | `600` | Seconds |
| **Micro-Batching** | `MICRO_BATCH_ENABLED` | `false` | `true`/`false` |
| | `MICRO_BATCH_WINDOW_MS` | `10.0` | Milliseconds |
| | `MICRO_BATCH_MAX_SIZE` | `32` | Integer |
| **Quantization** | `QUANTIZATION` | `none` | `none`/`bf16`/`int8` |

## Monitoring

```bash
# Check all features
curl -s http://localhost:8000/health | jq

# Redis cache stats
curl -s http://localhost:8000/health | jq '.distributed_cache'

# Micro-batching stats
curl -s http://localhost:8000/health | jq '.micro_batcher'

# Quantization mode
curl -s http://localhost:8000/health | jq '.model.quantization'
```

## Performance Expectations

| Feature | Throughput | Latency | Memory | Setup |
|---------|------------|---------|--------|-------|
| Redis Cache | +50-200% | -80% | +50MB | Medium |
| Micro-Batching | +30-50% | +10-20ms | +10MB | Easy |
| BF16 | +20-50% | -30% | -50% | Easy |
| INT8 | +50-100% | -40% | -75% | Medium |
| **All Combined** | **+200-300%** | **~+10ms** | **-50%** | **Medium** |

## When to Use What

### Redis Cache
✅ **Use if:**
- Multiple servers (2+)
- Repeated queries
- Want request deduplication

❌ **Skip if:**
- Single server only
- Unique queries per request
- Ultra-low latency critical

### Micro-Batching
✅ **Use if:**
- High QPS (>10 req/s)
- Bursty traffic
- GPU inference
- Can tolerate +10ms latency

❌ **Skip if:**
- Low QPS (<5 req/s)
- CPU-only inference
- Need <10ms p99 latency

### Quantization
✅ **BF16 recommended for:**
- CUDA GPUs
- Production deployments
- Memory-constrained systems

✅ **INT8 recommended for:**
- Very limited GPU memory
- Large models
- Can tolerate 1-2% accuracy loss

❌ **Skip if:**
- CPU-only (limited benefit)
- Small models (<500MB)
- Maximum accuracy critical

## Troubleshooting

### Redis Not Working
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check connection
curl -s http://localhost:8000/health | jq '.distributed_cache.connected'
# Should be true
```

### Micro-Batching Not Helping
```bash
# Check average batch size
curl -s http://localhost:8000/health | jq '.micro_batcher.avg_batch_size'

# If < 2: QPS too low or window too short
# Solution: Increase MICRO_BATCH_WINDOW_MS or disable
```

### Quantization Issues
```bash
# Check mode is active
curl -s http://localhost:8000/health | jq '.model.quantization'

# INT8 not loading:
pip list | grep bitsandbytes  # Should show version
python -c "import torch; print(torch.cuda.is_available())"  # Should be True
```

## Configuration Presets

### Development
```bash
# Basic setup for testing
./start_reranker.sh dev
```

### Single Server Production
```bash
QUANTIZATION=bf16
ENABLE_MIXED_PRECISION=true
MAX_PARALLEL_REQUESTS=4
./start_reranker.sh daemon
```

### Multi-Server Production (2-3 servers)
```bash
REDIS_ENABLED=true
QUANTIZATION=bf16
ENABLE_MIXED_PRECISION=true
MAX_PARALLEL_REQUESTS=4
./start_reranker.sh daemon
```

### High-Traffic Production (5+ servers)
```bash
REDIS_ENABLED=true
REDIS_TTL_SECONDS=600
MICRO_BATCH_ENABLED=true
MICRO_BATCH_WINDOW_MS=10.0
MICRO_BATCH_MAX_SIZE=32
QUANTIZATION=bf16
ENABLE_MIXED_PRECISION=true
MAX_PARALLEL_REQUESTS=8
BATCH_SIZE=32
./start_reranker.sh daemon
```

## Testing Commands

```bash
# Basic test
curl -X POST http://localhost:8000/rerank \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "documents": ["doc1", "doc2"], "top_k": 1}'

# Load test
./performance_test.sh load 100 4

# Check metrics
curl http://localhost:8000/metrics | jq

# Health check
curl http://localhost:8000/health | jq
```

## Decision Matrix

**Choose your setup based on:**

| Scenario | Redis | Micro-Batch | Quantization |
|----------|-------|-------------|--------------|
| Single server, low traffic | ❌ | ❌ | BF16 |
| Single server, high traffic | ❌ | ✅ | BF16 |
| 2-3 servers | ✅ | ⚠️ | BF16 |
| 5+ servers | ✅ | ✅ | BF16 |
| Limited GPU memory | ⚠️ | ❌ | INT8 |
| Maximum throughput | ✅ | ✅ | BF16 |

Legend: ✅ Recommended | ⚠️ Optional | ❌ Not needed

## Documentation Links

- **Full Guide**: [docs/ADVANCED_FEATURES.md](ADVANCED_FEATURES.md)
- **Implementation Details**: [docs/ADVANCED_IMPLEMENTATION.md](ADVANCED_IMPLEMENTATION.md)
- **All Environment Variables**: [docs/ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md)
- **Multi-Server Setup**: [docs/MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md)

## Summary

Three optional features, all production-ready:
- **Redis Cache** - Multi-server coordination (2-3× throughput)
- **Micro-Batching** - GPU efficiency (+30-50% throughput)
- **Quantization** - Memory optimization (50-75% reduction)

All features:
- Disabled by default
- No breaking changes
- Graceful fallbacks
- Well documented
- Fully monitored

Enable what you need, when you need it. Start simple, optimize as needed.
