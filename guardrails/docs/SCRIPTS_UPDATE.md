# Guardrails Scripts Update - Offline Mode Integration

## Overview

All scripts in the `./scripts` folder have been updated to integrate **Tiktoken Offline Mode** and **Hugging Face Offline Mode** configuration. This enables the Ollama Guard Proxy to operate completely offline without requiring downloads from Azure or Hugging Face's remote servers.

## Updated Scripts

### 1. **run_proxy.sh** (Linux/Unix)
**Purpose:** Main proxy runner for Linux and Unix systems

**Offline Mode Changes:**
- Added Tiktoken environment variables:
  - `TIKTOKEN_CACHE_DIR` (default: `./models/tiktoken`)
  - `TIKTOKEN_OFFLINE_MODE` (default: `true`)
  - `TIKTOKEN_FALLBACK_LOCAL` (default: `true`)

- Added Hugging Face environment variables:
  - `HF_HOME` (default: `./models/huggingface`)
  - `HF_OFFLINE` (default: `true`)
  - `TRANSFORMERS_OFFLINE` (default: `true`)
  - `HF_DATASETS_OFFLINE` (default: `true`)
  - `HF_HUB_OFFLINE` (default: `true`)
  - `TRANSFORMERS_CACHE` (default: `./models/huggingface/transformers`)
  - `HF_DATASETS_CACHE` (default: `./models/huggingface/datasets`)

**Usage:**
```bash
# Start proxy with offline mode enabled
./scripts/run_proxy.sh start

# Or set custom cache directories
export TIKTOKEN_CACHE_DIR=/data/tiktoken
export HF_HOME=/data/huggingface
./scripts/run_proxy.sh start
```

### 2. **run_proxy.bat** (Windows)
**Purpose:** Main proxy runner for Windows systems

**Offline Mode Changes:**
- Added same Tiktoken and Hugging Face environment variables as Linux
- Displays offline mode configuration in startup output
- Uses Windows path separators (`\` instead of `/`)

**Usage:**
```batch
REM Start proxy with offline mode enabled
run_proxy.bat

REM Or set custom cache directories
set TIKTOKEN_CACHE_DIR=D:\Models\tiktoken
set HF_HOME=D:\Models\huggingface
run_proxy.bat
```

### 3. **run_proxy_macos.sh** (macOS/Apple Silicon)
**Purpose:** Optimized proxy runner for macOS with Apple Silicon (M1/M2/M3) support

**Offline Mode Changes:**
- Added all Tiktoken and Hugging Face offline environment variables
- Integrated into Apple Silicon environment setup
- Displays offline mode configuration in startup output
- Optimized threading and memory settings alongside offline mode

**Usage:**
```bash
# Start proxy on macOS with Apple Silicon optimizations
./scripts/run_proxy_macos.sh start

# Check status with offline mode info
./scripts/run_proxy_macos.sh status
```

### 4. **download_models.sh** (Enhanced)
**Purpose:** Download LLM Guard models and offline mode resources

**New Features:**
- **Tiktoken encoding download:** Automatically downloads tiktoken encodings to local cache
- **Hugging Face model download:** Download specific HF models for offline use
- **LLM Guard model download:** Original functionality preserved

**New Command-Line Options:**
```
-e, --encodings ENCS    Tiktoken encodings (comma-separated)
                        Default: cl100k_base,p50k_base,p50k_edit,r50k_base
-m, --models MODELS     Hugging Face models (comma-separated)
--skip-tiktoken         Skip tiktoken encoding download
--skip-hf               Skip HF model download
--skip-guard            Skip LLM Guard model download
```

**Usage Examples:**
```bash
# Download all resources (tiktoken + HF + LLM Guard models)
./scripts/download_models.sh

# Download only offline mode resources (no LLM Guard models)
./scripts/download_models.sh --skip-guard

# Download specific encodings and models
./scripts/download_models.sh -e cl100k_base,p50k_base -m bert-base-uncased roberta-base

# Dry run to see what would be downloaded
./scripts/download_models.sh --dry-run

# Download to custom directory
./scripts/download_models.sh -d /data/models
```

**Output Directory Structure:**
```
./models/
├── tiktoken/
│   ├── encodings.json
│   └── vocab files...
├── huggingface/
│   ├── transformers/
│   │   ├── bert-base-uncased/
│   │   └── ...
│   └── datasets/
│       └── ...
└── [LLM Guard models if --skip-guard not used]
```

### 5. **setup_concurrency.sh** (Updated)
**Purpose:** Setup script for Linux - configures environment and dependencies

**Offline Mode Changes:**
- Creates offline mode directory structure automatically:
  - `./models/tiktoken/`
  - `./models/huggingface/transformers/`
  - `./models/huggingface/datasets/`
- Enhanced setup instructions mentioning offline mode
- Added references to offline mode documentation

**Usage:**
```bash
./scripts/setup_concurrency.sh
```

**What It Does:**
1. Creates Python virtual environment
2. Installs dependencies
3. Creates offline mode cache directories
4. Configures concurrency settings in `config.yaml`
5. Displays next steps including offline model download

### 6. **setup_concurrency.bat** (Updated)
**Purpose:** Setup script for Windows

**Offline Mode Changes:**
- Creates offline mode directory structure (Windows paths):
  - `.\models\tiktoken\`
  - `.\models\huggingface\transformers\`
  - `.\models\huggingface\datasets\`
- Enhanced setup instructions
- Added offline mode documentation references

**Usage:**
```batch
setup_concurrency.bat
```

### 7. **deploy-nginx.sh** (Updated)
**Purpose:** Deploy Nginx load balancer with multiple proxy instances

**Offline Mode Changes:**
- Exports offline mode environment variables before starting each proxy instance
- Each of the 3 proxy instances (ports 8080, 8081, 8082) gets offline mode enabled
- All instances share the same offline cache directories

**Environment Variables Set:**
```bash
TIKTOKEN_CACHE_DIR=./models/tiktoken
TIKTOKEN_OFFLINE_MODE=true
HF_HOME=./models/huggingface
HF_OFFLINE=true
TRANSFORMERS_OFFLINE=true
HF_DATASETS_OFFLINE=true
HF_HUB_OFFLINE=true
```

**Usage:**
```bash
# Start nginx with 3 proxy instances all in offline mode
./scripts/deploy-nginx.sh start

# Check status of all instances
./scripts/deploy-nginx.sh status

# Stop all instances
./scripts/deploy-nginx.sh stop
```

### 8. **deploy-nginx.bat** (Updated)
**Purpose:** Deploy Nginx load balancer on Windows

**Offline Mode Changes:**
- Sets offline mode environment variables for each proxy instance
- Each of the 3 proxy instances gets same offline configuration
- Windows-compatible path handling

**Usage:**
```batch
REM Start nginx with 3 proxy instances in offline mode
deploy-nginx.bat start

REM Check status
deploy-nginx.bat status

REM Stop all instances
deploy-nginx.bat stop
```

## Environment Variables Reference

### Tiktoken Offline Mode
| Variable | Default | Description |
|----------|---------|-------------|
| `TIKTOKEN_CACHE_DIR` | `./models/tiktoken` | Path to tiktoken cache directory |
| `TIKTOKEN_OFFLINE_MODE` | `true` | Enable/disable offline mode |
| `TIKTOKEN_FALLBACK_LOCAL` | `true` | Use local models as fallback |

### Hugging Face Offline Mode
| Variable | Default | Description |
|----------|---------|-------------|
| `HF_HOME` | `./models/huggingface` | Hugging Face home directory |
| `HF_OFFLINE` | `true` | Enable HF offline mode |
| `TRANSFORMERS_OFFLINE` | `true` | Enable transformers offline |
| `HF_DATASETS_OFFLINE` | `true` | Enable datasets offline |
| `HF_HUB_OFFLINE` | `true` | Enable hub offline |
| `TRANSFORMERS_CACHE` | `./models/huggingface/transformers` | Transformers cache path |
| `HF_DATASETS_CACHE` | `./models/huggingface/datasets` | Datasets cache path |

## Setup Workflow

### Quick Start (All-in-One)
```bash
# 1. Setup environment
./scripts/setup_concurrency.sh

# 2. Download offline resources
./scripts/download_models.sh

# 3. Start proxy
./scripts/run_proxy.sh start

# 4. Verify offline operation
curl http://localhost:9999/health
```

### Production Deployment (Nginx Load Balancer)
```bash
# 1. Setup
./scripts/setup_concurrency.sh

# 2. Download offline resources
./scripts/download_models.sh

# 3. Deploy with Nginx (3 instances)
./scripts/deploy-nginx.sh start

# 4. Check status
./scripts/deploy-nginx.sh status
```

### Custom Offline Models
```bash
# 1. Setup
./scripts/setup_concurrency.sh

# 2. Download specific offline models
./scripts/download_models.sh \
  -e cl100k_base p50k_base \
  -m bert-base-uncased roberta-base \
  -d ./models

# 3. Start proxy
./scripts/run_proxy.sh start
```

## Directory Structure After Setup

```
guardrails/
├── scripts/
│   ├── run_proxy.sh              (updated)
│   ├── run_proxy.bat             (updated)
│   ├── run_proxy_macos.sh        (updated)
│   ├── download_models.sh        (updated)
│   ├── setup_concurrency.sh      (updated)
│   ├── setup_concurrency.bat     (updated)
│   ├── deploy-nginx.sh           (updated)
│   └── deploy-nginx.bat          (updated)
├── models/                        (auto-created)
│   ├── tiktoken/                 (encodings cache)
│   ├── huggingface/
│   │   ├── transformers/         (model weights)
│   │   └── datasets/             (dataset cache)
│   └── [LLM Guard models]
├── config/
│   └── config.yaml               (concurrency settings)
└── src/
    └── ollama_guardrails/
        └── utils/
            ├── tiktoken_cache.py (offline mode utilities)
            └── huggingface_cache.py (HF offline utilities)
```

## Offline Mode Benefits

✅ **No Azure Downloads:** Tiktoken uses local cache instead of Azure  
✅ **No Internet Required:** After initial setup, works completely offline  
✅ **Faster Startup:** No remote downloads on each initialization  
✅ **Better Privacy:** All models stay local  
✅ **Cost Reduction:** No bandwidth usage for model downloads  
✅ **Air-Gapped Networks:** Perfect for isolated/secure environments  
✅ **Parallel Instances:** All proxy instances share same cache  

## Troubleshooting

### Proxy won't start
```bash
# Check if offline mode directories exist
ls -la ./models/

# Verify environment variables
echo $TIKTOKEN_CACHE_DIR
echo $HF_HOME

# Download offline resources
./scripts/download_models.sh
```

### Models not found
```bash
# Ensure models are downloaded
./scripts/download_models.sh -v

# Check cache contents
ls -la ./models/tiktoken/
ls -la ./models/huggingface/
```

### Permission errors on Linux/macOS
```bash
# Make scripts executable
chmod +x ./scripts/*.sh

# Check directory permissions
ls -la ./models/
```

## Integration with Source Code

The scripts now integrate with the offline mode utilities in `src/`:

- **`tiktoken_cache.py`** - Tiktoken offline configuration
- **`huggingface_cache.py`** - Hugging Face offline configuration

These utilities are automatically called when:
1. Importing `ollama_guardrails.cli`
2. Importing `ollama_guardrails.guards.guard_manager`
3. Running `setup_tiktoken_offline_mode()` or `setup_huggingface_offline_mode()`

## CLI Commands

The source code now includes CLI commands for offline mode management:

```bash
# Show tiktoken cache info
python -m ollama_guardrails tiktoken-info

# Download tiktoken encodings via CLI
python -m ollama_guardrails tiktoken-download -e cl100k_base p50k_base

# Show HF cache info
python -m ollama_guardrails hf-info

# Download HF models via CLI
python -m ollama_guardrails hf-download -m bert-base-uncased roberta-base
```

## Windows vs Linux Differences

### Path Separators
- **Linux:** Uses forward slashes (`/`) and `./models/`
- **Windows:** Uses backslashes (`\`) and `.\models\`

### Virtual Environment
- **Linux:** `source venv/bin/activate`
- **Windows:** `call venv\Scripts\activate.bat`

### Directory Creation
- **Linux:** `mkdir -p` (creates parent directories)
- **Windows:** `mkdir` with `if not exist` checks

## Documentation References

- **Offline Mode:** See `docs/TIKTOKEN_OFFLINE_MODE.md`
- **Hugging Face Setup:** See `docs/OFFLINE_MODE_UPDATE.md`
- **Concurrency:** See `docs/CONCURRENCY_GUIDE.md`
- **Quick Reference:** See `docs/QUICK_REFERENCE.md`

## Version History

### Current (v2.6)
- ✅ All scripts updated with offline mode support
- ✅ Tiktoken cache integration
- ✅ Hugging Face offline mode
- ✅ Cross-platform support (Windows, Linux, macOS)
- ✅ Enhanced download_models.sh with selective downloads
- ✅ Setup scripts create offline directories

### Previous Versions
- v2.5: Hugging Face offline mode added to source code
- v2.4: Tiktoken offline mode added to source code
- v2.3: Concurrency configuration implemented
- v2.2: Nginx load balancer support
- v2.1: Basic proxy functionality

## Support & Feedback

For issues or questions about offline mode in scripts:
1. Check `docs/` folder for relevant guides
2. Review script comments and help messages
3. Test with `--dry-run` flag first
4. Check environment variables are properly set

---

**Last Updated:** 2024  
**Maintainer:** AI4Team  
**Status:** Production Ready ✅
