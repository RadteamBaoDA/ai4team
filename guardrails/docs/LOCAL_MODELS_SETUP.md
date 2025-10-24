# Local Models Setup for LLM Guard

This guide explains how to configure LLM Guard to use local models instead of downloading them from HuggingFace at runtime.

## Overview

By default, LLM Guard downloads models from HuggingFace when scanners are initialized. For production environments or air-gapped deployments, you can pre-download models and configure LLM Guard to use them locally.

## Environment Variables

### Enable Local Models
```bash
export LLM_GUARD_USE_LOCAL_MODELS=true
```

### Models Base Path
```bash
export LLM_GUARD_MODELS_PATH=/path/to/models
# Default: ./models
```

## Required Models

When using local models, you need to download the following models:

### Input Scanners
- **PromptInjection**: `protectai/deberta-v3-base-prompt-injection-v2`
- **Toxicity**: `unitary/unbiased-toxic-roberta`
- **Code**: `philomath-1209/programming-language-identification`
- **Anonymize**: `Isotonic/deberta-v3-base_finetuned_ai4privacy_v2`

### Output Scanners
- **Toxicity**: `unitary/unbiased-toxic-roberta`
- **Code**: `philomath-1209/programming-language-identification`

## Model Download Script

Create a script to download all required models:

```bash
#!/bin/bash
# download_models.sh

set -e

MODELS_DIR=${LLM_GUARD_MODELS_PATH:-./models}
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

echo "Installing git-lfs..."
git lfs install

echo "Downloading models to $MODELS_DIR"

# Input scanner models
echo "Downloading PromptInjection model..."
git clone https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2

echo "Downloading Toxicity model..."
git clone https://huggingface.co/unitary/unbiased-toxic-roberta

echo "Downloading Code detection model..."
git clone https://huggingface.co/philomath-1209/programming-language-identification

echo "Downloading Anonymize model..."
git clone https://huggingface.co/Isotonic/deberta-v3-base_finetuned_ai4privacy_v2

echo "All models downloaded successfully!"
echo "Model directory structure:"
ls -la "$MODELS_DIR"
```

Make it executable and run:
```bash
chmod +x download_models.sh
./download_models.sh
```

## Directory Structure

After downloading, your models directory should look like:

```
models/
├── deberta-v3-base-prompt-injection-v2/
│   ├── config.json
│   ├── pytorch_model.bin
│   ├── tokenizer.json
│   └── ...
├── unbiased-toxic-roberta/
│   ├── config.json
│   ├── pytorch_model.bin
│   └── ...
├── programming-language-identification/
│   ├── config.json
│   ├── pytorch_model.bin
│   └── ...
└── deberta-v3-base_finetuned_ai4privacy_v2/
    ├── config.json
    ├── pytorch_model.bin
    └── ...
```

## Configuration Examples

### Docker Environment
```dockerfile
# Dockerfile
FROM python:3.9

# Copy pre-downloaded models
COPY models/ /app/models/

# Set environment variables
ENV LLM_GUARD_USE_LOCAL_MODELS=true
ENV LLM_GUARD_MODELS_PATH=/app/models

WORKDIR /app
# ... rest of your dockerfile
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  guardrails:
    build: .
    environment:
      - LLM_GUARD_USE_LOCAL_MODELS=true
      - LLM_GUARD_MODELS_PATH=/app/models
    volumes:
      - ./models:/app/models:ro
    # ... rest of your service config
```

### Shell Script
```bash
#!/bin/bash
# run_with_local_models.sh

export LLM_GUARD_USE_LOCAL_MODELS=true
export LLM_GUARD_MODELS_PATH="$(pwd)/models"

python ollama_guard_proxy.py
```

## Verification

To verify local models are being used, check the logs for messages like:

```
INFO - Configured PromptInjection model path: ./models/deberta-v3-base-prompt-injection-v2
INFO - Configured input Toxicity model path: ./models/unbiased-toxic-roberta
INFO - Local model configuration completed
INFO - Input scanners initialized: 6 scanners ready (local_models: True)
INFO - Output scanners initialized: 5 scanners ready (local_models: True)
```

## Optimization Tips

### ONNX Models Only
If you only need ONNX models for faster inference, you can remove PyTorch model files to save space:

```bash
# Remove PyTorch models, keep only ONNX
find models/ -name "pytorch_model.bin" -delete
find models/ -name "model.safetensors" -delete
```

### Model Caching
Set HuggingFace cache directory to avoid re-downloading:

```bash
export TRANSFORMERS_CACHE=/path/to/cache
export HF_HOME=/path/to/cache
```

## Troubleshooting

### Model Not Found
```
FileNotFoundError: [Errno 2] No such file or directory: './models/deberta-v3-base-prompt-injection-v2'
```

**Solution**: Ensure the model directory exists and contains the required files.

### Permission Errors
```
PermissionError: [Errno 13] Permission denied
```

**Solution**: Check file permissions on the models directory:
```bash
chmod -R 755 models/
```

### Memory Issues
If you experience memory issues with large models:

1. Use ONNX models only
2. Reduce the number of active scanners
3. Increase system memory allocation

## Advanced Configuration

### Custom Model Paths
You can override individual model paths by setting specific environment variables:

```bash
export LLM_GUARD_PROMPT_INJECTION_MODEL_PATH=/custom/path/to/prompt-injection-model
export LLM_GUARD_TOXICITY_MODEL_PATH=/custom/path/to/toxicity-model
export LLM_GUARD_CODE_MODEL_PATH=/custom/path/to/code-model
export LLM_GUARD_ANONYMIZE_MODEL_PATH=/custom/path/to/anonymize-model
```

### Model Variants
You can use different model variants by updating the paths in the configuration:

```python
# Custom model configuration
PROMPT_INJECTION_MODEL.path = "/path/to/custom-prompt-injection-model"
TOXICITY_INPUT_MODEL.path = "/path/to/custom-toxicity-model"
```

## Production Deployment

For production deployments:

1. **Pre-build containers** with models included
2. **Use read-only volumes** for model storage
3. **Monitor model loading time** during startup
4. **Set up health checks** to ensure models are loaded correctly
5. **Consider model warm-up** strategies for faster first-request performance

## Security Considerations

1. **Verify model integrity** using checksums
2. **Scan models** for potential security issues
3. **Use trusted sources** for model downloads
4. **Implement access controls** for model storage
5. **Regular updates** for security patches

## Performance Impact

Local models provide several benefits:

- **Faster startup**: No network downloads
- **Offline operation**: Works without internet
- **Consistent performance**: No dependency on external services
- **Better security**: Models stay within your infrastructure

Trade-offs:
- **Larger deployment size**: Models included in container/deployment
- **Manual updates**: Need to manually update models
- **Storage requirements**: Additional disk space needed