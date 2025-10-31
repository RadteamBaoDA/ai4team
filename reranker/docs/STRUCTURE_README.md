# Reranker Service - Optimized Package Structure

A production-ready reranking service powered by HuggingFace Transformers with an optimized Python package structure following best practices.

## 📁 **New Optimized Package Structure**

```
reranker/
├── 📁 src/reranker/           # Main package source code
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Entry point for `python -m reranker`
│   │
│   ├── 📁 api/                # FastAPI application layer
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI application factory
│   │   └── routes.py          # API route definitions
│   │
│   ├── 📁 core/               # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── concurrency.py     # Concurrency control
│   │   └── unified_reranker.py # Multi-backend reranker
│   │
│   ├── 📁 models/             # Data models and schemas
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   │
│   ├── 📁 services/           # Business logic services
│   │   ├── __init__.py
│   │   └── reranker_service.py # Main service orchestration
│   │
│   └── 📁 utils/              # Utility functions
│       ├── __init__.py
│       ├── distributed_cache.py
│       ├── micro_batcher.py
│       └── normalization.py
│
├── 📁 tests/                  # Test suite
│   ├── conftest.py            # Test configuration
│   ├── 📁 unit/               # Unit tests
│   │   └── test_config.py
│   └── 📁 integration/        # Integration tests
│       └── test_api.py
│
├── 📁 scripts/                # Shell scripts and utilities
│   ├── manage_reranker.sh     # Service management
│   ├── performance_test.sh    # Performance testing
│   └── start_reranker.sh      # Startup script
│
├── 📁 config/                 # Environment configurations
│   ├── README.md
│   ├── development.env        # Development settings
│   ├── production.env         # Production settings
│   └── apple_silicon.env      # Apple Silicon optimized
│
├── 📁 docs/                   # Documentation
│   └── (existing documentation)
│
├── main.py                    # Main entry point
├── setup.py                   # Package setup (legacy)
├── pyproject.toml             # Modern Python packaging
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## 🚀 **Benefits of New Structure**

### **1. Separation of Concerns**
- **API Layer** (`api/`): FastAPI routes and application setup
- **Core Logic** (`core/`): Business logic, configuration, and reranking
- **Models** (`models/`): Data validation and schemas  
- **Services** (`services/`): Service orchestration and coordination
- **Utils** (`utils/`): Helper functions and utilities

### **2. Better Testability**
- Dedicated `tests/` directory with unit and integration tests
- Clear separation enables focused testing of individual components
- Test fixtures and configuration in `conftest.py`

### **3. Improved Maintainability**
- Clear module boundaries and responsibilities
- Easier to navigate and understand codebase
- Simplified debugging and troubleshooting

### **4. Production Ready**
- Proper packaging with `setup.py` and `pyproject.toml`
- Environment-specific configuration files
- Professional project structure following Python standards

### **5. Enhanced Developer Experience**
- Type hints and proper imports
- IDE-friendly structure with clear module hierarchy
- Comprehensive documentation and examples

## 📦 **Installation & Usage**

### **Development Installation**

```bash
# Clone and navigate
git clone <repository-url>
cd reranker

# Install in development mode
pip install -e .

# Or install with all optional dependencies
pip install -e ".[all]"
```

### **Production Installation**

```bash
# Install from package
pip install reranker-service

# Or with specific extras
pip install reranker-service[mlx,redis,monitoring]
```

### **Running the Service**

```bash
# Method 1: Using main entry point
python main.py

# Method 2: Using package module
python -m reranker

# Method 3: Using console script (after installation)
reranker

# Method 4: With environment configuration
source config/production.env
python main.py
```

### **Development with Hot Reload**

```bash
# Load development environment
source config/development.env

# Start with uvicorn directly for hot reload
uvicorn reranker.api.app:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 **Configuration Management**

The new structure includes environment-specific configuration:

### **Development**
```bash
source config/development.env
python main.py
```

### **Production**
```bash
source config/production.env  
python main.py
```

### **Apple Silicon Optimization**
```bash
source config/apple_silicon.env
python main.py
```

## 🧪 **Testing**

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests  
pytest tests/integration/

# Run with coverage
pytest --cov=reranker --cov-report=html
```

## 📊 **Performance Testing**

```bash
# Load test
./scripts/performance_test.sh load 100 4

# Latency test
./scripts/performance_test.sh latency 50

# Stress test
./scripts/performance_test.sh stress 500 16
```

## 🛠 **Development Workflow**

### **Adding New Features**

1. **API Changes**: Update `src/reranker/api/routes.py`
2. **Core Logic**: Modify files in `src/reranker/core/`
3. **Data Models**: Update `src/reranker/models/schemas.py`
4. **Services**: Extend `src/reranker/services/`
5. **Utilities**: Add to `src/reranker/utils/`

### **Code Quality**

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

## 🌟 **Key Improvements**

### **Before (Flat Structure)**
```
reranker/
├── app.py
├── routes.py  
├── service.py
├── config.py
├── schemas.py
├── unified_reranker.py
├── enhanced_concurrency.py
├── normalization.py
├── distributed_cache.py
└── micro_batcher.py
```

### **After (Structured Package)**
- ✅ **Clear module hierarchy**
- ✅ **Proper package structure**
- ✅ **Separation of concerns**
- ✅ **Professional organization**
- ✅ **Better testing setup**
- ✅ **Modern Python packaging**

## 📚 **Migration Guide**

### **Import Changes**

**Old imports:**
```python
from .config import RerankerConfig
from .service import rerank_with_queue
from .schemas import RerankRequest
```

**New imports:**
```python
from reranker.core.config import RerankerConfig
from reranker.services.reranker_service import rerank_with_queue  
from reranker.models.schemas import RerankRequest
```

### **Running Scripts**

**Old:**
```bash
./start_reranker.sh
```

**New:**
```bash
./scripts/start_reranker.sh
```

## 🎯 **Next Steps**

1. **Migrate existing deployments** to use new structure
2. **Update CI/CD pipelines** to use new entry points
3. **Enhance testing coverage** with the new test structure
4. **Add more environment configurations** as needed
5. **Consider containerization** with the new structure

## 📖 **Documentation**

- [API Documentation](docs/API_UPDATES.md)
- [Performance Guide](docs/PERFORMANCE_OPTIMIZATION.md) 
- [Deployment Guide](docs/MULTI_SERVER_APPLE_SILICON.md)
- [Environment Variables](docs/ENV_VARS_QUICK_REF.md)

## 🤝 **Contributing**

The new structure makes contributing easier:

1. Fork the repository
2. Create a feature branch
3. Make changes following the package structure
4. Add tests in appropriate test directories
5. Run code quality checks
6. Submit a pull request

## 📄 **License**

[Your License Here]