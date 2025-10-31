# Script Update Required

The scripts in the `scripts/` directory need to be updated to work with the new package structure.

## Key Changes Required:

### 1. Module Path Updates
- Old: `src.ollama_guard_proxy:app`
- New: `ollama_guardrails.app:app`

### 2. Installation Commands  
- Old: `pip install -r requirements.txt`
- New: `pip install -e .` (development) or `pip install ollama-guardrails`

### 3. CLI Usage
The new package provides a proper CLI:
```bash
# Instead of running uvicorn directly
ollama-guardrails server

# With config
ollama-guardrails server --config config.yaml

# For development
python -m ollama_guardrails server
```

### 4. Updated Scripts Needed:
- `run_proxy.sh` ✅ (partially updated)
- `run_proxy.bat` (needs update)
- `run_proxy_macos.sh` (needs update)

### 5. Recommended Usage
For production deployment, use the new CLI commands instead of the legacy scripts:

```bash
# Production
ollama-guardrails server --config config/config.yaml

# Development with auto-reload
python -m ollama_guardrails server --config config/config.yaml
```