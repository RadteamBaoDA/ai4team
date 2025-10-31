# CPU and Apple Silicon (MPS) Optimization

## Overview

The guardrails service has been optimized to support:
- **CPU**: Universal support for all platforms (Linux, macOS, Windows)
- **MPS**: Apple Silicon GPU acceleration (M1/M2/M3/M4 chips)

NVIDIA CUDA support has been removed for simplicity and compatibility.

## Device Detection

The system automatically detects the best available device:

1. **Apple Silicon (arm64 macOS)**:
   - Checks if MPS (Metal Performance Shaders) is available
   - Uses MPS GPU acceleration if available
   - Falls back to CPU if MPS is not available

2. **All other platforms**:
   - Uses CPU by default

## Manual Device Selection

You can override automatic detection using the environment variable:

```bash
# Force CPU (useful for testing or compatibility)
export LLM_GUARD_DEVICE="cpu"
./run_proxy.sh start

# Force MPS (Apple Silicon only)
export LLM_GUARD_DEVICE="mps"
./run_proxy.sh start
```

## Installation

### Standard Installation (CPU-only)

```bash
pip install -r requirements.txt
```

This installs PyTorch with CPU support by default.

### Apple Silicon with MPS

On macOS with Apple Silicon, PyTorch will automatically detect and use MPS:

```bash
pip install -r requirements.txt
```

The system will automatically use MPS if:
- Running on Apple Silicon (M1/M2/M3/M4)
- PyTorch is installed with MPS support
- `torch.backends.mps.is_available()` returns True

## Performance Comparison

### CPU Mode
- **Pros**: Universal compatibility, stable, well-tested
- **Cons**: Slower inference times for large models
- **Best for**: Production servers, compatibility-focused deployments

### MPS Mode (Apple Silicon)
- **Pros**: 2-3x faster inference on Apple Silicon, lower CPU usage
- **Cons**: Only available on Apple Silicon Macs
- **Best for**: Development on MacBooks, local testing, Apple-based deployments

## Verification

Check which device is being used:

```bash
# Start the service and check logs
./run_proxy.sh run

# Look for log messages:
# - "Using MPS GPU acceleration" = MPS enabled
# - "Using CPU for ML inference" = CPU mode
```

Or query the health endpoint:

```bash
curl http://localhost:9999/health | jq .device
```

## Configuration Details

### Device-Specific Settings

The system configures models based on the detected device:

```python
# CPU configuration
device_kwargs = {'device': 'cpu'}

# MPS configuration (Apple Silicon)
device_kwargs = {'device': 'mps'}
```

### Model Loading

Local models are configured with device-specific settings:

```python
# Example: Toxicity model configuration
TOXICITY_MODEL.kwargs["device"] = "cpu"  # or "mps"
TOXICITY_MODEL.path = "./models/unbiased-toxic-roberta"
TOXICITY_MODEL.kwargs["local_files_only"] = True
```

## Troubleshooting

### MPS Not Available on Apple Silicon

If you're on Apple Silicon but MPS is not detected:

1. **Update PyTorch**:
   ```bash
   pip install --upgrade torch
   ```

2. **Check PyTorch version**:
   ```bash
   python -c "import torch; print(torch.__version__)"
   ```
   Ensure version is 2.4.0 or higher.

3. **Verify MPS support**:
   ```bash
   python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
   ```

### Force CPU Mode

If you encounter issues with MPS:

```bash
export LLM_GUARD_DEVICE="cpu"
./run_proxy.sh restart
```

## Why No CUDA Support?

NVIDIA CUDA support was removed for:

1. **Simplicity**: Reduces dependency complexity
2. **Compatibility**: Fewer version conflicts
3. **Focus**: Optimizes for most common deployment scenarios (CPU servers, Apple Silicon development)
4. **Maintenance**: Easier to maintain and test

If you need GPU acceleration:
- Use Apple Silicon MPS for development/testing
- Deploy to CPU-based production servers (sufficient for most workloads)
- Consider dedicated GPU inference services if needed

## Environment Variables Summary

| Variable | Values | Description |
|----------|--------|-------------|
| `LLM_GUARD_DEVICE` | `cpu`, `mps` | Override device selection |
| `LLM_GUARD_USE_LOCAL_MODELS` | `true`, `false` | Enable local model loading |
| `LLM_GUARD_MODELS_PATH` | Path | Directory containing local models |

## Best Practices

1. **Development**: Use Apple Silicon MPS for faster iteration
2. **Production**: Use CPU for stability and compatibility
3. **Testing**: Test on both CPU and MPS if deploying to mixed environments
4. **Monitoring**: Check device info in health endpoint for verification

## Related Documentation

- [Local Models Setup](LOCAL_MODELS_SETUP.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Quick Start](QUICK_START.md)
