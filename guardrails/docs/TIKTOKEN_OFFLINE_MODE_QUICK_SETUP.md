# Tiktoken & Hugging Face Offline Mode - Quick Reference

## What Changed in app.py

The `app.py` file now:
1. ✅ Initializes tiktoken offline mode on startup
2. ✅ Initializes Hugging Face offline mode on startup
3. ✅ Reads environment variables for cache paths
4. ✅ Logs offline mode configuration at startup
5. ✅ Supports CPU-only mode forcing

## Environment Variables - All You Need

### Minimal Setup
```bash
# Just enable offline mode (uses ./models by default)
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true
```

### Custom Paths
```bash
export TIKTOKEN_CACHE_DIR=/data/tiktoken
export HF_HOME=/data/huggingface
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true
```

### Complete (Recommended)
```bash
export TIKTOKEN_CACHE_DIR=./models/tiktoken
export TIKTOKEN_OFFLINE_MODE=true
export HF_HOME=./models/huggingface
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export HF_DATASETS_OFFLINE=true
```

### With CPU Only
```bash
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true
export LLM_GUARD_FORCE_CPU=true
```

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `TIKTOKEN_CACHE_DIR` | `./models/tiktoken` | Where tiktoken cache lives |
| `TIKTOKEN_OFFLINE_MODE` | `true` | Enable tiktoken offline |
| `HF_HOME` | `./models/huggingface` | Where HF cache lives |
| `HF_OFFLINE` | `true` | Enable HF offline |
| `TRANSFORMERS_OFFLINE` | `true` | Enable transformers offline |
| `HF_DATASETS_OFFLINE` | `true` | Enable datasets offline |
| `TRANSFORMERS_CACHE` | `./models/huggingface/transformers` | Transformers model path |
| `HF_DATASETS_CACHE` | `./models/huggingface/datasets` | Datasets cache path |
| `LLM_GUARD_FORCE_CPU` | `false` | Force CPU-only mode |

## How It Works

### Startup Sequence
```
1. app.py imported
   ↓
2. Tiktoken offline mode initialized (if enabled)
   ↓
3. HF offline mode initialized (if enabled)
   ↓
4. CPU forcing applied (if enabled)
   ↓
5. Logger initialized
   ↓
6. Offline config logged
   ↓
7. Application running
```

### What Gets Logged
```
Application starting up...
Offline mode configuration:
  - Tiktoken cache: ./models/tiktoken
  - Hugging Face cache: ./models/huggingface
Application startup complete
```

## Quick Start (4 Steps)

### Step 1: Download Models
```bash
./scripts/download_models.sh
```

### Step 2: Set Environment
```bash
export TIKTOKEN_OFFLINE_MODE=true
export HF_OFFLINE=true
```

### Step 3: Start Application
```bash
python -m ollama_guardrails
```

### Step 4: Verify
```bash
curl http://localhost:8080/health
```

## Key Points

✅ **Automatic initialization** - No manual code changes needed  
✅ **Environment-driven** - Configure via env variables  
✅ **Backward compatible** - Existing code still works  
✅ **Error handling** - Graceful fallback if offline mode fails  
✅ **Logging** - Startup shows offline configuration  

## Troubleshooting

### Models Not Found
```bash
# Verify cache exists
ls -la $TIKTOKEN_CACHE_DIR
ls -la $HF_HOME

# Download if missing
./scripts/download_models.sh
```

### Offline Mode Not Working
```bash
# Check environment variables are set
env | grep -E 'TIKTOKEN|HF_'

# Check they're exported (not just set)
export TIKTOKEN_OFFLINE_MODE=true
```

### Permission Errors
```bash
# Make cache readable/writable
chmod -R 755 ./models/
```

## Integration with Proxy Scripts

All proxy scripts automatically set these variables:
- `run_proxy.sh` (Linux)
- `run_proxy.bat` (Windows)
- `run_proxy_macos.sh` (macOS)

You can override them by setting them before running the script.

## Benefits

| Feature | Without | With |
|---------|---------|------|
| Downloads | From Azure/HF | From local cache |
| Startup Time | Slower (first time) | Faster |
| Offline Operation | ❌ No | ✅ Yes |
| Network Required | ✅ Yes | ❌ No (after setup) |
| Privacy | ⚠️ Data sent out | ✅ Fully local |

## Files Modified

- **app.py** - Added offline mode initialization
- **TIKTOKEN_CACHE_ENV_GUIDE.md** - Full configuration guide
- **APP_TIKTOKEN_CACHE_UPDATE.md** - Detailed update info

## Version

- **Status:** ✅ Production Ready
- **Version:** 2.6+
- **Compatible:** Python 3.9+

## One-Liner Setup

```bash
export TIKTOKEN_OFFLINE_MODE=true HF_OFFLINE=true && \
./scripts/download_models.sh && \
python -m ollama_guardrails
```

## See Also

- Complete guide: `TIKTOKEN_CACHE_ENV_GUIDE.md`
- Detailed update: `APP_TIKTOKEN_CACHE_UPDATE.md`
- Scripts update: `SCRIPTS_UPDATE.md`
- Offline mode: `OFFLINE_MODE_UPDATE.md`

---

**TL;DR:** Set `TIKTOKEN_OFFLINE_MODE=true` and `HF_OFFLINE=true` environment variables before starting app.py. Done! 🎉
