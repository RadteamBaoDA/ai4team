# Tiktoken Offline Mode - Setup Guide

This guide provides step-by-step instructions for setting up tiktoken offline mode in the Ollama Guardrails system.

## Why Offline Mode?

By default, `tiktoken` (used by `llm-guard` for token counting) downloads encoding files from Azure. In offline environments or to improve reliability, you can configure it to use a local cache directory.

## Quick Setup (5 minutes)

### Step 1: Download Tiktoken Encodings

```bash
# Navigate to guardrails directory
cd ai4team/guardrails

# Download all common encodings (recommended)
python -m ollama_guardrails tiktoken-download

# Or download to a custom location
python -m ollama_guardrails tiktoken-download -d /custom/path/to/models/tiktoken
```

### Step 2: Verify Setup

```bash
# Check your tiktoken cache
python -m ollama_guardrails tiktoken-info

# Expected output:
# Tiktoken Offline Cache Configuration:
#   Cache Directory: /path/to/models/tiktoken
#   Directory Exists: True
#   Offline Mode: True
#   Fallback Local: True
#   Cache Size: 2.45 MB
#   Cached Files (4):
#     - cl100k_base.tiktoken
#     - p50k_base.tiktoken
#     - p50k_edit.tiktoken
#     - r50k_base.tiktoken
```

### Step 3: Start the Application

```bash
# The offline mode is automatically initialized
python -m ollama_guardrails server

# Or with custom cache location
export TIKTOKEN_CACHE_DIR=/custom/path/to/models/tiktoken
python -m ollama_guardrails server
```

## Advanced Setup

### Custom Cache Directory

```bash
# Set environment variable before running
export TIKTOKEN_CACHE_DIR=/path/to/custom/cache
python -m ollama_guardrails tiktoken-download

# Verify with custom location
python -m ollama_guardrails tiktoken-info
```

### Download Specific Encodings

```bash
# Download only specific encodings
python -m ollama_guardrails tiktoken-download -e cl100k_base p50k_base

# Download to custom location
python -m ollama_guardrails tiktoken-download \
  -e cl100k_base p50k_base p50k_edit r50k_base \
  -d ./models/tiktoken_custom
```

### Programmatic Setup

```python
from ollama_guardrails.utils.tiktoken_cache import (
    setup_tiktoken_offline_mode,
    download_tiktoken_encoding,
)

# Call BEFORE importing tiktoken or llm-guard
setup_tiktoken_offline_mode('./models/tiktoken')

# Download additional encodings if needed
download_tiktoken_encoding('cl100k_base', './models/tiktoken')

# Now safe to use tiktoken or llm-guard
from llm_guard.input_scanners import TokenLimit
```

## Environment Variables

Control tiktoken behavior with these variables:

```bash
# Set cache directory
export TIKTOKEN_CACHE_DIR=/path/to/cache

# Enable/disable offline mode (default: true)
export TIKTOKEN_OFFLINE_MODE=true

# Enable/disable local fallback (default: true)
export TIKTOKEN_FALLBACK_LOCAL=true

# Then start the application
python -m ollama_guardrails server
```

## Docker Setup

### Dockerfile

```dockerfile
FROM python:3.9-slim

# Install guardrails
COPY guardrails /app/guardrails
WORKDIR /app/guardrails
RUN pip install -e .

# Setup tiktoken cache
ENV TIKTOKEN_CACHE_DIR=/app/models/tiktoken
RUN python -m ollama_guardrails tiktoken-download -d /app/models/tiktoken

# Start server
CMD ["python", "-m", "ollama_guardrails", "server"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  guardrails:
    build: .
    ports:
      - "8080:8080"
    environment:
      OLLAMA_URL: "http://ollama:11434"
      TIKTOKEN_CACHE_DIR: "/app/models/tiktoken"
      TIKTOKEN_OFFLINE_MODE: "true"
    volumes:
      - ./models/tiktoken:/app/models/tiktoken
```

### Build with Pre-cached Models

```bash
# Create cache directory
mkdir -p models/tiktoken

# Download encodings locally
python -m ollama_guardrails tiktoken-download -d ./models/tiktoken

# Build Docker image (models will be copied)
docker build -t ollama-guardrails:offline .

# Run with mounted cache
docker run -p 8080:8080 \
  -v $(pwd)/models/tiktoken:/app/models/tiktoken \
  ollama-guardrails:offline
```

## Troubleshooting

### Issue: "tiktoken encoding not found"

```bash
# Download the required encodings
python -m ollama_guardrails tiktoken-download

# Or download to specific location
python -m ollama_guardrails tiktoken-download -d ./models/tiktoken
```

### Issue: "Permission denied" error

```bash
# Ensure cache directory is writable
mkdir -p models/tiktoken
chmod 755 models/tiktoken

# Download with explicit path
python -m ollama_guardrails tiktoken-download -d ./models/tiktoken
```

### Issue: "TIKTOKEN_CACHE_DIR not recognized"

Ensure the environment variable is set BEFORE running the application:

```bash
# Correct (works):
export TIKTOKEN_CACHE_DIR=/path/to/cache
python -m ollama_guardrails server

# Incorrect (won't work):
python -m ollama_guardrails server
export TIKTOKEN_CACHE_DIR=/path/to/cache
```

### Issue: Large file downloads/slow initialization

This is normal on first run. Subsequent runs will use cached encodings:

```bash
# First run (downloads and caches)
python -m ollama_guardrails tiktoken-download  # Takes 1-2 minutes

# Verify cache is working
python -m ollama_guardrails tiktoken-info

# Subsequent runs (instant)
python -m ollama_guardrails server  # Uses cached encodings
```

## File Structure After Setup

```
guardrails/
├── models/
│   └── tiktoken/
│       ├── cl100k_base.tiktoken      # ~2.5 MB
│       ├── p50k_base.tiktoken        # ~1.6 MB
│       ├── p50k_edit.tiktoken        # ~1.6 MB
│       └── r50k_base.tiktoken        # ~0.9 MB
├── setup_tiktoken.py
├── src/
│   └── ollama_guardrails/
│       ├── guards/
│       │   └── guard_manager.py       # Uses offline tiktoken
│       └── utils/
│           └── tiktoken_cache.py      # Offline mode configuration
└── ...
```

## Encodings Reference

Common tiktoken encodings available for download:

| Encoding | Size | Model | Notes |
|----------|------|-------|-------|
| `cl100k_base` | 2.5 MB | GPT-4, GPT-3.5-turbo | **Recommended** - Most current |
| `p50k_base` | 1.6 MB | GPT-3, GPT-3.5 | Legacy encoding |
| `p50k_edit` | 1.6 MB | Edit operations | For completions |
| `r50k_base` | 0.9 MB | Text-davinci-002 | Legacy encoding |

## Performance Characteristics

- **Download time**: 1-2 minutes (first run only)
- **Cache size**: ~6-8 MB total for all encodings
- **Memory usage**: ~100 MB when loaded
- **Initialization**: <100ms (after first use)
- **Token counting**: <1ms per operation

## API Reference

See [Tiktoken Offline Mode Documentation](TIKTOKEN_OFFLINE_MODE.md) for complete API reference and advanced usage.

## Integration with Application

The offline mode is automatically initialized when:

1. `ollama_guardrails.cli` module is imported
2. `ollama_guardrails.guards.guard_manager` module is imported
3. `setup_tiktoken_offline_mode()` is called explicitly

This ensures tiktoken uses local cache for all operations:

```python
from ollama_guardrails.guards.guard_manager import LLMGuardManager

# Automatically uses offline tiktoken configuration
manager = LLMGuardManager()

# TokenLimit scanner uses cached encodings
result = await manager.scan_input("Your prompt")
```

## Next Steps

1. ✅ Download encodings: `python -m ollama_guardrails tiktoken-download`
2. ✅ Verify setup: `python -m ollama_guardrails tiktoken-info`
3. ✅ Start server: `python -m ollama_guardrails server`
4. 📖 Read full documentation: [TIKTOKEN_OFFLINE_MODE.md](TIKTOKEN_OFFLINE_MODE.md)

## Support

For issues or questions:
- Check [TIKTOKEN_OFFLINE_MODE.md](TIKTOKEN_OFFLINE_MODE.md) for detailed documentation
- Review troubleshooting section above
- Open an issue on GitHub: [RadteamBaoDA/ai4team](https://github.com/RadteamBaoDA/ai4team/issues)
