# Local Models Implementation for LLM Guard

This implementation adds support for using locally downloaded models in LLM Guard scanners, following the patterns from the [official LLM Guard documentation](https://protectai.github.io/llm-guard/tutorials/notebooks/local_models/).

## Features Added

### 1. Environment Variable Configuration
- `LLM_GUARD_USE_LOCAL_MODELS`: Enable/disable local models (true/false)
- `LLM_GUARD_MODELS_PATH`: Path to local models directory (default: `./models`)

### 2. Automatic Model Configuration
When local models are enabled, the system automatically configures:

#### Input Scanners
- **PromptInjection**: Uses `deberta-v3-base-prompt-injection-v2`
- **Toxicity**: Uses `unbiased-toxic-roberta`
- **Code**: Uses `programming-language-identification`
- **Anonymize**: Uses `deberta-v3-base_finetuned_ai4privacy_v2`

#### Output Scanners
- **Toxicity**: Uses `unbiased-toxic-roberta`
- **Code**: Uses `programming-language-identification`

### 3. Fallback Behavior
- If local models are not configured, scanners use default HuggingFace download behavior
- Graceful handling of missing model files with appropriate logging

## Files Modified

### `guard_manager.py`
- Added model configuration imports
- Added `_check_local_models_config()` method
- Added `_configure_local_models()` method
- Updated scanner initialization to use local models when configured
- Enhanced logging to show local model status

### `config.py`
- Added `use_local_models` configuration option
- Added `models_path` configuration option
- Integrated with existing environment variable handling

### `config.yaml`
- Added local models configuration section
- Documented configuration options

## New Files Created

### `docs/LOCAL_MODELS_SETUP.md`
Comprehensive documentation including:
- Setup instructions
- Environment variable reference
- Model download procedures
- Docker deployment examples
- Troubleshooting guide
- Security considerations

### `download_models.sh`
Automated script to download all required models:
- Checks prerequisites (git, git-lfs)
- Downloads all required models
- Provides disk space warnings
- Supports dry-run mode
- Colorized output with progress tracking

### `test_local_models.py`
Comprehensive test suite:
- Tests local models disabled (default behavior)
- Tests local models enabled
- Validates scanner configurations
- Checks for model file existence
- Provides detailed logging

## Usage Examples

### Quick Start
```bash
# Download models
./download_models.sh

# Enable local models
export LLM_GUARD_USE_LOCAL_MODELS=true
export LLM_GUARD_MODELS_PATH=./models

# Test configuration
python3 test_local_models.py

# Run proxy with local models
python3 ollama_guard_proxy.py
```

### Docker Deployment
```dockerfile
FROM python:3.9

# Copy pre-downloaded models
COPY models/ /app/models/

# Set environment variables
ENV LLM_GUARD_USE_LOCAL_MODELS=true
ENV LLM_GUARD_MODELS_PATH=/app/models

WORKDIR /app
# ... rest of dockerfile
```

### Configuration File
```yaml
# config.yaml
use_local_models: true
models_path: "/opt/models"
```

## Benefits

### Performance
- **Faster startup**: No network downloads during initialization
- **Offline operation**: Works without internet connectivity
- **Consistent performance**: No dependency on external services

### Security
- **Air-gapped deployment**: Models stay within your infrastructure
- **Version control**: Use specific model versions
- **Reduced attack surface**: No external downloads at runtime

### Reliability
- **No network dependencies**: Eliminates download failures
- **Predictable resource usage**: Known model sizes and requirements
- **Easier debugging**: Local model paths in logs

## Model Requirements

The implementation requires these models to be downloaded:

| Scanner | Model Repository | Local Directory |
|---------|------------------|-----------------|
| PromptInjection | `protectai/deberta-v3-base-prompt-injection-v2` | `deberta-v3-base-prompt-injection-v2` |
| Toxicity (Input/Output) | `unitary/unbiased-toxic-roberta` | `unbiased-toxic-roberta` |
| Code (Input/Output) | `philomath-1209/programming-language-identification` | `programming-language-identification` |
| Anonymize | `Isotonic/deberta-v3-base_finetuned_ai4privacy_v2` | `deberta-v3-base_finetuned_ai4privacy_v2` |

## Testing

The implementation includes comprehensive testing:

```bash
# Run all tests
python3 test_local_models.py

# Check model downloads
./download_models.sh --check-only

# Dry run download
./download_models.sh --dry-run
```

## Integration

The local models feature integrates seamlessly with existing code:

```python
# Existing code works unchanged
manager = LLMGuardManager()

# Local models are automatically used if configured
result = manager.scan_input("test prompt")
```

## Backward Compatibility

- **Fully backward compatible**: Existing deployments continue to work without changes
- **Opt-in feature**: Local models are disabled by default
- **Graceful fallback**: If local models are configured but missing, falls back to default behavior

## Monitoring

Enhanced logging provides visibility:

```
INFO - Local models enabled via LLM_GUARD_USE_LOCAL_MODELS environment variable
INFO - Configured PromptInjection model path: ./models/deberta-v3-base-prompt-injection-v2
INFO - Input scanners initialized: 6 scanners ready (local_models: True)
INFO - Output scanners initialized: 5 scanners ready (local_models: True)
```

## Future Enhancements

Potential improvements for future versions:

1. **Model validation**: Checksum verification for downloaded models
2. **Model updates**: Automated update mechanisms for local models
3. **Model variants**: Support for different model versions/variants
4. **Custom models**: Easy integration of custom-trained models
5. **Model caching**: Intelligent caching strategies for better performance

## Troubleshooting

Common issues and solutions:

### Models Not Found
```
FileNotFoundError: [Errno 2] No such file or directory: './models/...'
```
**Solution**: Run `./download_models.sh` to download required models

### Permission Errors
```
PermissionError: [Errno 13] Permission denied
```
**Solution**: Check file permissions: `chmod -R 755 models/`

### Memory Issues
**Solution**: Use ONNX models only or increase system memory

See `docs/LOCAL_MODELS_SETUP.md` for detailed troubleshooting guide.

---

This implementation provides a robust, production-ready solution for using local models with LLM Guard while maintaining full backward compatibility and ease of use.