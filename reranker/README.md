# Reranker Service

A production-ready reranking service powered by HuggingFace Transformers with an **optimized Python package structure** following best practices. Supports PyTorch (CUDA/MPS/CPU) and MLX (Apple Silicon optimization).

## Features

- ✅ **Professional Package Structure**: Organized src-layout following Python best practices
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
- ✅ **Modern Packaging**: Both setup.py and pyproject.toml support
- ✅ **Comprehensive Testing**: Unit and integration test structure

## 📁 **Package Structure**

```
reranker/
├── 📁 src/reranker/              # Main package source
│   ├── __init__.py               # Package entry point
│   ├── __main__.py               # Module execution entry
│   ├── 📁 api/                   # FastAPI application layer
│   │   ├── app.py                # FastAPI app factory
│   │   └── routes.py             # API route definitions
│   ├── 📁 core/                  # Core business logic
│   │   ├── config.py             # Configuration management
│   │   ├── concurrency.py        # Concurrency control
│   │   └── unified_reranker.py   # Multi-backend reranker
│   ├── 📁 models/                # Data models and schemas
│   │   └── schemas.py            # Pydantic models
│   ├── 📁 services/              # Business logic services
│   │   └── reranker_service.py   # Service orchestration
│   └── 📁 utils/                 # Utility functions
│       ├── distributed_cache.py  # Redis caching
│       ├── micro_batcher.py      # Batch processing
│       └── normalization.py     # Text preprocessing
├── 📁 tests/                     # Test suite
│   ├── conftest.py               # Test configuration
│   ├── 📁 unit/                  # Unit tests
│   └── 📁 integration/           # Integration tests
├── 📁 scripts/                   # Shell scripts and utilities
├── 📁 config/                    # Environment configurations
├── 📁 docs/                      # Documentation
├── main.py                       # Main entry point
├── pyproject.toml                # Modern Python packaging
└── requirements.txt              # Dependencies
```

## Quick Start

### Installation

```bash
# Method 1: Development installation
pip install -e .

# Method 2: With optional dependencies
pip install -e ".[mlx,redis,monitoring]"

# Method 3: All features
pip install -e ".[all]"

# Method 4: From requirements file
pip install -r requirements.txt
```

### Run the Service

```bash
# Method 1: Using main entry point
python main.py

# Method 2: Using package module
python -m reranker

# Method 3: Using console script (after installation)
reranker

# Method 4: Development with environment config
source config/development.env
python main.py

# Method 5: Production with environment config
source config/production.env
python main.py

# Method 6: Using management scripts
./scripts/start_reranker.sh dev       # Development mode
./scripts/start_reranker.sh daemon    # Production daemon
./scripts/start_reranker.sh fg        # Foreground mode
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

### Environment-Based Configuration

The service uses environment-specific configuration files:

```bash
# Development configuration
source config/development.env
python main.py

# Production configuration
source config/production.env
python main.py

# Apple Silicon optimized configuration
source config/apple_silicon.env
python main.py
```

### Available Environment Variables

```bash
# Model Configuration
RERANKER_MODEL=BAAI/bge-reranker-base   # HuggingFace model name
RERANKER_LOCAL_MODEL_PATH=/path/to/model # Local model fallback
RERANKER_MAX_LENGTH=512                 # Max token length
RERANKER_QUANTIZATION=none              # none, int8, bf16

# Backend Selection
RERANKER_USE_MLX=true                   # Enable MLX (auto-detected on Apple Silicon)
RERANKER_DEVICE=auto                    # auto, cuda, mps, cpu, mlx

# Concurrency Control
RERANKER_MAX_PARALLEL=4                 # Max concurrent inference
RERANKER_MAX_QUEUE=10                   # Queue capacity
RERANKER_QUEUE_TIMEOUT=30               # Max wait time

# Batch Processing
RERANKER_BATCH_SIZE=16                  # Documents per batch

# Worker Configuration
RERANKER_WORKER_TIMEOUT=120             # Request timeout
RERANKER_MAX_RETRIES=3                  # Retry attempts

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
./scripts/manage_reranker.sh start

# Stop service
./scripts/manage_reranker.sh stop

# Restart service
./scripts/manage_reranker.sh restart

# Check status
./scripts/manage_reranker.sh status

# View logs
./scripts/manage_reranker.sh tail
```

## Performance Testing

```bash
# Load test (100 requests, 4 concurrent)
./scripts/performance_test.sh load 100 4

# Latency test
./scripts/performance_test.sh latency 50

# Throughput test
./scripts/performance_test.sh throughput 200 8

# Stress test
./scripts/performance_test.sh stress 500 16
```

## Testing

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Test package structure
python test_structure.py

# Run with coverage
pytest --cov=reranker --cov-report=html
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
PORT=8000 RERANKER_MAX_PARALLEL=4 ./scripts/start_reranker.sh daemon

# Server 2
PORT=8001 RERANKER_MAX_PARALLEL=4 ./scripts/start_reranker.sh daemon

# Server 3
PORT=8002 RERANKER_MAX_PARALLEL=4 ./scripts/start_reranker.sh daemon
```

See [MULTI_SERVER_APPLE_SILICON.md](docs/MULTI_SERVER_APPLE_SILICON.md) for detailed configuration.

### Apple Silicon Optimization

For M1/M2/M3 Macs, install MLX for best performance:

```bash
# Install MLX dependencies
pip install -e ".[mlx]"

# Use Apple Silicon configuration
source config/apple_silicon.env
python main.py

# Or use environment variables directly
RERANKER_USE_MLX=true RERANKER_BATCH_SIZE=32 ./scripts/start_reranker.sh daemon
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
RERANKER_LOCAL_MODEL_PATH=/path/to/model ./scripts/start_reranker.sh daemon
```

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Application                │
├─────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  API       │  │   Services   │  │    Core    │  │
│  │  Layer     │  │              │  │  Reranker  │  │
│  │ /rerank    │→ │ Queue Mgmt   │→ │            │  │
│  │ /v1/rerank │  │ Concurrency  │  │ ┌────────┐ │  │
│  │ /health    │  │ Metrics      │  │ │PyTorch │ │  │
│  │ /metrics   │  │              │  │ │  or    │ │  │
│  └────────────┘  └──────────────┘  │ │  MLX   │ │  │
│                                     │ └────────┘ │  │
└─────────────────────────────────────┴────────────┴──┘
```

### Package Architecture

```
src/reranker/
├── api/                    # FastAPI Application Layer
│   ├── app.py             # FastAPI app factory & health endpoints
│   └── routes.py          # API route definitions (/rerank, /v1/rerank)
│
├── core/                  # Core Business Logic
│   ├── config.py          # Environment-based configuration
│   ├── concurrency.py     # Advanced queue and semaphore management
│   └── unified_reranker.py # Multi-backend model wrapper (PyTorch/MLX)
│
├── models/                # Data Models & Validation
│   └── schemas.py         # Pydantic models for request/response validation
│
├── services/              # Business Logic Services
│   └── reranker_service.py # Service orchestration, metrics, caching
│
└── utils/                 # Utility Functions
    ├── distributed_cache.py # Redis distributed caching
    ├── micro_batcher.py    # GPU micro-batching optimization
    └── normalization.py    # Document preprocessing utilities
```

**Key Components:**

- **api/app.py**: FastAPI application factory and health endpoints
- **api/routes.py**: API endpoint definitions and request handling
- **services/reranker_service.py**: Business logic, concurrency control, metrics
- **core/unified_reranker.py**: Multi-backend model wrapper (PyTorch/MLX)
- **core/concurrency.py**: Advanced queue and semaphore management
- **core/config.py**: Centralized configuration from environment variables
- **models/schemas.py**: Pydantic models for validation
- **utils/normalization.py**: Document preprocessing utilities
- **utils/distributed_cache.py**: Redis caching and request deduplication
- **utils/micro_batcher.py**: GPU efficiency optimization

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
RERANKER_MAX_PARALLEL=8 ./scripts/start_reranker.sh restart
```

### Memory issues

```bash
# Reduce batch size
RERANKER_BATCH_SIZE=8 ./scripts/start_reranker.sh restart

# Disable cache
ENABLE_PREDICTION_CACHE=false ./scripts/start_reranker.sh restart

# Reduce parallelism
RERANKER_MAX_PARALLEL=2 ./scripts/start_reranker.sh restart
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

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd reranker

# Install in development mode with all dependencies
pip install -e ".[dev,all]"

# Load development configuration
source config/development.env

# Run in development mode
python main.py

# Or with auto-reload
uvicorn reranker.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=reranker --cov-report=html

# Test package structure
python test_structure.py

# Integration tests with performance
./scripts/performance_test.sh load 10 2
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Manual Testing

```bash
# Test the reranker directly
python -c "
import sys
sys.path.insert(0, 'src')
from reranker.core.unified_reranker import UnifiedReRanker
from reranker.core.config import RerankerConfig

config = RerankerConfig.from_env()
reranker = UnifiedReRanker(config)
results = reranker.rerank('test query', ['doc1', 'doc2'])
print(results)
"
```

### Adding New Features

1. **Configuration**: Update `src/reranker/core/config.py` for new settings
2. **API Endpoints**: Add to `src/reranker/api/routes.py`
3. **Business Logic**: Implement in `src/reranker/services/` or `src/reranker/core/`
4. **Data Models**: Update `src/reranker/models/schemas.py` if needed
5. **Utilities**: Add helpers to `src/reranker/utils/`
6. **Tests**: Add tests to appropriate `tests/unit/` or `tests/integration/`
7. **Documentation**: Update README and relevant docs

## 🎯 **Benefits of Optimized Structure**

### **Professional Package Organization**
- ✅ **src-layout**: Industry standard Python package structure
- ✅ **Separation of concerns**: Clear boundaries between API, core logic, models, services, and utilities
- ✅ **Modern packaging**: Both `setup.py` and `pyproject.toml` support
- ✅ **Multiple entry points**: Various ways to run the application

### **Enhanced Developer Experience**
- ✅ **IDE-friendly**: Proper import resolution and navigation
- ✅ **Type hints**: Better code completion and error detection
- ✅ **Clear documentation**: Comprehensive guides and examples
- ✅ **Environment configs**: Pre-configured settings for different deployment scenarios

### **Improved Maintainability**
- ✅ **Testable architecture**: Dedicated test structure with fixtures
- ✅ **Modular design**: Easy to modify individual components
- ✅ **Clean dependencies**: Well-defined module relationships
- ✅ **Professional standards**: Follows Python packaging best practices

### **Production Ready**
- ✅ **Multiple deployment methods**: Package installation, scripts, Docker-ready
- ✅ **Environment-specific configs**: Development, production, Apple Silicon optimized
- ✅ **Comprehensive monitoring**: Health checks, metrics, logging
- ✅ **Scalable architecture**: Multi-server deployment support

## Migration from Old Structure

If upgrading from the previous flat structure:

### **Import Changes**
```python
# Old imports
from .config import RerankerConfig
from .service import rerank_with_queue

# New imports
from reranker.core.config import RerankerConfig
from reranker.services.reranker_service import rerank_with_queue
```

### **Script Path Changes**
```bash
# Old script paths
./start_reranker.sh
./manage_reranker.sh

# New script paths
./scripts/start_reranker.sh
./scripts/manage_reranker.sh
```

## License

[Your License Here]

## Contributing

The new package structure makes contributing easier:

1. Fork the repository
2. Create a feature branch
3. Make changes following the package structure:
   - API changes: `src/reranker/api/`
   - Core logic: `src/reranker/core/`
   - Models: `src/reranker/models/`
   - Services: `src/reranker/services/`
   - Utilities: `src/reranker/utils/`
4. Add tests in appropriate directories
5. Run code quality checks: `black`, `isort`, `mypy`, `flake8`
6. Submit a pull request

## Support

For issues and questions:
- Check [docs/MULTI_SERVER_APPLE_SILICON.md](docs/MULTI_SERVER_APPLE_SILICON.md) and [docs/PERFORMANCE_OPTIMIZATION.md](docs/PERFORMANCE_OPTIMIZATION.md)
- Review [docs/STRUCTURE_README.md](docs/STRUCTURE_README.md) for detailed structure information
- Check [docs/OPTIMIZATION_COMPLETE.md](docs/OPTIMIZATION_COMPLETE.md) for migration details
- Open an issue on GitHub
- Contact [Your Contact Info]

## Additional Resources

- [📁 Package Structure Guide](docs/STRUCTURE_README.md)
- [🔧 Optimization Details](docs/OPTIMIZATION_COMPLETE.md)
- [🧹 Cleanup Summary](docs/CLEANUP_COMPLETE.md)
- [📊 Performance Optimization](docs/PERFORMANCE_OPTIMIZATION.md)
- [🚀 Multi-Server Deployment](docs/MULTI_SERVER_APPLE_SILICON.md)
- [⚙️ Environment Variables](docs/ENV_VARS_QUICK_REF.md)
