# Docker Setup for Reranker Service

This directory contains Docker configurations for running the Reranker service in various environments.

## 🐳 Available Configurations

### 1. **Production** (`docker-compose.yml`)
- **Purpose**: Production-ready deployment with Redis caching
- **Features**: High parallelism, Redis distributed cache, performance optimizations
- **Usage**: `./docker-manage.sh up production`

### 2. **Development** (`docker-compose.dev.yml`)
- **Purpose**: Local development with minimal resources
- **Features**: Debug logging, source volume mounting, reduced parallelism
- **Usage**: `./docker-manage.sh up dev`

### 3. **Apple Silicon** (`docker-compose.macos.yml`)
- **Purpose**: Optimized for M1/M2/M3 Macs
- **Features**: MPS device support, MLX acceleration, ARM64 platform
- **Usage**: `./docker-manage.sh up macos`

### 4. **GPU** (`docker-compose.gpu.yml`)
- **Purpose**: NVIDIA GPU acceleration
- **Features**: CUDA support, larger batch sizes, quantization
- **Usage**: `./docker-manage.sh up gpu`

### 5. **Scaling** (`docker-compose.scale.yml`)
- **Purpose**: Multi-instance deployment with load balancing
- **Features**: Nginx load balancer, horizontal scaling, monitoring
- **Usage**: `./docker-manage.sh scale 3`

## 🚀 Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2.0+
- For GPU: NVIDIA Container Toolkit
- For Apple Silicon: Docker Desktop with ARM64 support

### 1. Basic Setup
```bash
# Clone and navigate to reranker directory
cd reranker/

# Build and start production services
./docker-manage.sh build production
./docker-manage.sh up production -d

# Check service health
./docker-manage.sh health
curl http://localhost:8000/health
```

### 2. Development Setup
```bash
# Start development environment
./docker-manage.sh up dev

# View logs
./docker-manage.sh logs reranker

# Open shell in container
./docker-manage.sh shell reranker
```

### 3. GPU Setup (NVIDIA)
```bash
# Ensure NVIDIA Container Toolkit is installed
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Start GPU-optimized service
./docker-manage.sh build gpu
./docker-manage.sh up gpu -d
```

### 4. Apple Silicon Setup
```bash
# Start Apple Silicon optimized service
./docker-manage.sh build macos
./docker-manage.sh up macos -d
```

## 📋 Management Commands

### Docker Management Script (`./docker-manage.sh`)

```bash
# Build commands
./docker-manage.sh build [env]           # Build images
./docker-manage.sh build dev --no-cache  # Build without cache
./docker-manage.sh build gpu --pull      # Pull latest base images

# Service management
./docker-manage.sh up [env] -d           # Start services (detached)
./docker-manage.sh down [env]            # Stop services
./docker-manage.sh restart [env]         # Restart services
./docker-manage.sh status                # Show service status

# Scaling and monitoring
./docker-manage.sh scale 3               # Scale to 3 instances
./docker-manage.sh up --profile monitoring  # Start with monitoring

# Debugging
./docker-manage.sh logs reranker         # Show logs
./docker-manage.sh shell reranker        # Open shell
./docker-manage.sh health                # Check health

# Maintenance
./docker-manage.sh clean                 # Clean up containers/images
./docker-manage.sh update production     # Update and restart
```

### Direct Docker Compose Commands

```bash
# Production
docker-compose up -d
docker-compose logs -f reranker
docker-compose down

# Development
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f reranker

# GPU
docker-compose -f docker-compose.gpu.yml up -d

# Apple Silicon
docker-compose -f docker-compose.macos.yml up -d

# Scaling with load balancer
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale reranker=3
```

## 🔧 Configuration

### Environment Variables

Key environment variables can be set in the docker-compose files or via `.env` file:

```bash
# Model Configuration
RERANKER_MODEL=BAAI/bge-reranker-base
RERANKER_QUANTIZATION=bf16
RERANKER_DEVICE=auto

# Performance
RERANKER_MAX_PARALLEL=8
RERANKER_BATCH_SIZE=32
RERANKER_MAX_QUEUE=20

# Caching
ENABLE_PREDICTION_CACHE=true
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

### Volume Mounts

```yaml
volumes:
  - ./logs:/app/logs           # Application logs
  - ./models:/app/models       # Pre-downloaded models
  - ./cache:/app/cache         # Local cache directory
  - ./config:/app/config:ro    # Configuration files (read-only)
```

### Redis Configuration

Redis is configured in `config/redis.conf` with:
- 512MB memory limit (production) / 256MB (dev)
- LRU eviction policy
- AOF persistence for production
- Optimized for caching reranking results

## 🏗️ Advanced Setups

### 1. Multi-Instance with Load Balancer

```bash
# Start 3 reranker instances with Nginx load balancer
./docker-manage.sh scale 3

# Or manually
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale reranker=3

# Access via load balancer
curl http://localhost:80/health
curl http://localhost:80/rerank -X POST -H "Content-Type: application/json" -d '...'
```

### 2. Multi-GPU Setup

```bash
# Start with multi-GPU profile
docker-compose -f docker-compose.gpu.yml -f docker-compose.scale.yml --profile multi-gpu up -d

# This creates:
# - reranker-gpu-1 (uses GPU 0)
# - reranker-gpu-2 (uses GPU 1)
```

### 3. Monitoring Stack

```bash
# Start with monitoring services
./docker-manage.sh up --profile monitoring

# Access monitoring:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin123)
```

### 4. Development with Redis

```bash
# Start development with Redis cache
docker-compose -f docker-compose.dev.yml --profile redis up -d
```

## 📊 Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| Reranker API | http://localhost:8000 | Main API endpoint |
| Health Check | http://localhost:8000/health | Service health status |
| Metrics | http://localhost:8000/metrics | Performance metrics |
| Load Balancer | http://localhost:80 | Nginx load balancer |
| Redis | localhost:6379 | Redis cache (local access only) |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3000 | Metrics visualization |

## 🧪 Testing

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Simple rerank request
curl -X POST http://localhost:8000/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "documents": ["AI is the future", "Python programming", "Neural networks"],
    "top_k": 2
  }'

# Cohere-compatible endpoint
curl -X POST http://localhost:8000/v1/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning", 
    "documents": ["AI is the future", "Python programming", "Neural networks"],
    "top_n": 2,
    "model": "rerank-english-v2.0"
  }'
```

### Load Testing

```bash
# Simple load test with Apache Bench
ab -n 100 -c 10 -p test_request.json -T application/json http://localhost:8000/rerank

# Or use the built-in performance test
docker-compose exec reranker bash
./scripts/performance_test.sh load 100 4
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
./docker-manage.sh logs reranker

# Check resource usage
docker stats

# Verify Docker daemon is running
docker version
```

#### 2. GPU Not Detected
```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Check container GPU access
docker-compose -f docker-compose.gpu.yml exec reranker nvidia-smi
```

#### 3. Apple Silicon Issues
```bash
# Ensure ARM64 platform
docker-compose -f docker-compose.macos.yml exec reranker uname -m
# Should return: aarch64

# Check MPS availability
docker-compose -f docker-compose.macos.yml exec reranker python -c "import torch; print(torch.backends.mps.is_available())"
```

#### 4. Memory Issues
```bash
# Reduce batch size and parallelism
# Edit docker-compose file:
RERANKER_MAX_PARALLEL=2
RERANKER_BATCH_SIZE=8

# Or use development config
./docker-manage.sh up dev
```

#### 5. Port Conflicts
```bash
# Check port usage
lsof -i :8000
netstat -tulpn | grep :8000

# Use different port
PORT=8001 docker-compose up -d
```

### Log Analysis

```bash
# Real-time logs
./docker-manage.sh logs reranker

# Specific service logs
docker-compose logs redis
docker-compose logs nginx

# Container inspection
docker inspect reranker-service

# Performance metrics
curl http://localhost:8000/metrics | jq .
```

### Resource Monitoring

```bash
# Container resource usage
docker stats

# System resources
docker system df
docker system events

# Health checks
docker-compose ps
curl http://localhost:8000/health | jq .
```

## 🔒 Security Considerations

### Production Security

1. **Network Security**
   - Use internal networks for service communication
   - Expose only necessary ports
   - Consider using a reverse proxy with SSL/TLS

2. **Container Security**
   - Run containers as non-root user
   - Use security scanning tools
   - Keep base images updated

3. **Redis Security**
   - Enable authentication in production
   - Restrict network access
   - Use TLS for connections

### Example Secure Configuration

```yaml
# In docker-compose.yml
services:
  redis:
    command: redis-server --requirepass your_secure_password
    networks:
      - internal
    
  reranker:
    environment:
      - REDIS_URL=redis://:your_secure_password@redis:6379/0
    networks:
      - internal
      - external

networks:
  internal:
    internal: true
  external:
```

## 📈 Performance Tuning

### GPU Optimization

```yaml
# docker-compose.gpu.yml
environment:
  - RERANKER_BATCH_SIZE=64        # Larger batches for GPU
  - RERANKER_MAX_PARALLEL=16      # Higher parallelism
  - ENABLE_MIXED_PRECISION=true   # FP16 for faster inference
  - TORCH_CUDNN_BENCHMARK=1       # CUDA optimizations
```

### Apple Silicon Optimization

```yaml
# docker-compose.macos.yml  
environment:
  - RERANKER_USE_MLX=true         # Enable MLX acceleration
  - RERANKER_DEVICE=mps           # Use Metal Performance Shaders
  - RERANKER_BATCH_SIZE=32        # Optimize for unified memory
  - OMP_NUM_THREADS=8             # Use more CPU cores
```

### Memory Management

```yaml
deploy:
  resources:
    limits:
      memory: 4G                  # Prevent OOM
    reservations:
      memory: 2G                  # Guarantee minimum
```

## 📚 Additional Resources

- [Reranker Service Documentation](../README.md)
- [Performance Optimization Guide](../docs/PERFORMANCE_OPTIMIZATION.md)
- [Multi-Server Apple Silicon Guide](../docs/MULTI_SERVER_APPLE_SILICON.md)
- [Environment Variables Reference](../docs/ENV_VARS_QUICK_REF.md)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)

## 🤝 Support

For Docker-specific issues:
1. Check the troubleshooting section above
2. Review container logs: `./docker-manage.sh logs`
3. Verify system requirements and dependencies
4. Open an issue with Docker version and logs

For service-specific issues, see the main [README.md](../README.md) file.