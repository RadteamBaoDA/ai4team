# Project Structure

## Overview

This document describes the folder structure and organization of the Ollama Guard Proxy project after the modularization and reorganization completed in January 2025.

## Directory Layout

```
guardrails/
├── src/                          # Python source code (NEW)
│   ├── __init__.py              # Package initialization
│   ├── ollama_guard_proxy.py    # Main FastAPI application (242 lines)
│   ├── endpoints_ollama.py      # 12 Ollama API endpoints (534 lines)
│   ├── endpoints_openai.py      # 4 OpenAI-compatible endpoints (535 lines)
│   ├── endpoints_admin.py       # 9 admin/monitoring endpoints (172 lines)
│   ├── streaming_handlers.py    # Stream processing with guards (562 lines)
│   ├── http_client.py           # HTTP client management (74 lines)
│   ├── utils.py                 # Utility functions (114 lines)
│   ├── guard_manager.py         # LLM Guard integration
│   ├── cache.py                 # Caching (Redis + in-memory)
│   ├── concurrency.py           # Per-model concurrency control
│   ├── config.py                # Configuration management
│   ├── ip_whitelist.py          # IP whitelist middleware
│   └── language.py              # Language detection
│
├── scripts/                      # Shell and batch scripts (NEW)
│   ├── run_proxy.sh             # Linux/Unix runner
│   ├── run_proxy.bat            # Windows runner
│   ├── run_proxy_macos.sh       # macOS Apple Silicon runner
│   ├── deploy-nginx.sh          # Nginx deployment (Linux/Mac)
│   ├── deploy-nginx.bat         # Nginx deployment (Windows)
│   ├── setup_concurrency.sh     # Concurrency setup (Linux/Mac)
│   ├── setup_concurrency.bat    # Concurrency setup (Windows)
│   └── download_models.sh       # Model download utility
│
├── config/                       # Configuration files (NEW)
│   ├── config.yaml              # Main application config
│   └── nginx-ollama-production.conf  # Nginx configuration
│
├── tests/                        # Test files
│   ├── test_local_models.py
│   ├── test_prompt_gptoss.py
│   ├── test_output_scanner_fix.py
│   └── client_example.py
│
├── docs/                         # Documentation
│   ├── API_UPDATES.md
│   ├── CHANGES_MADE.md
│   ├── COMPLETE.md
│   ├── CONNECTION_CLEANUP_OPTIMIZATION.md
│   ├── CONCURRENCY_IMPLEMENTATION_SUMMARY.md
│   ├── CONCURRENCY_UPDATE.md
│   └── ...
│
├── docker/                       # Docker files (OPTIONAL - can organize here)
│   ├── Dockerfile               # Multi-arch Dockerfile
│   ├── Dockerfile.macos         # macOS/ARM64 optimized
│   ├── docker-compose.yml
│   ├── docker-compose-macos.yml
│   └── docker-compose-redis.yml
│
├── bk/                          # Backups (archived old versions)
│
├── main.py                      # Application entry point (NEW)
├── requirements.txt             # Python dependencies
├── README.md                    # Main readme
├── README_FINAL.md             # Final documentation
├── LICENSE                      # License file
└── PROJECT_STRUCTURE.md        # This file (NEW)
```

## Key Changes from Original Structure

### Before Modularization (December 2024)
- **Single monolithic file**: `ollama_guard_proxy.py` (1971 lines)
- All code mixed together at root level
- Scripts, configs, and source code mixed at root
- Difficult to maintain and navigate

### After Modularization (January 2025)
- **7 focused modules** in `src/` directory
- **87.7% reduction** in main file (1971 → 242 lines)
- Clean separation of concerns
- Professional folder structure following Python best practices

## Module Descriptions

### Source Code (`src/`)

#### Core Application
- **`ollama_guard_proxy.py`** (242 lines)
  - Main FastAPI application entry point
  - App initialization with lifespan management
  - Middleware configuration (IP whitelist, logging)
  - Router registration
  - Component initialization (config, guard manager, cache, concurrency)

#### HTTP Layer
- **`http_client.py`** (74 lines)
  - Singleton HTTP client with connection pooling
  - Request forwarding utilities
  - Safe JSON parsing

- **`streaming_handlers.py`** (562 lines)
  - Stream processing for Ollama and OpenAI responses
  - Guard scanning integration for streaming
  - Connection cleanup on blocking
  - Three handlers: Ollama, OpenAI Chat, OpenAI Completions

#### API Endpoints
- **`endpoints_ollama.py`** (534 lines)
  - 12 Ollama API endpoints
  - `/api/generate`, `/api/chat`, `/api/pull`, `/api/push`, `/api/create`
  - `/api/tags`, `/api/show`, `/api/delete`, `/api/copy`
  - `/api/embed`, `/api/ps`, `/api/version`

- **`endpoints_openai.py`** (535 lines)
  - 4 OpenAI-compatible endpoints
  - `/v1/chat/completions` (streaming + non-streaming)
  - `/v1/completions` (streaming + non-streaming)
  - `/v1/embeddings`
  - `/v1/models`

- **`endpoints_admin.py`** (172 lines)
  - 9 admin and monitoring endpoints
  - `/health`, `/config`, `/stats`
  - `/admin/cache/clear`, `/admin/cache/cleanup`
  - `/queue/stats`, `/queue/memory`
  - `/admin/queue/reset`, `/admin/queue/update`

#### Utilities
- **`utils.py`** (114 lines)
  - Extract client IP from request
  - Extract model/text from payloads
  - Build Ollama options from OpenAI payloads
  - Text combination and extraction utilities

#### Core Services
- **`guard_manager.py`** - LLM Guard integration with input/output scanners
- **`cache.py`** - Caching layer (Redis + in-memory fallback)
- **`concurrency.py`** - Per-model concurrency control (Ollama-style)
- **`config.py`** - Configuration loading and management
- **`ip_whitelist.py`** - IP whitelist middleware for security
- **`language.py`** - Language detection for error messages

### Scripts (`scripts/`)

All executable scripts for running and managing the proxy:

- **`run_proxy.sh`** - Linux/Unix runner with process management (start/stop/restart/status/logs)
- **`run_proxy.bat`** - Windows runner with virtual environment support
- **`run_proxy_macos.sh`** - macOS runner optimized for Apple Silicon (M1/M2/M3)
- **`deploy-nginx.sh/bat`** - Nginx deployment scripts
- **`setup_concurrency.sh/bat`** - Concurrency setup scripts
- **`download_models.sh`** - Download LLM Guard models

### Configuration (`config/`)

- **`config.yaml`** - Main application configuration
  - Guard scanner settings
  - Cache configuration
  - Concurrency settings
  - Logging configuration

- **`nginx-ollama-production.conf`** - Nginx reverse proxy configuration

### Entry Point

**`main.py`** - Application entry point at project root
- Adds `src/` to Python path
- Imports and runs the FastAPI application
- Usage: `python main.py`

## Running the Application

### Using main.py (Recommended)
```bash
cd guardrails
python main.py
```

### Using scripts (Process Management)
```bash
# Linux/Unix
cd guardrails
./scripts/run_proxy.sh start     # Start as background service
./scripts/run_proxy.sh status    # Check status
./scripts/run_proxy.sh logs      # View logs
./scripts/run_proxy.sh stop      # Stop service

# Windows
cd guardrails
.\scripts\run_proxy.bat

# macOS (Apple Silicon optimized)
cd guardrails
./scripts/run_proxy_macos.sh start
```

### Using uvicorn directly
```bash
cd guardrails
uvicorn src.ollama_guard_proxy:app --host 0.0.0.0 --port 8080
```

### Using Docker
```bash
cd guardrails
docker-compose up -d
```

## Import Structure

All imports now use the `src` package:

```python
# In application code
from src.ollama_guard_proxy import app, config
from src.utils import extract_client_ip
from src.guard_manager import GuardManager
from src.cache import get_cache
```

## Development Workflow

### Setting up Development Environment

1. **Clone repository**
```bash
git clone <repository>
cd guardrails
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure application**
```bash
cp config/config.yaml.example config/config.yaml  # If example exists
# Edit config/config.yaml as needed
```

5. **Run in development mode**
```bash
python main.py
# or with auto-reload
uvicorn src.ollama_guard_proxy:app --reload
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test
python tests/test_output_scanner_fix.py
```

### Adding New Features

1. **New endpoint module**: Add to appropriate file in `src/`:
   - Ollama endpoints → `endpoints_ollama.py`
   - OpenAI endpoints → `endpoints_openai.py`
   - Admin endpoints → `endpoints_admin.py`

2. **New utility function**: Add to `src/utils.py`

3. **New service/manager**: Create new file in `src/` and import in `ollama_guard_proxy.py`

## Docker Structure

### Dockerfile Updates

Both `Dockerfile` and `Dockerfile.macos` have been updated to use the new structure:

```dockerfile
# Copy new structure
COPY main.py .
COPY src/ ./src/
COPY config/ ./config/
COPY requirements.txt .

# Run with main.py
CMD ["python", "main.py"]
```

### Docker Compose

No changes needed to `docker-compose.yml` files - they reference the Dockerfiles which have been updated.

## Performance Improvements

### Modularization Benefits
- **Maintainability**: 87.7% reduction in main file size
- **Clarity**: Each module has single responsibility
- **Testability**: Easier to test individual components
- **Scalability**: Easy to add new features without cluttering main file

### Connection Cleanup
- Immediate connection close when content is blocked
- 93% faster resource cleanup (from 30-60s to 2-3s)
- Implemented in all streaming handlers

### Concurrency
- Per-model concurrency limits (Ollama-style)
- Queue management with configurable limits
- Automatic parallelism based on available RAM

## Migration Notes

### For Existing Deployments

If upgrading from the old structure:

1. **Update Docker images**:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

2. **Update systemd services** (if used):
```ini
[Service]
ExecStart=/path/to/venv/bin/python /path/to/guardrails/main.py
WorkingDirectory=/path/to/guardrails
```

3. **Update shell scripts**:
- Use `./scripts/run_proxy.sh` instead of `./run_proxy.sh`
- All scripts automatically reference new paths

### Import Changes

If you have custom code importing from the old structure:

```python
# Old import
from ollama_guard_proxy import app

# New import
from src.ollama_guard_proxy import app
```

## Best Practices

### File Organization
- **Source code** → `src/`
- **Scripts** → `scripts/`
- **Configuration** → `config/`
- **Tests** → `tests/`
- **Documentation** → `docs/`
- **Docker files** → Root or `docker/` (optional)

### Module Guidelines
- Keep modules focused (single responsibility)
- Avoid circular imports
- Use factory functions for router creation
- Use dependency injection for shared services

### Configuration
- Store all configuration in `config/` directory
- Use environment variables for sensitive data
- Document all configuration options

### Scripts
- Make scripts executable: `chmod +x scripts/*.sh`
- Use absolute paths from `PROJECT_ROOT`
- Support both foreground and background modes

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: 
- Use `python main.py` instead of `python src/ollama_guard_proxy.py`
- Or add to PYTHONPATH: `export PYTHONPATH=/path/to/guardrails:$PYTHONPATH`

### Config File Not Found

**Problem**: `FileNotFoundError: config.yaml not found`

**Solution**:
- Config should be in `config/config.yaml`
- Scripts automatically set `CONFIG_FILE` environment variable
- If running manually: `CONFIG_FILE=config/config.yaml python main.py`

### Scripts Not Executable

**Problem**: `Permission denied: ./scripts/run_proxy.sh`

**Solution**:
```bash
chmod +x scripts/*.sh
```

## Version History

### v2.0 (January 2025) - Major Refactoring
- Modularized monolithic codebase (1971 → 242 lines main file)
- Reorganized folder structure (src/, scripts/, config/)
- Created main.py entry point
- Updated all scripts and Docker files
- Fixed FastAPI lifespan handling
- Fixed output scanner signature
- Improved connection cleanup (93% faster)

### v1.0 (December 2024) - Initial Release
- Monolithic codebase
- Basic guard functionality
- Ollama and OpenAI API support

---

For more information, see:
- [README.md](README.md) - Getting started guide
- [README_FINAL.md](README_FINAL.md) - Complete documentation
- [docs/](docs/) - Detailed documentation
