# Offline Mode Update - Tiktoken + Hugging Face

## 🎯 What's New

Updated all scripts and source code to support **offline mode for both**:
- ✅ **Tiktoken** - OpenAI token encoding caching
- ✅ **Hugging Face** - Transformer models and datasets caching

## 📦 New Modules & Components

### 1. Hugging Face Cache Module
**File**: `src/ollama_guardrails/utils/huggingface_cache.py`

**Functions**:
- `setup_huggingface_offline_mode()` - Configure HF offline mode
- `ensure_huggingface_cache_dir()` - Create cache directories
- `download_huggingface_model()` - Download specific models
- `get_huggingface_cache_info()` - Retrieve cache information
- `init_huggingface_with_retry()` - Initialize with retry logic

**Environment Variables**:
```bash
HF_HOME                  # Hugging Face home directory
HF_OFFLINE              # Enable offline mode
TRANSFORMERS_OFFLINE    # Transformers offline mode
HF_DATASETS_OFFLINE     # Datasets offline mode
HF_HUB_OFFLINE          # Hub offline mode
TRANSFORMERS_CACHE      # Transformers cache directory
HF_DATASETS_CACHE       # Datasets cache directory
```

### 2. Updated Tiktoken Module
**File**: `src/ollama_guardrails/utils/tiktoken_cache.py`

**Enhancement**: Now initializes Hugging Face offline mode automatically when called

### 3. New CLI Commands

#### Hugging Face Info
```bash
python -m ollama_guardrails hf-info
```
Shows Hugging Face cache configuration and statistics

#### Hugging Face Download
```bash
python -m ollama_guardrails hf-download -m model_id1 model_id2
python -m ollama_guardrails hf-download -m bert-base-uncased
python -m ollama_guardrails hf-download -d /custom/path -m sentence-transformers/all-mpnet-base-v2
```

## 🔧 Updated Scripts

### 1. Python Setup Script
**File**: `setup_tiktoken.py` (Updated)

**New Features**:
```bash
# Setup both tiktoken and HF with defaults
python setup_tiktoken.py

# Setup with custom cache location
python setup_tiktoken.py /path/to/models

# Setup both with specific models
python setup_tiktoken.py --models bert-base-uncased sentence-transformers/all-mpnet-base-v2

# Skip tiktoken or HF
python setup_tiktoken.py --skip-hf          # Only setup tiktoken
python setup_tiktoken.py --skip-tiktoken    # Only setup HF

# Verbose output
python setup_tiktoken.py -v
```

### 2. Linux/macOS Bash Script
**File**: `init_tiktoken_new.sh` (New)

**Features**:
```bash
# Setup both
./init_tiktoken_new.sh

# Setup with custom cache location
./init_tiktoken_new.sh ./models

# Skip certain components
./init_tiktoken_new.sh --skip-tiktoken
./init_tiktoken_new.sh --skip-hf

# Download specific HF models
./init_tiktoken_new.sh ./models --models bert-base-uncased
```

### 3. Windows Batch Script
**File**: `init_all_offline.bat` (New)

**Features**:
```batch
REM Setup both
init_all_offline.bat

REM Setup with custom cache location
init_all_offline.bat models

REM Skip certain components
init_all_offline.bat --skip-tiktoken
init_all_offline.bat --skip-hf

REM Download HF models
init_all_offline.bat models --models bert-base-uncased
```

## 📊 Updated CLI Commands

### Tiktoken Commands
```bash
python -m ollama_guardrails tiktoken-info                              # Show tiktoken cache info
python -m ollama_guardrails tiktoken-download                          # Download all encodings
python -m ollama_guardrails tiktoken-download -e cl100k_base           # Download specific
python -m ollama_guardrails tiktoken-download -d /custom/path          # Custom location
```

### Hugging Face Commands (NEW)
```bash
python -m ollama_guardrails hf-info                                    # Show HF cache info
python -m ollama_guardrails hf-download -m model_id                    # Download model
python -m ollama_guardrails hf-download -m model1 model2 model3        # Download multiple
python -m ollama_guardrails hf-download -d /custom/path -m model_id    # Custom location
```

## 🌍 Environment Variables (Complete List)

### Tiktoken
```bash
TIKTOKEN_CACHE_DIR=./models/tiktoken          # Cache directory (default)
TIKTOKEN_OFFLINE_MODE=true                    # Enable offline mode
TIKTOKEN_FALLBACK_LOCAL=true                  # Use local fallback
```

### Hugging Face
```bash
HF_HOME=./models/huggingface                  # Home directory (default)
HF_OFFLINE=true                               # Enable offline mode
TRANSFORMERS_OFFLINE=1                        # Transformers offline
HF_DATASETS_OFFLINE=1                         # Datasets offline
HF_HUB_OFFLINE=1                              # Hub offline
TRANSFORMERS_CACHE=./models/huggingface/transformers
HF_DATASETS_CACHE=./models/huggingface/datasets
```

## 📁 Directory Structure

After running setup scripts:

```
models/
├── tiktoken/                              # Tiktoken encodings
│   ├── cl100k_base.tiktoken              # GPT-4 encoding (~2.5 MB)
│   ├── p50k_base.tiktoken                # GPT-3 encoding (~1.6 MB)
│   ├── p50k_edit.tiktoken                # Edit encoding (~1.6 MB)
│   └── r50k_base.tiktoken                # Legacy encoding (~0.9 MB)
└── huggingface/                           # Hugging Face models
    ├── transformers/                      # Transformer models
    │   └── [model-cache-structure]/
    └── datasets/                          # Datasets
        └── [dataset-cache-structure]/
```

## 🚀 Quick Start Commands

### One-liner Setup (All Platforms)

```bash
# Python - Setup everything
python setup_tiktoken.py ./models -e cl100k_base p50k_base --models bert-base-uncased

# Linux/macOS
./init_tiktoken_new.sh

# Windows
init_all_offline.bat

# Then verify
python -m ollama_guardrails tiktoken-info
python -m ollama_guardrails hf-info

# Start server
python -m ollama_guardrails server
```

## 🔄 Updated Files

### New Files
- ✅ `src/ollama_guardrails/utils/huggingface_cache.py` - HF offline configuration
- ✅ `setup_tiktoken.py` - Updated with HF support
- ✅ `init_tiktoken_new.sh` - Updated bash script
- ✅ `init_all_offline.bat` - Updated batch script
- ✅ `OFFLINE_MODE_UPDATE.md` - This file

### Modified Files
- ✅ `src/ollama_guardrails/cli.py` - Added HF commands
- ✅ `src/ollama_guardrails/utils/tiktoken_cache.py` - HF integration
- ✅ `src/ollama_guardrails/utils/__init__.py` - Exported HF functions
- ✅ `README.md` - Updated offline mode section

## 💡 Usage Examples

### Example 1: Complete Offline Setup
```bash
# Download everything to ./models
python setup_tiktoken.py ./models \
    -e cl100k_base p50k_base p50k_edit r50k_base \
    --models bert-base-uncased sentence-transformers/all-mpnet-base-v2
```

### Example 2: Using CLI Commands Separately
```bash
# Setup tiktoken
python -m ollama_guardrails tiktoken-download -d ./models/tiktoken

# Setup HF
python -m ollama_guardrails hf-download -d ./models/huggingface \
    -m bert-base-uncased sentence-transformers/all-mpnet-base-v2
```

### Example 3: Docker Setup
```dockerfile
# Download both offline caches
RUN python -m ollama_guardrails tiktoken-download -d /app/models/tiktoken
RUN python -m ollama_guardrails hf-download -d /app/models/huggingface \
    -m bert-base-uncased

# Set environment variables
ENV TIKTOKEN_CACHE_DIR=/app/models/tiktoken
ENV HF_HOME=/app/models/huggingface
ENV HF_OFFLINE=true
```

### Example 4: Docker Compose
```yaml
version: '3.8'
services:
  guardrails:
    build: .
    environment:
      TIKTOKEN_CACHE_DIR: /app/models/tiktoken
      HF_HOME: /app/models/huggingface
      HF_OFFLINE: "true"
      TRANSFORMERS_OFFLINE: "1"
    volumes:
      - ./models/tiktoken:/app/models/tiktoken
      - ./models/huggingface:/app/models/huggingface
```

## 📈 Statistics

| Metric | Value |
|--------|-------|
| **Tiktoken Cache Size** | ~6-8 MB (all encodings) |
| **HF Models (varies)** | Depends on model size |
| **Setup Time** | 2-5 minutes (one-time) |
| **Network Usage** | One-time download only |
| **Runtime Network** | Zero (fully offline) |

## ✨ Benefits

✅ **Complete Offline Operation** - No internet needed after setup  
✅ **Multiple Model Support** - Download any HF model  
✅ **Automatic Initialization** - Offline mode loads automatically  
✅ **Environment Control** - Set via environment variables  
✅ **Cross-Platform** - Windows, Linux, macOS support  
✅ **Docker Ready** - Works in containers  
✅ **Easy Management** - CLI commands for cache management  

## 🔐 Security & Performance

- 🔒 No external downloads at runtime
- ⚡ Faster initialization (uses local cache)
- 📦 Efficient caching strategies
- 🛡️ Secure offline operation
- 🔄 Automatic fallback handling

## 📝 Configuration Priority

Environment variables are loaded in this order:
1. Explicit OS environment variables (highest priority)
2. Script default values
3. Hardcoded defaults (lowest priority)

```bash
# This will be used
export TIKTOKEN_CACHE_DIR=/custom/path
python -m ollama_guardrails server

# This will be ignored if env var is set
# (even if script default is different)
```

## 🧪 Verification

After setup, verify everything works:

```bash
# Check tiktoken cache
python -m ollama_guardrails tiktoken-info

# Check HF cache
python -m ollama_guardrails hf-info

# Start server and test
python -m ollama_guardrails server
```

Expected output should show:
- ✅ Cache directories exist
- ✅ Offline mode: true
- ✅ Files cached
- ✅ Cache sizes

## 📚 Related Documentation

- Full Tiktoken Guide: `docs/TIKTOKEN_SETUP_GUIDE.md`
- Offline Mode Reference: `docs/TIKTOKEN_OFFLINE_MODE.md`
- Implementation Details: `docs/TIKTOKEN_IMPLEMENTATION_SUMMARY.md`

## 🤝 Support

For issues or questions:
1. Run `python -m ollama_guardrails --help`
2. Check cache status: `tiktoken-info` and `hf-info`
3. Review setup guide: `docs/TIKTOKEN_SETUP_GUIDE.md`
4. Open GitHub issue: [RadteamBaoDA/ai4team](https://github.com/RadteamBaoDA/ai4team/issues)

---

**Version**: 1.1 (Updated with Hugging Face Support)  
**Date**: November 2024  
**Status**: ✅ Production Ready
