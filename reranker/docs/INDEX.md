# Reranker Service - Complete Documentation Index

## Quick Links

- [README](../README.md) - **START HERE** - Overview and quick start
- [Multi-Server & Apple Silicon Guide](MULTI_SERVER_APPLE_SILICON.md) - Deployment and optimization
- [Environment Variables Reference](ENV_VARS_QUICK_REF.md) - Configuration guide
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) - Production deployment steps
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) - Detailed tuning guide
- [Implementation Complete](IMPLEMENTATION_COMPLETE.md) - Technical summary

## Documentation Structure

```
reranker/
├── README.md                          # Main documentation
├── requirements.txt                   # Python dependencies
├── start_reranker.sh                 # Startup script
├── manage_reranker.sh                # Service management
├── performance_test.sh               # Performance testing
├── test_multi_backend.py             # Multi-backend tests
│
├── Core Application Files
│   ├── index.py                      # Entry point
│   ├── config.py                     # Configuration
│   ├── app.py                        # FastAPI application
│   ├── routes.py                     # API endpoints
│   ├── service.py                    # Core service logic
│   ├── schemas.py                    # Pydantic models
│   └── normalization.py              # Utilities
│
├── Reranker Backends
│   ├── unified_reranker.py           # Multi-backend wrapper (NEW)
│   ├── optimized_hf_model.py         # Optimized PyTorch
│   └── hf_model.py                   # Basic PyTorch
│
├── Concurrency Management
│   ├── enhanced_concurrency.py       # Advanced controller
│   └── concurrency.py                # Basic controller
│
└── docs/
    ├── MULTI_SERVER_APPLE_SILICON.md # Multi-server & M-series guide
    ├── ENV_VARS_QUICK_REF.md         # Configuration reference
    ├── DEPLOYMENT_CHECKLIST.md       # Deployment guide
    ├── PERFORMANCE_OPTIMIZATION.md   # Performance tuning
    └── IMPLEMENTATION_COMPLETE.md    # Technical summary
```

## Getting Started

### For New Users

1. **Read the README** - [README.md](../README.md)
   - Quick start guide
   - Basic configuration
   - API examples

2. **Install and Test** - Follow README instructions
   ```bash
   pip install -r requirements.txt
   ./start_reranker.sh dev
   curl http://localhost:8000/health
   ```

3. **Review Configuration** - [ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md)
   - All environment variables
   - Configuration examples
   - Hardware-specific settings

### For Production Deployment

1. **Multi-Server Setup** - [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md)
   - Multi-server deployment strategies
   - Load balancer configuration
   - Scaling guidelines

2. **Follow Checklist** - [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
   - Pre-deployment validation
   - Single/multi-server setup
   - Monitoring setup
   - Post-deployment verification

3. **Performance Tuning** - [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
   - Concurrency tuning
   - Memory optimization
   - Caching strategies

### For Apple Silicon Users

1. **Installation**
   ```bash
   pip install mlx mlx-lm  # Optional but recommended
   ```

2. **Configuration** - See [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md)
   ```bash
   USE_MLX=true
   BATCH_SIZE=32
   ```

3. **Validation**
   ```bash
   curl http://localhost:8000/health | jq '.model.backend, .model.device'
   # Expected: "mlx", "mlx"
   ```

## Key Features by Document

### README.md
- ✓ Service overview
- ✓ Quick start guide
- ✓ API endpoints documentation
- ✓ Basic configuration
- ✓ Troubleshooting basics

### MULTI_SERVER_APPLE_SILICON.md
- ✓ Multi-server deployment patterns
- ✓ Load balancer configuration
- ✓ Apple Silicon optimization (MPS/MLX)
- ✓ Performance benchmarks
- ✓ Monitoring multi-server deployments
- ✓ Distributed mode (future)

### ENV_VARS_QUICK_REF.md
- ✓ Complete environment variable catalog
- ✓ Default values and ranges
- ✓ Hardware-specific configurations
- ✓ Use case examples
- ✓ Performance tuning workflow

### DEPLOYMENT_CHECKLIST.md
- ✓ Pre-deployment validation steps
- ✓ Single server deployment
- ✓ Multi-server deployment
- ✓ Apple Silicon setup
- ✓ Monitoring configuration
- ✓ Production readiness criteria

### PERFORMANCE_OPTIMIZATION.md
- ✓ Concurrency optimization strategies
- ✓ Memory management techniques
- ✓ Caching configuration
- ✓ Batch processing tuning
- ✓ Hardware-specific optimizations

### IMPLEMENTATION_COMPLETE.md
- ✓ Technical implementation summary
- ✓ Architecture overview
- ✓ File changes and additions
- ✓ Migration guide
- ✓ Validation checklist

## Common Scenarios

### Scenario 1: Local Development
**Goal:** Run service locally for development/testing

**Documents:**
1. [README.md](../README.md) - Installation and quick start
2. [ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md) - Development configuration

**Commands:**
```bash
./start_reranker.sh dev
```

### Scenario 2: Production Single Server
**Goal:** Deploy production service on single server

**Documents:**
1. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Follow single server section
2. [ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md) - Production configuration
3. [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) - Tuning

**Commands:**
```bash
MAX_PARALLEL_REQUESTS=4 \
BATCH_SIZE=16 \
./start_reranker.sh daemon
```

### Scenario 3: Multi-Server Production
**Goal:** Deploy high-availability multi-server setup

**Documents:**
1. [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md) - Multi-server guide
2. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Multi-server section
3. [ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md) - Configuration

**Commands:**
```bash
PORT=8000 ./start_reranker.sh daemon
PORT=8001 ./start_reranker.sh daemon
PORT=8002 ./start_reranker.sh daemon
# Configure load balancer
```

### Scenario 4: Apple Silicon Optimization
**Goal:** Maximize performance on M1/M2/M3 Mac

**Documents:**
1. [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md) - Apple Silicon section
2. [ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md) - Apple Silicon config

**Commands:**
```bash
pip install mlx mlx-lm
USE_MLX=true BATCH_SIZE=32 ./start_reranker.sh daemon
```

### Scenario 5: Troubleshooting
**Goal:** Diagnose and fix issues

**Documents:**
1. [README.md](../README.md) - Troubleshooting section
2. [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md) - Troubleshooting section
3. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Validation steps

**Commands:**
```bash
./manage_reranker.sh status
./manage_reranker.sh tail
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Document Relationships

```
                    README.md (START HERE)
                         |
        +----------------+----------------+
        |                |                |
   Quick Start      Configuration    Production
        |                |                |
        v                v                v
test_multi_backend  ENV_VARS_QUICK   DEPLOYMENT_
    .py             _REF.md          CHECKLIST.md
                         |                |
                         v                v
                    MULTI_SERVER_    PERFORMANCE_
                    APPLE_SILICON    OPTIMIZATION
                        .md              .md
                         |
                         v
                  IMPLEMENTATION_
                    COMPLETE.md
```

## Quick Reference

### Installation
```bash
pip install -r requirements.txt
# Optional: pip install mlx mlx-lm
```

### Start Service
```bash
./start_reranker.sh dev      # Development
./start_reranker.sh daemon   # Production
```

### Check Status
```bash
./manage_reranker.sh status
curl http://localhost:8000/health
```

### Test Performance
```bash
./performance_test.sh load 100 4
python test_multi_backend.py
```

### View Logs
```bash
./manage_reranker.sh tail
```

### Stop Service
```bash
./manage_reranker.sh stop
```

## Support Resources

### Health & Metrics
- **Health Endpoint:** `GET http://localhost:8000/health`
- **Metrics Endpoint:** `GET http://localhost:8000/metrics`

### Scripts
- **Start:** `./start_reranker.sh [dev|daemon|fg]`
- **Manage:** `./manage_reranker.sh [start|stop|restart|status|tail]`
- **Test:** `./performance_test.sh [load|latency|throughput|stress]`
- **Validate:** `python test_multi_backend.py`

### Configuration
- **Main Config:** Environment variables
- **Reference:** [ENV_VARS_QUICK_REF.md](ENV_VARS_QUICK_REF.md)
- **Examples:** All documentation files

### Performance
- **Tuning Guide:** [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
- **Apple Silicon:** [MULTI_SERVER_APPLE_SILICON.md](MULTI_SERVER_APPLE_SILICON.md)
- **Test Tools:** `performance_test.sh`, `test_multi_backend.py`

## Document Maintenance

### When to Update

| Trigger | Update Documents |
|---------|------------------|
| New feature added | README.md, relevant guide |
| Configuration changed | ENV_VARS_QUICK_REF.md, README.md |
| Performance improvement | PERFORMANCE_OPTIMIZATION.md |
| Deployment change | DEPLOYMENT_CHECKLIST.md |
| API changed | README.md (API section) |
| Multi-server enhancement | MULTI_SERVER_APPLE_SILICON.md |

### Documentation Standards

- Keep README.md as the entry point
- Include practical examples in all docs
- Update quick reference cards
- Maintain consistent formatting
- Include troubleshooting sections
- Add validation steps
- Provide copy-paste commands

## Feedback & Contributions

If you find issues or have suggestions:

1. **Check existing documentation** - Issue may be addressed
2. **Test your scenario** - Verify issue is reproducible
3. **Report issues** - Include:
   - Scenario description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, hardware, config)
4. **Suggest improvements** - Documentation or features

## Version History

### v1.0 (Current)
- ✓ Multi-backend architecture (PyTorch + MLX)
- ✓ Apple Silicon support (MPS + MLX)
- ✓ Multi-server deployment guide
- ✓ Comprehensive documentation
- ✓ Production-ready deployment

### Future Enhancements
- 🚧 Distributed coordination (Redis-based)
- 🚧 Native MLX model format
- 🚧 Auto-scaling support
- 🚧 Advanced monitoring dashboards

## Summary

This documentation set provides:

- **Complete coverage** - Installation to production deployment
- **Practical examples** - Copy-paste commands for all scenarios
- **Performance guidance** - Hardware-specific optimization
- **Production readiness** - Checklists and validation steps
- **Troubleshooting** - Common issues and solutions

**Start with [README.md](../README.md) and follow the links based on your needs!**
