# Tiktoken & Hugging Face Cache Configuration Guide

## Overview

The Ollama Guardrails application now fully supports offline mode for both **Tiktoken** (token encoding) and **Hugging Face** (transformer models) using environment variables. This guide explains how to configure and use these offline caching features.

## Quick Start

### Minimal Setup (Uses Defaults)
```bash
# Just set offline mode to true (uses ./models/ by default)
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true

# Start the application
python -m ollama_guardrails
```

### Custom Cache Locations
```bash
# Set custom cache directories
export TIKTOKEN_CACHE_DIR=/data/tiktoken
export HF_HOME=/data/huggingface

# Enable offline mode
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true

# Start the application
python -m ollama_guardrails
```

## Environment Variables

### Tiktoken Offline Mode

| Variable | Default | Values | Description |
|----------|---------|--------|-------------|
| `TIKTOKEN_CACHE_DIR` | `./models/tiktoken` | Path | Directory to cache tiktoken encoding files |
| `TIKTOKEN_OFFLINE_MODE` | `true` | `true`, `false` | Enable/disable offline mode |
| `TIKTOKEN_FALLBACK_LOCAL` | `true` | `true`, `false` | Use local cache as fallback |

### Hugging Face Offline Mode

| Variable | Default | Values | Description |
|----------|---------|--------|-------------|
| `HF_HOME` | `./models/huggingface` | Path | Hugging Face home directory for caches |
| `HF_OFFLINE` | `true` | `true`, `false` | Enable offline mode for HF hub |
| `TRANSFORMERS_OFFLINE` | `true` | `true`, `false` | Enable offline mode for transformers |
| `HF_DATASETS_OFFLINE` | `true` | `true`, `false` | Enable offline mode for datasets |
| `HF_HUB_OFFLINE` | `true` | `true` | Enable offline hub mode |
| `TRANSFORMERS_CACHE` | `./models/huggingface/transformers` | Path | Transformers model cache directory |
| `HF_DATASETS_CACHE` | `./models/huggingface/datasets` | Path | Datasets cache directory |

### CPU Forcing (Optional)

| Variable | Default | Values | Description |
|----------|---------|--------|-------------|
| `LLM_GUARD_FORCE_CPU` | `false` | `true`, `false`, `1`, `0` | Force CPU-only mode for transformers |
| `LLM_GUARD_DEVICE` | `auto` | `cpu`, `cuda`, `mps`, `auto` | Device selection |

## Initialization Flow

When the application starts:

1. **Early Initialization (Before Logger)**
   - Tiktoken offline mode setup
   - Hugging Face offline mode setup
   - CPU forcing configuration

2. **Logger Initialization**
   - Setup logging system
   - Configure logging format

3. **Lifespan Startup (Application Startup)**
   - Log offline mode configuration
   - Display cache paths
   - Verify device settings
   - Initialize HTTP client
   - Initialize async components

## Configuration Examples

### Example 1: Development (Offline, CPU-only)
```bash
#!/bin/bash
export TIKTOKEN_CACHE_DIR=./models/tiktoken
export HF_HOME=./models/huggingface
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export LLM_GUARD_DEVICE=cpu

python -m ollama_guardrails
```

### Example 2: Production (Offline, GPU-Accelerated)
```bash
#!/bin/bash
export TIKTOKEN_CACHE_DIR=/opt/guardrails/cache/tiktoken
export HF_HOME=/opt/guardrails/cache/huggingface
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export LLM_GUARD_DEVICE=cuda

python -m ollama_guardrails
```

### Example 3: Air-Gapped Network (Maximum Offline)
```bash
#!/bin/bash
export TIKTOKEN_CACHE_DIR=/data/guardrails/tiktoken
export HF_HOME=/data/guardrails/huggingface
export TRANSFORMERS_CACHE=/data/guardrails/huggingface/transformers
export HF_DATASETS_CACHE=/data/guardrails/huggingface/datasets

export TIKTOKEN_OFFLINE_MODE=true
export TIKTOKEN_FALLBACK_LOCAL=true
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export HF_DATASETS_OFFLINE=true
export HF_HUB_OFFLINE=true

python -m ollama_guardrails
```

### Example 4: Docker Container
```dockerfile
FROM python:3.11

# Install dependencies
RUN pip install -r requirements.txt

# Set offline mode environment
ENV TIKTOKEN_CACHE_DIR=/data/models/tiktoken
ENV HF_HOME=/data/models/huggingface
ENV TIKTOKEN_OFFLINE_MODE=true
ENV HF_OFFLINE=true
ENV TRANSFORMERS_OFFLINE=true

# Mount volume for cached models
VOLUME ["/data/models"]

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "ollama_guardrails"]
```

### Example 5: Docker Compose
```yaml
version: '3.8'

services:
  guardrails:
    image: guardrails:latest
    ports:
      - "8080:8080"
    volumes:
      - ./models:/data/models
    environment:
      TIKTOKEN_CACHE_DIR: /data/models/tiktoken
      HF_HOME: /data/models/huggingface
      TIKTOKEN_OFFLINE_MODE: "true"
      HF_OFFLINE: "true"
      TRANSFORMERS_OFFLINE: "true"
      LLM_GUARD_DEVICE: cpu
```

## Startup Output

When you start the application with offline mode enabled, you'll see:

```
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Application starting up...
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Offline mode configuration:
2024-11-05 10:00:00 - ollama_guardrails.app - INFO -   - Tiktoken cache: ./models/tiktoken
2024-11-05 10:00:00 - ollama_guardrails.app - INFO -   - Hugging Face cache: ./models/huggingface
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Application startup complete
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Ollama URL: http://127.0.0.1:11434
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Input guard: enabled
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Output guard: enabled
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - Cache: enabled
2024-11-05 10:00:00 - ollama_guardrails.app - INFO - IP whitelist: disabled
```

## Setting Up Offline Cache

### Step 1: Download Offline Models

Use the provided download script:

```bash
# Download tiktoken encodings and HF models
./scripts/download_models.sh

# Or specify custom locations
./scripts/download_models.sh -d /data/models
```

### Step 2: Verify Cache Structure

```bash
# Check tiktoken cache
ls -la ./models/tiktoken/

# Check HF cache
ls -la ./models/huggingface/transformers/
ls -la ./models/huggingface/datasets/
```

### Step 3: Set Environment Variables

```bash
# Linux/macOS
export TIKTOKEN_CACHE_DIR=./models/tiktoken
export HF_HOME=./models/huggingface
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true

# Windows (PowerShell)
$env:TIKTOKEN_CACHE_DIR=".\models\tiktoken"
$env:HF_HOME=".\models\huggingface"
$env:TIKTOKEN_OFFLINE_MODE="true"
$env:HF_OFFLINE="true"
```

### Step 4: Start Application

```bash
# Development
python -m ollama_guardrails

# Production with gunicorn
gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 4 ollama_guardrails.app:app
```

## Troubleshooting

### Issue: "Model not found" in offline mode

**Solution:**
1. Verify cache directories exist:
   ```bash
   ls -la $TIKTOKEN_CACHE_DIR
   ls -la $HF_HOME
   ```

2. Download missing models:
   ```bash
   ./scripts/download_models.sh
   ```

3. Check environment variables:
   ```bash
   echo $TIKTOKEN_CACHE_DIR
   echo $HF_HOME
   ```

### Issue: Application tries to download from internet

**Solution:**
1. Ensure offline mode is enabled:
   ```bash
   export TIKTOKEN_OFFLINE_MODE=true
   export HF_OFFLINE=true
   ```

2. Check environment variables are exported (not just set):
   ```bash
   # Correct
   export TIKTOKEN_CACHE_DIR=./models/tiktoken
   
   # Incorrect (not exported to child processes)
   TIKTOKEN_CACHE_DIR=./models/tiktoken
   ```

3. Verify HF library respects offline mode:
   ```bash
   python -c "import os; os.environ['HF_OFFLINE']='true'; from transformers import AutoTokenizer; print('HF offline mode working')"
   ```

### Issue: Permission denied on cache directories

**Solution:**
```bash
# Make sure cache directories are readable/writable
chmod -R 755 ./models/tiktoken
chmod -R 755 ./models/huggingface
```

### Issue: Out of disk space

**Solution:**
Check cache sizes:
```bash
du -sh ./models/
du -sh ./models/tiktoken/
du -sh ./models/huggingface/
```

If cache is too large, delete unused models:
```bash
# Be careful - only delete unused models
rm -rf ./models/huggingface/transformers/unused-model/
```

## Integration with Scripts

All proxy runner scripts (`run_proxy.sh`, `run_proxy.bat`, `run_proxy_macos.sh`) automatically set offline mode environment variables:

```bash
# Linux/macOS - run_proxy.sh
export TIKTOKEN_CACHE_DIR="${TIKTOKEN_CACHE_DIR:-$PROJECT_ROOT/models/tiktoken}"
export TIKTOKEN_OFFLINE_MODE="${TIKTOKEN_OFFLINE_MODE:-true}"
export HF_HOME="${HF_HOME:-$PROJECT_ROOT/models/huggingface}"
export HF_OFFLINE="${HF_OFFLINE:-true}"
```

You can override these by setting environment variables before running the script.

## Performance Tips

1. **SSD Storage:** Cache tiktoken/HF models on SSD for faster access
2. **Local Network:** Mount cache via fast NFS on network for shared instances
3. **Preload Models:** Pre-download all needed models before production deployment
4. **Memory:** Allow models to be loaded into memory cache (first request slower, subsequent faster)

## Security Considerations

✅ **Offline Operation:** No data leaves your network when offline mode is enabled  
✅ **Local Models:** All models are local and under your control  
✅ **No API Keys:** No need for Hugging Face API tokens in offline mode  
✅ **Air-Gapped:** Suitable for classified/isolated networks  

## CLI Commands for Offline Mode

```bash
# Show tiktoken cache info
python -m ollama_guardrails tiktoken-info

# Download specific tiktoken encoding
python -m ollama_guardrails tiktoken-download -e cl100k_base

# Show HF cache info
python -m ollama_guardrails hf-info

# Download specific HF model
python -m ollama_guardrails hf-download -m bert-base-uncased
```

## Environment Variables Quick Reference

```bash
# Minimum offline configuration
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true

# Complete offline configuration
export TIKTOKEN_CACHE_DIR=./models/tiktoken
export TIKTOKEN_OFFLINE_MODE=true
export TIKTOKEN_FALLBACK_LOCAL=true
export HF_HOME=./models/huggingface
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export HF_DATASETS_OFFLINE=true
export HF_HUB_OFFLINE=true
export TRANSFORMERS_CACHE=./models/huggingface/transformers
export HF_DATASETS_CACHE=./models/huggingface/datasets
```

## Verification Script

```bash
#!/bin/bash
echo "=== Tiktoken & Hugging Face Offline Mode Verification ==="
echo ""
echo "Environment Variables:"
echo "  TIKTOKEN_CACHE_DIR: $TIKTOKEN_CACHE_DIR"
echo "  TIKTOKEN_OFFLINE_MODE: $TIKTOKEN_OFFLINE_MODE"
echo "  HF_HOME: $HF_HOME"
echo "  HF_OFFLINE: $HF_OFFLINE"
echo ""
echo "Cache Directory Status:"
[ -d "$TIKTOKEN_CACHE_DIR" ] && echo "  ✓ Tiktoken cache directory exists" || echo "  ✗ Tiktoken cache directory missing"
[ -d "$HF_HOME" ] && echo "  ✓ Hugging Face cache directory exists" || echo "  ✗ Hugging Face cache directory missing"
echo ""
echo "Cache Contents:"
echo "  Tiktoken files: $(ls -1 "$TIKTOKEN_CACHE_DIR" 2>/dev/null | wc -l)"
echo "  HF models: $(find "$HF_HOME" -maxdepth 1 -type d 2>/dev/null | wc -l)"
```

---

**Status:** ✅ Offline mode fully integrated in app.py  
**Version:** 2.6+  
**Compatible With:** Python 3.9+, FastAPI, Tiktoken, Transformers, LLM-Guard
