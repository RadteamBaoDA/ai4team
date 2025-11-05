# Tiktoken Offline Mode - Quick Reference

## 🚀 Quick Start (Choose One)

### Option 1: Using Shell Script
```bash
./init_tiktoken.sh
```

### Option 2: Using Batch Script
```batch
init_tiktoken.bat
```

### Option 3: Using Python CLI
```bash
python -m ollama_guardrails tiktoken-download
```

### Option 4: Using Python Script
```bash
python setup_tiktoken.py
```

## ✅ Verify Installation

```bash
python -m ollama_guardrails tiktoken-info
```

Expected output:
```
Tiktoken Offline Cache Configuration:
  Cache Directory: /path/to/models/tiktoken
  Directory Exists: True
  Offline Mode: True
  Cache Size: 2.45 MB
  Cached Files (4):
    - cl100k_base.tiktoken
    - p50k_base.tiktoken
    - p50k_edit.tiktoken
    - r50k_base.tiktoken
```

## 🎯 Start Server

```bash
# Automatic - uses local cache
python -m ollama_guardrails server
ollama-guardrails server
```

## 🔧 Custom Cache Location

```bash
# Set environment variable
export TIKTOKEN_CACHE_DIR=/custom/path

# Download to custom location
python -m ollama_guardrails tiktoken-download -d /custom/path

# Start server
python -m ollama_guardrails server
```

## 📋 CLI Commands

```bash
# Show cache info
python -m ollama_guardrails tiktoken-info

# Download all default encodings
python -m ollama_guardrails tiktoken-download

# Download specific encodings
python -m ollama_guardrails tiktoken-download -e cl100k_base p50k_base

# Custom cache directory
python -m ollama_guardrails tiktoken-download -d ./models/tiktoken

# Verbose output
python -m ollama_guardrails tiktoken-download -v
```

## 🐳 Docker

```dockerfile
ENV TIKTOKEN_CACHE_DIR=/app/models/tiktoken
RUN python -m ollama_guardrails tiktoken-download -d /app/models/tiktoken
```

## 🐍 Python API

```python
from ollama_guardrails.utils.tiktoken_cache import (
    setup_tiktoken_offline_mode,
    download_tiktoken_encoding,
    get_tiktoken_cache_info,
)

# Setup BEFORE importing tiktoken
setup_tiktoken_offline_mode('./models/tiktoken')

# Download specific encoding
download_tiktoken_encoding('cl100k_base')

# Check cache status
info = get_tiktoken_cache_info()
print(f"Cache size: {info['cache_size_mb']} MB")
```

## 🌍 Environment Variables

```bash
# Cache directory (default: ./models/tiktoken)
export TIKTOKEN_CACHE_DIR=/path/to/cache

# Enable offline mode (default: true)
export TIKTOKEN_OFFLINE_MODE=true

# Enable local fallback (default: true)  
export TIKTOKEN_FALLBACK_LOCAL=true
```

## 📚 Documentation

- **Setup Guide**: [docs/TIKTOKEN_SETUP_GUIDE.md](docs/TIKTOKEN_SETUP_GUIDE.md)
- **Full Reference**: [docs/TIKTOKEN_OFFLINE_MODE.md](docs/TIKTOKEN_OFFLINE_MODE.md)
- **Implementation**: [docs/TIKTOKEN_IMPLEMENTATION_SUMMARY.md](docs/TIKTOKEN_IMPLEMENTATION_SUMMARY.md)

## ❓ Common Issues

| Issue | Solution |
|-------|----------|
| "encoding not found" | Run `python -m ollama_guardrails tiktoken-download` |
| "Permission denied" | Ensure cache directory is writable: `chmod 755 models/tiktoken` |
| "Slow first load" | Normal - downloads and caches encodings (1-2 minutes) |
| "TIKTOKEN_CACHE_DIR not working" | Set env var BEFORE running: `export TIKTOKEN_CACHE_DIR=...` then run |

## 📊 Supported Encodings

| Encoding | Model | Recommended |
|----------|-------|-------------|
| `cl100k_base` | GPT-4, GPT-3.5-turbo | ⭐ Yes |
| `p50k_base` | GPT-3, GPT-3.5 | Legacy |
| `p50k_edit` | Edit operations | Legacy |
| `r50k_base` | Text-davinci-002 | Legacy |

## ⚡ Performance

- **Download**: 1-2 minutes (first run)
- **Cache size**: 6-8 MB total
- **Initialization**: <100ms after first use
- **Token counting**: <1ms per operation

## 🔗 Files Created/Modified

### New Files
- `src/ollama_guardrails/utils/tiktoken_cache.py` - Core implementation
- `setup_tiktoken.py` - Standalone setup script
- `init_tiktoken.sh` - Linux/macOS setup
- `init_tiktoken.bat` - Windows setup
- `docs/TIKTOKEN_OFFLINE_MODE.md` - Full reference
- `docs/TIKTOKEN_SETUP_GUIDE.md` - Setup guide
- `docs/TIKTOKEN_IMPLEMENTATION_SUMMARY.md` - Implementation details

### Modified Files
- `src/ollama_guardrails/cli.py` - Added tiktoken commands
- `src/ollama_guardrails/guards/guard_manager.py` - Initialize offline mode
- `src/ollama_guardrails/utils/__init__.py` - Export tiktoken functions
- `README.md` - Updated with offline mode info

## 🎓 Next Steps

1. **Download encodings**: `python -m ollama_guardrails tiktoken-download`
2. **Verify setup**: `python -m ollama_guardrails tiktoken-info`
3. **Start server**: `python -m ollama_guardrails server`
4. **Read guide**: [docs/TIKTOKEN_SETUP_GUIDE.md](docs/TIKTOKEN_SETUP_GUIDE.md)

---

For complete documentation, see the setup guide and offline mode reference.
