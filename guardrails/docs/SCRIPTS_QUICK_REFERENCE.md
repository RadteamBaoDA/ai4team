# Scripts - Offline Mode Quick Reference

## Essential Commands

### Setup & Download (First Time)
```bash
# 1. Setup environment
./scripts/setup_concurrency.sh

# 2. Download offline resources
./scripts/download_models.sh

# 3. Start proxy
./scripts/run_proxy.sh start
```

### Test Offline Operation
```bash
# Check proxy health
curl http://localhost:9999/health

# Stop proxy
./scripts/run_proxy.sh stop
```

## Production Deployment

```bash
# Deploy with Nginx load balancer (3 instances)
./scripts/deploy-nginx.sh start

# Check status
./scripts/deploy-nginx.sh status

# Stop all
./scripts/deploy-nginx.sh stop
```

## Download Options

```bash
# All models (tiktoken + HF + LLM Guard)
./scripts/download_models.sh

# Only offline resources (no LLM Guard)
./scripts/download_models.sh --skip-guard

# Specific encodings and models
./scripts/download_models.sh -e cl100k_base -m bert-base-uncased

# Dry run (no downloads)
./scripts/download_models.sh --dry-run
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TIKTOKEN_CACHE_DIR` | `./models/tiktoken` | Tiktoken cache location |
| `HF_HOME` | `./models/huggingface` | Hugging Face cache location |
| `TIKTOKEN_OFFLINE_MODE` | `true` | Enable offline mode |
| `HF_OFFLINE` | `true` | HF offline mode |
| `TRANSFORMERS_OFFLINE` | `true` | Transformers offline |

### Override Example
```bash
export TIKTOKEN_CACHE_DIR=/data/tiktoken
export HF_HOME=/data/huggingface
./scripts/run_proxy.sh start
```

## Files Updated

| Script | Purpose | Change |
|--------|---------|--------|
| `run_proxy.sh` | Linux proxy | Added offline vars |
| `run_proxy.bat` | Windows proxy | Added offline vars |
| `run_proxy_macos.sh` | macOS proxy | Added offline vars |
| `download_models.sh` | Model download | Enhanced with offline support |
| `setup_concurrency.sh` | Linux setup | Creates offline dirs |
| `setup_concurrency.bat` | Windows setup | Creates offline dirs |
| `deploy-nginx.sh` | Nginx (Linux) | Added offline vars |
| `deploy-nginx.bat` | Nginx (Windows) | Added offline vars |

## Directory Structure

```
models/
├── tiktoken/              ← Tiktoken encodings
├── huggingface/
│   ├── transformers/      ← Model weights
│   └── datasets/          ← Dataset cache
└── [LLM Guard models]     ← Optional
```

## Offline Mode Verification

```bash
# Check environment variables
env | grep -E 'TIKTOKEN|HF_'

# Check directories exist
ls -la ./models/

# Check cache contents
ls -la ./models/tiktoken/
ls -la ./models/huggingface/
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Proxy won't start | Run `./scripts/download_models.sh` |
| Models not found | Check `./models/` exists with files |
| Permission denied | Run `chmod +x ./scripts/*.sh` |
| Wrong Python | Check virtual env: `which python` |

## CLI Commands

```bash
# Tiktoken info
python -m ollama_guardrails tiktoken-info

# Download tiktoken encodings
python -m ollama_guardrails tiktoken-download -e cl100k_base

# HF info
python -m ollama_guardrails hf-info

# Download HF models
python -m ollama_guardrails hf-download -m bert-base-uncased
```

## Parallel Instances (Nginx)

```bash
# Start 3 instances on ports 8080, 8081, 8082
./scripts/deploy-nginx.sh start

# All use shared offline cache
# Better load distribution
# Automatic failover

# Check all running
./scripts/deploy-nginx.sh status
```

## Key Benefits

✅ No Azure downloads  
✅ No internet required (after setup)  
✅ Faster startup  
✅ Better privacy  
✅ Air-gapped environments  
✅ Parallel instances supported  

## Quick Start (One-Liner)

```bash
# Linux/macOS
./scripts/setup_concurrency.sh && ./scripts/download_models.sh && ./scripts/run_proxy.sh start

# Windows
setup_concurrency.bat && download_models.bat && run_proxy.bat
```

## Documentation

- Full guide: `SCRIPTS_UPDATE.md`
- Summary: `SCRIPTS_UPDATE_SUMMARY.md`
- This quick ref: `SCRIPTS_QUICK_REFERENCE.md`

---

**All 8 scripts updated with offline mode support**  
**Status: ✅ Production Ready**
