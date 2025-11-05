# Force Transformers to Use CPU - Environment Variables Setup

## Overview

This guide explains how to force the Hugging Face `transformers` library (used by `llm-guard`) to use CPU for all inference operations through environment variables. This is useful for CPU-only systems, testing, or when GPU acceleration is not needed.

## Environment Variables for CPU-Only Mode

### Primary Variable (Existing)

```bash
export LLM_GUARD_DEVICE=cpu
```

**Effect:** Forces llm-guard to use CPU device  
**Default:** auto-detected (CPU, or MPS on Apple Silicon)  
**Supported Values:** `cpu`, `mps`

### Additional Transformers Environment Variables (Recommended)

```bash
# Disable GPU acceleration in transformers
export CUDA_VISIBLE_DEVICES=""

# Disable CUDA entirely
export CUDA_LAUNCH_BLOCKING=1

# Disable Flash Attention
export DISABLE_FLASH_ATTENTION=1

# Force CPU execution in torch
export TORCH_DEVICE=cpu
```

### Hugging Face Offline Mode (Optional but Recommended)

```bash
export HF_HOME=./models/huggingface
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export HF_DATASETS_OFFLINE=true
export HF_HUB_OFFLINE=true
export TRANSFORMERS_CACHE=./models/huggingface/transformers
export HF_DATASETS_CACHE=./models/huggingface/datasets
```

## Complete CPU-Only Configuration

### Option 1: Minimal Setup (Easiest)

```bash
#!/bin/bash
export LLM_GUARD_DEVICE=cpu
export CUDA_VISIBLE_DEVICES=""
```

### Option 2: Comprehensive Setup (Recommended)

```bash
#!/bin/bash
# Force CPU usage
export LLM_GUARD_DEVICE=cpu
export CUDA_VISIBLE_DEVICES=""
export CUDA_LAUNCH_BLOCKING=1
export DISABLE_FLASH_ATTENTION=1

# Ensure no GPU fallback
export TORCH_DEVICE=cpu
```

### Option 3: With Offline Mode (Production)

```bash
#!/bin/bash
# Force CPU usage
export LLM_GUARD_DEVICE=cpu
export CUDA_VISIBLE_DEVICES=""
export CUDA_LAUNCH_BLOCKING=1
export DISABLE_FLASH_ATTENTION=1
export TORCH_DEVICE=cpu

# Offline mode
export HF_HOME=./models/huggingface
export HF_OFFLINE=true
export TRANSFORMERS_OFFLINE=true
export TRANSFORMERS_CACHE=./models/huggingface/transformers
export HF_DATASETS_CACHE=./models/huggingface/datasets

# Tiktoken offline
export TIKTOKEN_CACHE_DIR=./models/tiktoken
export TIKTOKEN_OFFLINE_MODE=true

# Local models
export LLM_GUARD_USE_LOCAL_MODELS=true
export LLM_GUARD_MODELS_PATH=./models
```

## Implementation in Code

### Method 1: Set Environment Variables in Python Script

```python
import os

# Set environment variables BEFORE any imports
os.environ['LLM_GUARD_DEVICE'] = 'cpu'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['DISABLE_FLASH_ATTENTION'] = '1'

# Now import guardrails
from ollama_guardrails.guards.guard_manager import LLMGuardManager

# Initialize guard manager
guard_manager = LLMGuardManager()
```

### Method 2: In guardrails CLI Setup

```python
# src/ollama_guardrails/__init__.py or cli.py

import os
import logging

logger = logging.getLogger(__name__)

def setup_cpu_mode():
    """Force transformers and llm-guard to use CPU."""
    # Set LLM Guard to CPU
    os.environ.setdefault('LLM_GUARD_DEVICE', 'cpu')
    
    # Disable CUDA
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
    
    # Disable Flash Attention
    os.environ['DISABLE_FLASH_ATTENTION'] = '1'
    
    logger.info('CPU-only mode enabled for transformers and llm-guard')

# Call this at module initialization
setup_cpu_mode()
```

### Method 3: In Proxy Application

```python
# src/ollama_guardrails/app.py

import os

# Set CPU mode BEFORE importing anything else
os.environ.setdefault('LLM_GUARD_DEVICE', 'cpu')
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['DISABLE_FLASH_ATTENTION'] = '1'

from fastapi import FastAPI
from ollama_guardrails.guards.guard_manager import LLMGuardManager

app = FastAPI()

# Initialize with CPU mode
guard_manager = LLMGuardManager()
```

## Updates Needed in Scripts

### run_proxy.sh (Linux/Unix)

```bash
#!/bin/bash
# Add to export_variables() function:

# Force Transformers to CPU
export LLM_GUARD_DEVICE=cpu
export CUDA_VISIBLE_DEVICES=""
export CUDA_LAUNCH_BLOCKING=1
export DISABLE_FLASH_ATTENTION=1
export TORCH_DEVICE=cpu
```

### run_proxy.bat (Windows)

```batch
@echo off
REM Force Transformers to CPU
set LLM_GUARD_DEVICE=cpu
set CUDA_VISIBLE_DEVICES=
set CUDA_LAUNCH_BLOCKING=1
set DISABLE_FLASH_ATTENTION=1
set TORCH_DEVICE=cpu
```

### run_proxy_macos.sh (macOS)

```bash
#!/bin/bash
# Add to setup_environment() function:

# Force Transformers to CPU (Apple Silicon users may want MPS instead)
export LLM_GUARD_DEVICE="${LLM_GUARD_DEVICE:-cpu}"  # Allow override to 'mps'
export CUDA_VISIBLE_DEVICES=""
export CUDA_LAUNCH_BLOCKING=1
export DISABLE_FLASH_ATTENTION=1
export TORCH_DEVICE=cpu
```

## Docker Configuration

### Dockerfile

```dockerfile
# Add to environment variables section
ENV LLM_GUARD_DEVICE=cpu \
    CUDA_VISIBLE_DEVICES="" \
    CUDA_LAUNCH_BLOCKING=1 \
    DISABLE_FLASH_ATTENTION=1 \
    TORCH_DEVICE=cpu \
    # ... other variables
```

### docker-compose.yml

```yaml
services:
  ollama-guard-proxy:
    environment:
      # Force CPU usage
      - LLM_GUARD_DEVICE=cpu
      - CUDA_VISIBLE_DEVICES=
      - CUDA_LAUNCH_BLOCKING=1
      - DISABLE_FLASH_ATTENTION=1
      - TORCH_DEVICE=cpu
      # ... other variables
```

## Verification

### Check Device Configuration

```bash
# View effective device
python -c "
import os
from ollama_guardrails.guards.guard_manager import LLMGuardManager
manager = LLMGuardManager()
print(f'Device: {manager.device}')
"
```

### Verify Environment Variables

```bash
# Check if CPU mode is set
echo "LLM_GUARD_DEVICE: $LLM_GUARD_DEVICE"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "CUDA_LAUNCH_BLOCKING: $CUDA_LAUNCH_BLOCKING"
echo "DISABLE_FLASH_ATTENTION: $DISABLE_FLASH_ATTENTION"
echo "TORCH_DEVICE: $TORCH_DEVICE"
```

### Test CPU-Only Operation

```bash
# Start proxy with CPU mode
export LLM_GUARD_DEVICE=cpu
export CUDA_VISIBLE_DEVICES=""
./scripts/run_proxy.sh start

# Test endpoint
curl http://localhost:9999/health

# Check logs for CPU device message
tail -f logs/proxy.log | grep -i "cpu\|device\|cuda"
```

## Environment Variable Details

| Variable | Purpose | Default | Value | Notes |
|----------|---------|---------|-------|-------|
| `LLM_GUARD_DEVICE` | LLM Guard device | auto | `cpu`, `mps` | Explicit device selection |
| `CUDA_VISIBLE_DEVICES` | Visible CUDA GPUs | (system) | `` (empty) | Empty disables GPU access |
| `CUDA_LAUNCH_BLOCKING` | Blocking CUDA calls | 0 | `1` | Synchronous execution |
| `DISABLE_FLASH_ATTENTION` | Flash Attention | 0 | `1` | Disable optimized attention |
| `TORCH_DEVICE` | PyTorch device | - | `cpu` | Force torch to CPU |

## Troubleshooting

### Issue: Still using GPU despite environment variables

**Solution:**
1. Verify variables are set BEFORE imports:
   ```bash
   python -c "import os; os.environ['LLM_GUARD_DEVICE']='cpu'; from ollama_guardrails..."
   ```

2. Check for hardcoded device settings in code:
   ```bash
   grep -r "cuda\|gpu\|mps" src/ --ignore-case
   ```

3. Ensure variables are exported, not just set:
   ```bash
   export LLM_GUARD_DEVICE=cpu
   ```

### Issue: CPU performance is slow

**Causes & Solutions:**
- Normal for large models (Deberta-v3-base is 200MB+)
- Use `LLM_GUARD_USE_LOCAL_MODELS=true` for faster repeated runs
- Consider smaller quantized models if available
- Run scanners individually rather than all at once

### Issue: Environment variables not persisting in Docker

**Solution:** Use `-e` flag or environment section in docker-compose:
```bash
docker run -e LLM_GUARD_DEVICE=cpu -e CUDA_VISIBLE_DEVICES="" ...
```

## Performance Considerations

### CPU-Only Performance
- **Startup Time:** 30-60 seconds (model loading)
- **Per-Request Time:** 50-200ms per scan (depends on model size and CPU cores)
- **Memory Usage:** 500MB-2GB

### Optimization Tips
1. **Enable Caching:** `export CACHE_ENABLED=true`
2. **Use Local Models:** `export LLM_GUARD_USE_LOCAL_MODELS=true`
3. **Multi-threading:** Let CPU use all available cores (system default)
4. **Async Processing:** Use async endpoints for better throughput

## Best Practices

✅ **DO:**
- Set environment variables BEFORE any imports
- Use `export` in shell scripts (not just `set`)
- Test with `--dry-run` before production
- Monitor CPU/memory usage with `top` or `htop`

❌ **DON'T:**
- Set variables after imports
- Mix CPU and GPU configuration
- Assume default device on all systems
- Ignore memory constraints with large models

## Reference Implementation

Create a file `src/ollama_guardrails/utils/device_config.py`:

```python
"""Device configuration utilities for forcing CPU usage."""

import os
import logging

logger = logging.getLogger(__name__)

def force_cpu_mode():
    """
    Force transformers and llm-guard to use CPU exclusively.
    
    Call this BEFORE importing any ML libraries.
    """
    # LLM Guard device
    os.environ.setdefault('LLM_GUARD_DEVICE', 'cpu')
    
    # Disable CUDA
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
    
    # Disable Flash Attention
    os.environ['DISABLE_FLASH_ATTENTION'] = '1'
    
    # PyTorch device
    if 'TORCH_DEVICE' not in os.environ:
        os.environ['TORCH_DEVICE'] = 'cpu'
    
    logger.info(
        'CPU-only mode enabled:\n'
        f'  LLM_GUARD_DEVICE: {os.environ.get("LLM_GUARD_DEVICE")}\n'
        f'  CUDA_VISIBLE_DEVICES: "{os.environ.get("CUDA_VISIBLE_DEVICES")}"\n'
        f'  CUDA_LAUNCH_BLOCKING: {os.environ.get("CUDA_LAUNCH_BLOCKING")}\n'
        f'  DISABLE_FLASH_ATTENTION: {os.environ.get("DISABLE_FLASH_ATTENTION")}\n'
        f'  TORCH_DEVICE: {os.environ.get("TORCH_DEVICE")}'
    )

def force_gpu_mode(device: str = 'mps'):
    """
    Force transformers and llm-guard to use GPU (Apple Silicon only).
    
    Args:
        device: GPU device ('mps' for Apple Silicon)
    """
    os.environ['LLM_GUARD_DEVICE'] = device
    # Remove CUDA restrictions
    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        del os.environ['CUDA_VISIBLE_DEVICES']
    
    logger.info(f'GPU mode enabled: {device}')

def get_device_config() -> dict:
    """Get current device configuration."""
    return {
        'llm_guard_device': os.environ.get('LLM_GUARD_DEVICE', 'auto'),
        'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES', '(system default)'),
        'cuda_launch_blocking': os.environ.get('CUDA_LAUNCH_BLOCKING', '0'),
        'disable_flash_attention': os.environ.get('DISABLE_FLASH_ATTENTION', '0'),
        'torch_device': os.environ.get('TORCH_DEVICE', 'auto'),
    }
```

Then use in `src/ollama_guardrails/__init__.py`:

```python
from .utils.device_config import force_cpu_mode

# Force CPU mode at module initialization
force_cpu_mode()
```

## Conclusion

By setting these environment variables, you ensure that:
1. ✅ All transformers models run on CPU
2. ✅ No CUDA operations are attempted
3. ✅ Flash Attention optimizations are disabled
4. ✅ PyTorch uses CPU device exclusively
5. ✅ llm-guard respects the device setting

This provides predictable, reproducible behavior across all systems and environments.
