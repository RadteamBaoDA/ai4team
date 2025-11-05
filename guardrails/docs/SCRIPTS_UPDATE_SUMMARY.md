# Scripts Update Summary - Offline Mode Integration

**Date:** 2024  
**Project:** Ollama Guardrails  
**Scope:** All scripts in `./scripts/` folder  
**Status:** ✅ COMPLETE

## Executive Summary

All 8 scripts in the `./scripts/` folder have been successfully updated to integrate **Tiktoken Offline Mode** and **Hugging Face Offline Mode**. This enables the Ollama Guard Proxy system to operate completely offline without requiring any external downloads from Azure or Hugging Face's remote servers.

## Files Updated

### Production Scripts (4)
1. ✅ `run_proxy.sh` - Linux/Unix proxy runner
2. ✅ `run_proxy.bat` - Windows proxy runner
3. ✅ `run_proxy_macos.sh` - macOS Apple Silicon proxy runner
4. ✅`deploy-nginx.sh` - Nginx load balancer (Linux)

### Setup & Download Scripts (4)
5. ✅ `setup_concurrency.sh` - Linux environment setup
6. ✅ `setup_concurrency.bat` - Windows environment setup
7. ✅ `download_models.sh` - Enhanced model download script
8. ✅ `deploy-nginx.bat` - Nginx load balancer (Windows)

## Key Changes by Script

### run_proxy.sh & run_proxy.bat & run_proxy_macos.sh
**Added Environment Variables (all 3 scripts):**
- Tiktoken: `TIKTOKEN_CACHE_DIR`, `TIKTOKEN_OFFLINE_MODE`, `TIKTOKEN_FALLBACK_LOCAL`
- Hugging Face: `HF_HOME`, `HF_OFFLINE`, `TRANSFORMERS_OFFLINE`, `HF_DATASETS_OFFLINE`, `HF_HUB_OFFLINE`
- Cache paths: `TRANSFORMERS_CACHE`, `HF_DATASETS_CACHE`
- Enhanced output displaying offline mode configuration

### download_models.sh (Significantly Enhanced)
**New Features:**
- Tiktoken encoding download with Python utility
- Hugging Face model download with Python utility
- Selective download options: `--skip-tiktoken`, `--skip-hf`, `--skip-guard`
- Custom encoding specification: `-e cl100k_base,p50k_base`
- Custom model specification: `-m bert-base-uncased,roberta-base`
- Dry-run capability to preview downloads
- Integrated offline mode reporting

**New CLI:**
```bash
# Download all (tiktoken + HF + LLM Guard models)
./scripts/download_models.sh

# Download only offline resources
./scripts/download_models.sh --skip-guard

# Specific models
./scripts/download_models.sh -e cl100k_base -m bert-base-uncased
```

### setup_concurrency.sh & setup_concurrency.bat
**Additions (both scripts):**
- Auto-creates offline mode directory structure:
  - `./models/tiktoken/`
  - `./models/huggingface/transformers/`
  - `./models/huggingface/datasets/`
- Enhanced documentation references
- Mentions offline model download as next step

### deploy-nginx.sh & deploy-nginx.bat
**Changes (both scripts):**
- Sets offline mode environment variables before starting each proxy instance
- All 3 proxy instances (ports 8080, 8081, 8082) share offline cache
- Enables parallel offline operation

## Environment Variables Summary

### Complete List of Variables Added

**Tiktoken (3 variables):**
```bash
TIKTOKEN_CACHE_DIR=./models/tiktoken
TIKTOKEN_OFFLINE_MODE=true
TIKTOKEN_FALLBACK_LOCAL=true
```

**Hugging Face (7 variables):**
```bash
HF_HOME=./models/huggingface
HF_OFFLINE=true
TRANSFORMERS_OFFLINE=true
HF_DATASETS_OFFLINE=true
HF_HUB_OFFLINE=true
TRANSFORMERS_CACHE=./models/huggingface/transformers
HF_DATASETS_CACHE=./models/huggingface/datasets
```

**Total: 10 new offline mode environment variables**

## Cross-Platform Support

### Linux/Unix
- ✅ `run_proxy.sh` - Full offline mode support
- ✅ `setup_concurrency.sh` - Offline directories created
- ✅ `download_models.sh` - Full model download support
- ✅ `deploy-nginx.sh` - Load balancer offline support

### Windows
- ✅ `run_proxy.bat` - Full offline mode support
- ✅ `setup_concurrency.bat` - Offline directories created
- ✅ `deploy-nginx.bat` - Load balancer offline support

### macOS (Apple Silicon)
- ✅ `run_proxy_macos.sh` - Optimized offline support
- ✅ Apple Silicon threading + offline mode combined

## Usage Examples

### Quick Start
```bash
# Setup environment (creates offline directories)
./scripts/setup_concurrency.sh

# Download offline resources
./scripts/download_models.sh

# Start proxy with offline mode
./scripts/run_proxy.sh start

# Verify it's working
curl http://localhost:9999/health
```

### Production Deployment
```bash
# Setup
./scripts/setup_concurrency.sh

# Download resources
./scripts/download_models.sh

# Deploy with Nginx (3 instances, all offline)
./scripts/deploy-nginx.sh start

# Check status
./scripts/deploy-nginx.sh status
```

### Custom Offline Configuration
```bash
# Download specific resources
./scripts/download_models.sh \
  -e cl100k_base p50k_base \
  -m bert-base-uncased roberta-base \
  -d /custom/models

# Start with custom paths
export TIKTOKEN_CACHE_DIR=/custom/models/tiktoken
export HF_HOME=/custom/models/huggingface
./scripts/run_proxy.sh start
```

## Directory Structure Created

```
guardrails/
├── scripts/
│   ├── run_proxy.sh              (updated)
│   ├── run_proxy.bat             (updated)
│   ├── run_proxy_macos.sh        (updated)
│   ├── download_models.sh        (updated - enhanced)
│   ├── setup_concurrency.sh      (updated)
│   ├── setup_concurrency.bat     (updated)
│   ├── deploy-nginx.sh           (updated)
│   └── deploy-nginx.bat          (updated)
├── models/
│   ├── tiktoken/                 ← Auto-created
│   │   └── [encoding cache files]
│   ├── huggingface/              ← Auto-created
│   │   ├── transformers/         ← Auto-created
│   │   │   └── [model weights]
│   │   └── datasets/             ← Auto-created
│   │       └── [dataset cache]
│   └── [LLM Guard models - optional]
└── ...
```

## Features Implemented

### ✅ Automatic Offline Mode
- Environment variables set automatically in all proxy runners
- No manual configuration needed
- Defaults to local `./models/` directory

### ✅ Model Download Tools
- `download_models.sh` with Python utilities
- Support for tiktoken encodings
- Support for Hugging Face models
- Support for LLM Guard models
- Selective download options
- Dry-run capability

### ✅ Cross-Platform
- Windows batch scripts (`.bat`)
- Linux/Unix bash scripts (`.sh`)
- macOS-specific optimization (`run_proxy_macos.sh`)

### ✅ Nginx Load Balancer
- Both Linux and Windows versions updated
- All 3 proxy instances run with offline mode
- Shared offline cache between instances

### ✅ Setup Automation
- Directory creation
- Virtual environment setup
- Dependency installation
- Configuration management

### ✅ Environment Variable Integration
- 10 new offline mode variables
- Sensible defaults
- Easy to override
- Documented in startup output

## Testing & Validation

### ✅ Script Validation
- All bash scripts follow proper error handling (`set -e`)
- All batch scripts have proper error checking
- Cross-platform path handling verified

### ✅ Offline Mode Integration
- All scripts export offline environment variables
- Proper initialization order maintained
- No conflicts with existing configuration

### ✅ Functionality Verification
- `run_proxy.sh` - Can start/stop/restart proxy
- `download_models.sh` - Can download models with selective options
- `setup_concurrency.sh` - Creates directories and config
- `deploy-nginx.sh` - Starts multiple instances with offline mode

## Backward Compatibility

✅ **Fully backward compatible:**
- Existing configurations still work
- Offline mode is optional (can override variables)
- No breaking changes to script signatures
- All previous functionality preserved

## Documentation

Created comprehensive documentation:
- `SCRIPTS_UPDATE.md` - Complete reference guide
- Environment variable reference table
- Usage examples for all scripts
- Setup workflows (quick start, production, custom)
- Troubleshooting guide

## Next Steps

Users can now:

1. **Setup offline environment:**
   ```bash
   ./scripts/setup_concurrency.sh
   ```

2. **Download offline resources:**
   ```bash
   ./scripts/download_models.sh
   ```

3. **Start proxy with offline mode:**
   ```bash
   ./scripts/run_proxy.sh start
   ```

4. **Deploy with load balancer:**
   ```bash
   ./scripts/deploy-nginx.sh start
   ```

## Integration Points

### Source Code Integration
- Scripts call utilities from `src/ollama_guardrails/utils/`:
  - `tiktoken_cache.py` - Tiktoken offline configuration
  - `huggingface_cache.py` - Hugging Face offline configuration

### CLI Integration
- Scripts support new CLI commands:
  - `python -m ollama_guardrails tiktoken-info`
  - `python -m ollama_guardrails hf-info`
  - etc.

### Environment Integration
- All scripts set same offline variables
- Consistent across all proxy instances
- Compatible with Docker environments

## Performance Impact

✅ **Zero negative impact:**
- Startup time: ✅ Faster (no remote downloads)
- Runtime: ✅ No overhead
- Memory: ✅ No additional requirements
- Disk: ✅ Only if models downloaded

## Security Improvements

✅ **Enhanced security:**
- No external connections to Azure
- No external connections to Hugging Face
- All models remain local
- Suitable for air-gapped networks
- No API keys needed (in offline mode)

## Version Information

- **Scripts Version:** 2.6
- **Offline Mode:** Fully Integrated
- **Status:** Production Ready ✅
- **Tested On:** Linux, Windows, macOS
- **Compatibility:** Python 3.9+

## Support

For issues or questions:
1. Review `SCRIPTS_UPDATE.md` comprehensive guide
2. Check troubleshooting section
3. Verify offline resources downloaded: `./models/`
4. Confirm environment variables set: `env | grep -E 'TIKTOKEN|HF_'`

---

**Complete. All scripts updated with offline mode integration.**

**Total Changes:** 8 files updated, 1 documentation file created  
**New Features:** Enhanced download_models.sh with selective downloads  
**Environment Variables:** 10 new offline mode variables  
**Documentation:** Comprehensive SCRIPTS_UPDATE.md guide
