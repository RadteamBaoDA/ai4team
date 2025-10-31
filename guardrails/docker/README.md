# Ollama Guardrails Docker Setup

This directory contains Docker configurations for running the Ollama Guardrails proxy in various environments.

## Quick Start

### Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- 4GB+ available RAM
- 2GB+ available disk space

### Basic Usage

1. **Start all services** (recommended for first-time users):
   ```bash
   # Linux/macOS
   ./manage.sh up
   
   # Windows
   manage.bat up
   ```

2. **Access the services**:
   - Proxy API: http://localhost:8080
   - Ollama API: http://localhost:11434 (direct access)
   - Redis: localhost:6379 (when running dev profile)

3. **Stop services**:
   ```bash
   # Linux/macOS
   ./manage.sh down
   
   # Windows  
   manage.bat down
   ```

## Available Configurations

### 1. Standard Docker Compose (`docker-compose.yml`)

**Best for**: Production deployments, standard Linux environments

```bash
# Start standard configuration
docker-compose up -d

# Or using management script
./manage.sh up
```

**Includes**:
- Ollama Guardrails Proxy (port 8080)
- Ollama LLM Service (port 11434) 
- Redis Cache (port 6379, localhost only)

**Resource requirements**: 2GB RAM, 1GB disk

### 2. macOS Optimized (`docker-compose-macos.yml`)

**Best for**: Apple Silicon Macs (M1/M2/M3), macOS development

```bash
# Start macOS optimized configuration
./manage.sh macos

# Or directly
docker-compose -f docker-compose-macos.yml up -d
```

**Optimizations**:
- ARM64 platform targeting
- Apple Silicon performance tuning
- Optimized resource limits
- Enhanced thread configurations

### 3. Redis Only (`docker-compose-redis.yml`)

**Best for**: External proxy deployments, distributed caching

```bash
# Start Redis only
./manage.sh redis

# Or directly  
docker-compose -f docker-compose-redis.yml up -d
```

**Includes**:
- Redis with production configuration
- Redis Commander web UI (optional, `--profile dev`)

### 4. Development Environment (`docker-compose.override.yml`)

**Best for**: Development, debugging, testing

```bash
# Start development environment
./manage.sh dev

# Or directly
docker-compose -f docker-compose.yml -f docker-compose.override.yml --profile dev up -d
```

**Additional features**:
- Hot code reloading
- Debug logging
- Relaxed rate limits  
- Redis Commander UI
- Source code mounting
- Development tools

### 5. Monitoring Stack

**Best for**: Production monitoring, performance analysis

```bash
# Start with monitoring
./manage.sh monitor

# Or directly
docker-compose -f docker-compose.yml -f docker-compose.override.yml --profile monitoring up -d
```

**Additional services**:
- Prometheus (metrics collection) - port 9090
- Grafana (dashboards) - port 3000
  - Default login: admin/dev123

## Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Key variables to customize:

```env
# Ollama backend
OLLAMA_URL=http://ollama:11434

# Proxy configuration  
PROXY_HOST=0.0.0.0
PROXY_PORT=8080

# Guards
ENABLE_INPUT_GUARD=true
ENABLE_OUTPUT_GUARD=true
BLOCK_ON_GUARD_ERROR=false

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Cache configuration
CACHE_ENABLED=true
CACHE_BACKEND=redis
CACHE_TTL=3600

# Performance
OLLAMA_NUM_PARALLEL=auto
REQUEST_TIMEOUT=300
```

### Persistent Data

Data is stored in Docker volumes:

- `ollama_data`: Ollama models and configuration
- `redis_data`: Redis cache data  
- `proxy_cache`: Proxy cache data

**Backup volumes**:
```bash
# Backup Ollama models
docker run --rm -v ollama_data:/data -v $(pwd):/backup ubuntu tar czf /backup/ollama-backup.tar.gz /data

# Restore Ollama models
docker run --rm -v ollama_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/ollama-backup.tar.gz -C /
```

## Management Scripts

The `manage.sh` (Linux/macOS) and `manage.bat` (Windows) scripts provide easy service management:

### Common Commands

```bash
# Service management
./manage.sh up [profile]      # Start services
./manage.sh down              # Stop services  
./manage.sh restart [service] # Restart service(s)
./manage.sh status            # Show status

# Development
./manage.sh dev               # Start dev environment
./manage.sh logs [service]    # View logs
./manage.sh shell proxy       # Open shell in proxy container

# Maintenance  
./manage.sh build [service]   # Rebuild service(s)
./manage.sh update            # Pull latest images
./manage.sh clean             # Remove unused resources
./manage.sh deep-clean        # Full cleanup (DESTRUCTIVE)

# Service shortcuts
./manage.sh logs proxy        # Proxy logs
./manage.sh shell redis       # Redis shell
./manage.sh exec proxy "python -c 'import sys; print(sys.version)'"
```

### Service Names

The scripts accept friendly service names:

- `proxy`, `guard`, `guardrails` → `ollama-guard-proxy`
- `ollama`, `llm` → `ollama` 
- `redis`, `cache` → `redis`
- `redis-ui` → `redis-commander`

## Health Checks

All services include health checks:

```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect <container_name> | grep Health -A 10
```

**Health endpoints**:
- Proxy: `GET /health` (port 8080)
- Ollama: `GET /api/tags` (port 11434)
- Redis: `redis-cli ping`

## Troubleshooting

### Common Issues

1. **Port conflicts**:
   ```bash
   # Check what's using ports
   netstat -tulpn | grep :8080
   
   # Use different ports
   PROXY_PORT=8081 ./manage.sh up
   ```

2. **Memory issues**:
   ```bash
   # Check resource usage
   ./manage.sh status
   
   # Reduce Ollama parallel processing
   echo "OLLAMA_NUM_PARALLEL=1" >> .env
   ```

3. **Permission errors**:
   ```bash
   # Fix log directory permissions
   sudo chown -R $USER:$USER ../logs
   
   # On macOS, ensure Docker has access to project directory
   ```

4. **Container won't start**:
   ```bash
   # Check logs
   ./manage.sh logs proxy
   
   # Rebuild container
   ./manage.sh build proxy
   
   # Check configuration
   docker-compose config
   ```

### Performance Tuning

**For development (low resource usage)**:
```env
OLLAMA_NUM_PARALLEL=1
REDIS_MAX_MEMORY=128mb
CACHE_TTL=1800
```

**For production (high performance)**:
```env
OLLAMA_NUM_PARALLEL=4
REDIS_MAX_MEMORY=1gb
CACHE_TTL=7200
REDIS_MAX_CONNECTIONS=100
```

**For Apple Silicon Macs**:
```env
OMP_NUM_THREADS=8
VECLIB_MAXIMUM_THREADS=8
PYTORCH_ENABLE_MPS_FALLBACK=1
```

### Monitoring

**Access monitoring services**:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/dev123)
- Redis Commander: http://localhost:8081 (admin/admin)

**Key metrics to monitor**:
- Request rate and latency
- Guard processing time  
- Cache hit ratio
- Memory and CPU usage
- Error rates

## Security Considerations

### Production Deployment

1. **Use production compose file**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

2. **Disable debug features**:
   ```env
   DEBUG=false
   DEV_MODE=false
   LOG_LEVEL=WARNING
   ```

3. **Enable IP filtering**:
   ```env
   ENABLE_IP_FILTER=true
   IP_WHITELIST=192.168.1.0/24,10.0.0.0/8
   ```

4. **Use strong Redis password**:
   ```env
   REDIS_PASSWORD=your-strong-password-here
   ```

5. **Limit resource usage**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2.0'
         memory: 2G
   ```

### Network Security

- Redis is bound to localhost by default
- Ollama is bound to localhost by default  
- Only proxy port (8080) is exposed externally
- Use reverse proxy (nginx) for SSL termination

## Development

### Building Custom Images

```bash
# Build with custom tag
docker build -t my-guardrails:latest -f ../Dockerfile ..

# Build for specific platform
docker build --platform linux/amd64 -t my-guardrails:amd64 -f ../Dockerfile ..
docker build --platform linux/arm64 -t my-guardrails:arm64 -f ../Dockerfile ..
```

### Testing Changes

```bash
# Start development environment
./manage.sh dev

# Make code changes (they'll be reflected immediately)
# Test your changes

# View logs in real-time  
./manage.sh logs proxy

# Rebuild if needed
./manage.sh build proxy
```

### Debugging

```bash
# Open shell in running container
./manage.sh shell proxy

# Execute commands
./manage.sh exec proxy "python -c 'import ollama_guardrails; print(ollama_guardrails.__version__)'"

# Check Python environment
./manage.sh exec proxy "pip list"

# Test Redis connection
./manage.sh exec redis "redis-cli ping"
```

## Support

For issues and questions:

1. Check logs: `./manage.sh logs`
2. Verify configuration: `docker-compose config`
3. Check resource usage: `./manage.sh status`  
4. Review the main [README](../README.md) for application-specific help
5. Open an issue in the project repository

## Version Information

- Docker Compose format: 3.8
- Target Python version: 3.12
- Base images: python:3.12-slim, redis:7-alpine, ollama/ollama:latest
- Supported platforms: linux/amd64, linux/arm64