# Tiktoken Offline Mode Configuration

## Overview

The Ollama Guardrails system uses `tiktoken` for token counting through the `llm-guard` library. By default, tiktoken attempts to download encoding files from Azure, which requires network access and can cause issues in offline environments.

This guide explains how to configure tiktoken for offline operation using a local models folder.

## Quick Start

### 1. Automatic Setup (Recommended)

The offline mode is automatically configured when you run the application:

```bash
# Start the server - tiktoken offline mode is initialized automatically
python -m ollama_guardrails server

# Or using the CLI
ollama-guardrails server
```

### 2. Pre-download Tiktoken Encodings

To ensure all required encodings are available offline:

```bash
# Download default encodings (cl100k_base, p50k_base, p50k_edit, r50k_base)
ollama-guardrails tiktoken-download

# Download specific encodings
ollama-guardrails tiktoken-download -e cl100k_base p50k_base

# Download to custom cache directory
ollama-guardrails tiktoken-download -d /custom/path/to/cache
```

### 3. Verify Configuration

Check your tiktoken cache status:

```bash
ollama-guardrails tiktoken-info
```

Output example:
```
Tiktoken Offline Cache Configuration:
  Cache Directory: /abs/path/to/models/tiktoken
  Directory Exists: True
  Offline Mode: True
  Fallback Local: True
  Cache Size: 2.45 MB
  Cached Files (4):
    - cl100k_base.tiktoken
    - p50k_base.tiktoken
    - p50k_edit.tiktoken
    - r50k_base.tiktoken
```

## Configuration

### Environment Variables

Control tiktoken behavior with these environment variables:

```bash
# Set cache directory (default: ./models/tiktoken)
export TIKTOKEN_CACHE_DIR=/path/to/cache

# Enable offline mode (default: true)
export TIKTOKEN_OFFLINE_MODE=true

# Enable local fallback (default: true)
export TIKTOKEN_FALLBACK_LOCAL=true

# Start server with offline tiktoken
ollama-guardrails server
```

### Configuration File

You can also set these in your `config.yaml`:

```yaml
# This doesn't directly affect tiktoken, but you can set environment
# variables before running the application:
# export TIKTOKEN_CACHE_DIR=$(pwd)/models/tiktoken
# ollama-guardrails server --config config.yaml
```

## Directory Structure

After downloading encodings, your models folder will look like:

```
models/
├── tiktoken/              # Tiktoken cache directory
│   ├── cl100k_base.tiktoken
│   ├── p50k_base.tiktoken
│   ├── p50k_edit.tiktoken
│   ├── r50k_base.tiktoken
│   └── ... other encoding files
├── deberta/               # Other llm-guard models
│   ├── deberta-v3-base-prompt-injection-v2/
│   ├── deberta-v3-base_finetuned_ai4privacy_v2/
│   └── ...
└── llm-guard-models/
    ├── unbiased-toxic-roberta/
    ├── programming-language-identification/
    └── ...
```

## API Usage

### Python API

```python
from ollama_guardrails.utils.tiktoken_cache import (
    setup_tiktoken_offline_mode,
    download_tiktoken_encoding,
    get_tiktoken_cache_info,
    init_tiktoken_with_retry
)

# Setup offline mode (call before importing tiktoken)
setup_tiktoken_offline_mode('./models/tiktoken')

# Import after setup is safe
import tiktoken

# Get cache information
info = get_tiktoken_cache_info()
print(f"Cache size: {info['cache_size_mb']:.2f} MB")
print(f"Offline mode: {info['offline_mode']}")

# Download additional encodings if needed
download_tiktoken_encoding('cl100k_base', './models/tiktoken')

# Initialize with retry logic (useful for robust startup)
success = init_tiktoken_with_retry(max_retries=3)
```

## Troubleshooting

### Issue: "tiktoken encoding not found"

**Solution:** Download the required encodings:
```bash
ollama-guardrails tiktoken-download
```

### Issue: "Failed to download from Azure"

This is expected in offline mode. The application should:
1. Check local cache first
2. Use fallback encodings if available
3. Continue with reduced functionality if needed

Verify your cache is set up:
```bash
ollama-guardrails tiktoken-info
```

### Issue: "Permission denied" on cache directory

**Solution:** Ensure the cache directory is writable:
```bash
mkdir -p models/tiktoken
chmod 755 models/tiktoken
```

### Issue: "TIKTOKEN_CACHE_DIR not recognized"

Make sure environment variable is set BEFORE running the application:
```bash
# Incorrect (won't work):
ollama-guardrails server
export TIKTOKEN_CACHE_DIR=/path

# Correct (works):
export TIKTOKEN_CACHE_DIR=/path
ollama-guardrails server
```

## Docker Usage

### Dockerfile Configuration

```dockerfile
# In your Dockerfile
ENV TIKTOKEN_CACHE_DIR=/app/models/tiktoken
ENV TIKTOKEN_OFFLINE_MODE=true

# Copy pre-downloaded models
COPY models/tiktoken /app/models/tiktoken

# Or download during build
RUN ollama-guardrails tiktoken-download -d /app/models/tiktoken
```

### Docker Compose

```yaml
version: '3.8'
services:
  guardrails:
    image: ollama-guardrails:latest
    environment:
      TIKTOKEN_CACHE_DIR: /app/models/tiktoken
      TIKTOKEN_OFFLINE_MODE: "true"
    volumes:
      - ./models/tiktoken:/app/models/tiktoken
    ports:
      - "8080:8080"
```

## Performance Notes

- **Initial Load:** First-time initialization may take a few seconds as encodings are verified
- **Memory:** Tiktoken encodings are loaded on-demand, typically < 100MB
- **Disk:** Each encoding file is 1-3 MB depending on the encoding type
- **Offline:** Once cached, no network access is needed for encoding operations

## Supported Encodings

Common tiktoken encodings available for download:

- `cl100k_base` - Used by GPT-4 and GPT-3.5-turbo (most common, **recommended**)
- `p50k_base` - Used by GPT-3 and GPT-3.5
- `p50k_edit` - Used for edit operations
- `r50k_base` - Legacy encoding

To see all available encodings:
```bash
ollama-guardrails tiktoken-download -h
```

## Integration with LLM-Guard

Tiktoken offline mode works seamlessly with llm-guard scanners:

```python
from ollama_guardrails.guards.guard_manager import LLMGuardManager

# Initialization automatically uses offline tiktoken
guard_manager = LLMGuardManager(
    enable_input=True,
    enable_output=True,
    lazy_init=False  # Scanners initialize immediately
)

# All token counting uses local cached encodings
result = await guard_manager.scan_input("Your prompt here")
```

The `TokenLimit` scanner uses tiktoken internally and will work seamlessly with offline encodings.

## Development & Contribution

To add support for additional encodings:

1. Edit `src/ollama_guardrails/utils/tiktoken_cache.py`
2. Update the default encodings list in `cmd_tiktoken_download()`
3. Test with `ollama-guardrails tiktoken-download`

## References

- [Tiktoken Documentation](https://github.com/openai/tiktoken)
- [LLM-Guard Documentation](https://github.com/protectai/llm-guard)
- [OpenAI Token Counting](https://platform.openai.com/docs/guides/tokens)

## License

This offline mode configuration is part of the Ollama Guardrails project and follows the same MIT license.
