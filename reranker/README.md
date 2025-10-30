# Reranker Service

A production-ready reranking service powered by HuggingFace Transformers with support for PyTorch (CUDA/MPS/CPU) and MLX (Apple Silicon optimization).

## Features

- ✅ **Multiple Backend Support**: Automatic selection of PyTorch or MLX based on hardware
- ✅ **API Compatibility**: Cohere and Jina reranker API compatible
- ✅ **Concurrency Control**: Advanced queue management with configurable parallelism
- ✅ **Performance Optimization**: Batching, caching, and memory management
- ✅ **Apple Silicon Support**: Native MPS and optional MLX acceleration for M-series Macs
- ✅ **Production Ready**: Health checks, metrics, daemon mode, graceful shutdown
- ✅ **Multi-Server Deployment**: Horizontal scaling with load balancer support
- ✅ **Redis Distributed Cache**: Share cache across servers with request deduplication
- ✅ **Micro-Batching**: Improve GPU utilization during bursty traffic
- ✅ **Model Quantization**: 8-bit and BF16 support for memory optimization

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: For Apple Silicon optimization
pip install mlx mlx-lm
```

### Run the Service

```bash
# Development mode (with auto-reload)
./start_reranker.sh dev

# Production mode (daemon)
./start_reranker.sh daemon

# Foreground mode
./start_reranker.sh fg
```

### Test the API

```bash
# Native reranker endpoint
curl -X POST http://localhost:8000/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "documents": [
      "Machine learning is a subset of AI",
      "Python is a programming language",
      "Deep learning uses neural networks"
    ],
    "top_k": 2
  }'

# Cohere-compatible endpoint
curl -X POST http://localhost:8000/v1/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "documents": [
      "Machine learning is a subset of AI",
      "Python is a programming language",
      "Deep learning uses neural networks"
    ],
    "top_n": 2,
    "model": "rerank-english-v2.0"
  }'
```

## Configuration

Configure via environment variables:

```bash
# Model Configuration
MODEL_NAME=BAAI/bge-reranker-base      # HuggingFace model name
LOCAL_MODEL_PATH=/path/to/model         # Local model fallback
MAX_LENGTH=512                          # Max token length
QUANTIZATION=none                       # none, int8, bf16

# Backend Selection
USE_MLX=true                            # Enable MLX (auto-detected on Apple Silicon)
DEVICE_PREFERENCE=auto                  # auto, cuda, mps, cpu

# Concurrency Control
MAX_PARALLEL_REQUESTS=4                 # Max concurrent inference
MAX_QUEUE_SIZE=10                       # Queue capacity
QUEUE_TIMEOUT_SECONDS=30                # Max wait time

# Batch Processing
BATCH_SIZE=16                           # Documents per batch

# Worker Configuration
WORKER_TIMEOUT=120                      # Request timeout
MAX_RETRIES=3                           # Retry attempts

# Caching
ENABLE_PREDICTION_CACHE=true            # Enable result cache
CACHE_TTL_SECONDS=300                   # Cache expiration
CLEAR_CACHE_INTERVAL=3600               # Periodic cleanup

# Performance Optimizations
ENABLE_TORCH_COMPILE=false              # torch.compile on CUDA
ENABLE_MIXED_PRECISION=false            # float16 autocast
WARMUP_ON_START=true                    # Reduce cold start

# Advanced Features (Optional)
REDIS_ENABLED=false                     # Distributed cache
REDIS_URL=redis://localhost:6379/0      # Redis connection
MICRO_BATCH_ENABLED=false               # GPU micro-batching
MICRO_BATCH_WINDOW_MS=10.0              # Batch collection window

# Server Configuration
HOST=0.0.0.0                            # Bind address
PORT=8000                               # Server port
LOG_LEVEL=INFO                          # Logging level
```

## Service Management

```bash
# Start service
./manage_reranker.sh start

# Stop service
./manage_reranker.sh stop

# Restart service
./manage_reranker.sh restart

# Check status
./manage_reranker.sh status

# View logs
./manage_reranker.sh tail
```

## Performance Testing

```bash
# Load test (100 requests, 4 concurrent)
./performance_test.sh load 100 4

# Latency test
./performance_test.sh latency 50

# Throughput test
./performance_test.sh throughput 200 8

# Stress test
./performance_test.sh stress 500 16
```

## API Endpoints

### POST /rerank

Native reranking endpoint.

**Request:**
```json
{
  "query": "string",
  "documents": ["string"],
  "top_k": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "index": 0,
      "document": "string",
      "score": 0.95
    }
  ],
  "processing_time_ms": 156.3
}
```

### POST /v1/rerank

Cohere/Jina compatible endpoint.

**Request:**
```json
{
  "query": "string",
  "documents": ["string"],
  "top_n": 10,
  "model": "optional",
  "return_documents": true
}
```

**Response:**
```json
{
  "id": "unique-id",
  "results": [
    {
      "index": 0,
      "relevance_score": 0.95,
      "document": {
        "text": "string"
      }
    }
  ],
  "meta": {
    "api_version": {"version": "1.0.0"}
  }
}
```

### GET /health

Health check with service statistics.

**Response:**
```json
{
  "status": "healthy",
  "controller": {
    "waiting": 0,
    "active": 2,
    "available_slots": 2,
    "max_parallel": 4,
    "max_queue": 10
  },
  "model": {
    "backend": "pytorch",
    "source": "remote:BAAI/bge-reranker-base",
    "device": "cuda:0",
    "cache_enabled": true,
    "cache_size": 42
  }
}
```

### GET /metrics

Detailed performance metrics.

**Response:**
```json
{
  "total_requests": 1247,
  "successful_requests": 1235,
  "failed_requests": 12,
  "success_rate": 0.990,
  "avg_wait_time_ms": 45.3,
  "avg_process_time_ms": 167.8,
  "p50_wait_time_ms": 12.5,
  "p95_wait_time_ms": 156.7,
  "p99_wait_time_ms": 234.2
}
```

## Advanced Usage

### Multi-Server Deployment

Deploy multiple instances behind a load balancer:

```bash
# Server 1
PORT=8000 MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh daemon

# Server 2
PORT=8001 MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh daemon

# Server 3
PORT=8002 MAX_PARALLEL_REQUESTS=4 ./start_reranker.sh daemon
```

See [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md) for detailed configuration.

### Apple Silicon Optimization

For M1/M2/M3 Macs, install MLX for best performance:

```bash
pip install mlx mlx-lm
USE_MLX=true BATCH_SIZE=32 ./start_reranker.sh daemon
```

**Performance Comparison (M2 Max):**
- CPU: ~12 doc/s
- MPS: ~45 doc/s
- MLX: ~78 doc/s

### Local Model Loading

For offline or air-gapped environments:

```bash
# Download model first
python -c "from transformers import AutoModel; AutoModel.from_pretrained('BAAI/bge-reranker-base')"

# Configure local path
LOCAL_MODEL_PATH=/path/to/model ./start_reranker.sh daemon
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Application                │
├─────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Routes    │  │   Service    │  │  Unified   │  │
│  │            │  │              │  │  Reranker  │  │
│  │ /rerank    │→ │ Queue Mgmt   │→ │            │  │
│  │ /v1/rerank │  │ Concurrency  │  │ ┌────────┐ │  │
│  │ /health    │  │ Metrics      │  │ │PyTorch │ │  │
│  │ /metrics   │  │              │  │ │  or    │ │  │
│  └────────────┘  └──────────────┘  │ │  MLX   │ │  │
│                                     │ └────────┘ │  │
└─────────────────────────────────────┴────────────┴──┘
```

**Key Components:**

- **routes.py**: FastAPI endpoints and request/response handling
- **service.py**: Business logic, concurrency control, metrics
- **unified_reranker.py**: Multi-backend model wrapper (PyTorch/MLX)
- **enhanced_concurrency.py**: Advanced queue and semaphore management
- **config.py**: Centralized configuration from environment variables
- **schemas.py**: Pydantic models for validation
- **normalization.py**: Document preprocessing utilities

## Documentation

- [MULTI_SERVER_APPLE_SILICON.md](docs/MULTI_SERVER_APPLE_SILICON.md) - Multi-server deployment and Apple Silicon optimization guide
- [PERFORMANCE_OPTIMIZATION.md](docs/PERFORMANCE_OPTIMIZATION.md) - Detailed performance tuning guide
- [ADVANCED_FEATURES.md](docs/ADVANCED_FEATURES.md) - Redis cache, micro-batching, and quantization guide
- [ENV_VARS_QUICK_REF.md](docs/ENV_VARS_QUICK_REF.md) - Complete environment variables reference

## Troubleshooting

### Service won't start

```bash
# Check Python environment
which python
python --version

# Check dependencies
pip list | grep -E "fastapi|transformers|torch"

# Check port availability
lsof -i :8000
```

### High latency

```bash
# Check health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics

# Tune concurrency
MAX_PARALLEL_REQUESTS=8 ./start_reranker.sh restart
```

### Memory issues

```bash
# Reduce batch size
BATCH_SIZE=8 ./start_reranker.sh restart

# Disable cache
ENABLE_PREDICTION_CACHE=false ./start_reranker.sh restart

# Reduce parallelism
MAX_PARALLEL_REQUESTS=2 ./start_reranker.sh restart
```

### Apple Silicon not using GPU

```bash
# Check device
curl http://localhost:8000/health | jq '.model.device'

# Should show "mps" or "mlx", not "cpu"

# Check PyTorch MPS availability
python -c "import torch; print(torch.backends.mps.is_available())"

# For MLX
python -c "import mlx.core; print('MLX available')"
```

## Development

### Project Structure

```
reranker/
├── __init__.py                    # Package initialization
├── config.py                      # Configuration management
├── schemas.py                     # Pydantic models
├── unified_reranker.py            # Multi-backend reranker
├── enhanced_concurrency.py        # Concurrency controller
├── service.py                     # Core service logic
├── routes.py                      # FastAPI routes
├── app.py                         # Application factory
├── normalization.py               # Utilities
├── index.py                       # Entry point
├── requirements.txt               # Dependencies
├── start_reranker.sh             # Startup script
├── manage_reranker.sh            # Service management
└── performance_test.sh           # Performance testing
```

### Running Tests

```bash
# Unit tests (if available)
pytest tests/

# Integration tests
./performance_test.sh load 10 2

# Manual testing
python -c "
from reranker.unified_reranker import UnifiedReRanker
from reranker.config import RerankerConfig

config = RerankerConfig.from_env()
reranker = UnifiedReRanker(config)
results = reranker.rerank('test query', ['doc1', 'doc2'])
print(results)
"
```

### Adding New Features

1. Update `config.py` for new settings
2. Implement in appropriate module (service, routes, reranker)
3. Update schemas if needed
4. Test locally
5. Update documentation

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions:
- Check [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md) and [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
- Open an issue on GitHub
- Contact [Your Contact Info]
