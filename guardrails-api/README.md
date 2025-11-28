# LLM Guard API - Standalone Deployment

LLM Guard API deployment for Ollama guardrails protection. This is a standalone API service based on [ProtectAI's LLM Guard](https://protectai.github.io/llm-guard/).

## Overview

This folder contains a standalone LLM Guard API deployment that can be used to protect Ollama (or any LLM) with input and output scanning. The API provides:

- **Input Scanners**: Protect against prompt injection, toxicity, PII leakage, secrets exposure, etc.
- **Output Scanners**: Detect bias, malicious URLs, toxicity, sensitive data in responses, etc.
- **REST API**: Simple HTTP endpoints for scanning prompts and outputs
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Quick Start

### Using Docker (Recommended)

1. **Start the API**:
```bash
docker-compose up -d
```

2. **Check health**:
```bash
curl http://localhost:8000/healthz
```

3. **Scan a prompt**:
```bash
curl -X POST http://localhost:8000/analyze/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

### Using Official Docker Image

```bash
docker pull laiyer/llm-guard-api:latest
docker run -d -p 8000:8000 \
  -e LOG_LEVEL='DEBUG' \
  -e AUTH_TOKEN='your-secret-token' \
  -v ./config/scanners.yml:/home/user/app/config/scanners.yml \
  laiyer/llm-guard-api:latest
```

### From Source

1. **Install dependencies**:
```bash
python -m pip install -r requirements.txt
```

2. **Run the API**:
```bash
llm_guard_api ./config/scanners.yml
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8000` | API port |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `AUTH_TOKEN` | `` | Bearer token for authentication (optional) |
| `SCAN_FAIL_FAST` | `true` | Stop on first scanner failure |
| `SCAN_PROMPT_TIMEOUT` | `30` | Prompt scan timeout (seconds) |
| `SCAN_OUTPUT_TIMEOUT` | `60` | Output scan timeout (seconds) |
| `LAZY_LOAD` | `true` | Load models on first request |
| `CACHE_MAX_SIZE` | `10000` | Maximum cache entries |
| `CACHE_TTL` | `3600` | Cache TTL (seconds) |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_LIMIT` | `60/minute` | Rate limit |

### Scanners Configuration

Edit `config/scanners.yml` to customize scanners. See [LLM Guard documentation](https://protectai.github.io/llm-guard/) for all available scanners and options.

#### Input Scanners
- **Anonymize**: Detect and anonymize PII
- **BanCode**: Block code in prompts
- **BanSubstrings**: Block specific words/phrases
- **BanTopics**: Block specific topics
- **Gibberish**: Detect gibberish text
- **InvisibleText**: Detect hidden/invisible text
- **Language**: Validate input language
- **PromptInjection**: Detect prompt injection attacks
- **Regex**: Custom regex patterns
- **Secrets**: Detect API keys, passwords, etc.
- **Sentiment**: Analyze sentiment
- **TokenLimit**: Limit prompt tokens
- **Toxicity**: Detect toxic content

#### Output Scanners
- **BanCode**: Block code in responses
- **BanSubstrings**: Block specific words/phrases
- **BanTopics**: Block specific topics
- **Bias**: Detect biased content
- **Deanonymize**: Restore anonymized data
- **FactualConsistency**: Check factual consistency
- **Gibberish**: Detect gibberish
- **Language**: Validate output language
- **LanguageSame**: Ensure response matches input language
- **MaliciousURLs**: Detect malicious URLs
- **NoRefusal**: Detect refusals
- **ReadingTime**: Limit response length
- **Regex**: Custom regex patterns
- **Relevance**: Check response relevance
- **Sensitive**: Detect sensitive data
- **Sentiment**: Analyze sentiment
- **Toxicity**: Detect toxic content

## API Endpoints

### Health Check
```
GET /healthz
```

### Readiness Check
```
GET /readyz
```

### Analyze Prompt
```
POST /analyze/prompt
Content-Type: application/json

{
  "prompt": "Your prompt text here"
}
```

### Analyze Output
```
POST /analyze/output
Content-Type: application/json

{
  "prompt": "Original prompt",
  "output": "LLM response to scan"
}
```

### Swagger UI
When `LOG_LEVEL=DEBUG`:
```
GET /swagger.json
```

## Integration with Ollama

### Option 1: Proxy Integration
Use the `guardrails` project which acts as a proxy between clients and Ollama, automatically scanning all requests and responses.

### Option 2: Direct API Calls
Call the LLM Guard API directly before/after Ollama requests:

```python
import httpx

LLM_GUARD_URL = "http://localhost:8000"
OLLAMA_URL = "http://localhost:11434"

async def chat_with_guard(prompt: str):
    async with httpx.AsyncClient() as client:
        # Scan input
        input_result = await client.post(
            f"{LLM_GUARD_URL}/analyze/prompt",
            json={"prompt": prompt}
        )
        input_data = input_result.json()
        
        if not input_data.get("is_valid", True):
            return {"error": "Input blocked by guardrails"}
        
        # Use sanitized prompt
        safe_prompt = input_data.get("sanitized_prompt", prompt)
        
        # Call Ollama
        ollama_result = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama2", "prompt": safe_prompt}
        )
        response = ollama_result.json()["response"]
        
        # Scan output
        output_result = await client.post(
            f"{LLM_GUARD_URL}/analyze/output",
            json={"prompt": safe_prompt, "output": response}
        )
        output_data = output_result.json()
        
        if not output_data.get("is_valid", True):
            return {"error": "Output blocked by guardrails"}
        
        return {"response": output_data.get("sanitized_output", response)}
```

## LiteLLM Integration

Use LLM Guard with LiteLLM Proxy to moderate calls across 100+ LLMs including Ollama models.

Reference: https://protectai.github.io/llm-guard/tutorials/litellm/

### Quick Start with LiteLLM

1. **Start LLM Guard API**:
```bash
docker-compose up -d
```

2. **Set environment variables**:
```bash
export LLM_GUARD_API_BASE="http://localhost:8000"
export OLLAMA_API_BASE="http://192.168.1.2:11434"
```

3. **Start LiteLLM Proxy**:
```bash
# Linux/macOS
./start_litellm.sh

# Windows
start_litellm.bat
```

Or manually:
```bash
litellm --config litellm_llmguard_config.yaml --port 4000
```

4. **Test with curl**:
```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-litellm-master-key" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### LiteLLM Configuration Files

- `litellm_llmguard_config.yaml` - Basic configuration with LLM Guard for all requests
- `litellm_advanced_config.yaml` - Advanced config with per-key/per-request guard control

### LLM Guard Modes

| Mode | Description |
|------|-------------|
| `all` | Apply guardrails to all requests (default) |
| `key-specific` | Only apply to API keys with `enable_llm_guard_check=true` |
| `request-specific` | Only apply when request includes `enable_llm_guard_check` |

### Per-Request Guard Control

Using OpenAI SDK:
```python
import openai

client = openai.OpenAI(
    api_key="sk-your-key",
    base_url="http://localhost:4000"
)

response = client.chat.completions.create(
    model="llama3.2",
    messages=[{"role": "user", "content": "Hello!"}],
    extra_body={
        "metadata": {
            "permissions": {
                "enable_llm_guard_check": True
            }
        }
    }
)
```

## GPU Support

For NVIDIA GPU acceleration:

```bash
docker-compose -f docker-compose.gpu.yml up -d
```

## Local Models

To use locally downloaded models instead of downloading from HuggingFace:

1. Download models to `./models/` directory
2. Uncomment `model_path` in `config/scanners.yml`
3. Set model paths for each scanner

## Observability

### Metrics
Prometheus metrics available at `/metrics` when `METRICS_TYPE=prometheus`.

### Tracing
Supports OpenTelemetry tracing. Configure with:
- `TRACING_EXPORTER`: `console`, `otel_http`, or `xray`
- `TRACING_OTEL_ENDPOINT`: OpenTelemetry collector endpoint

## Best Practices

1. **Enable `SCAN_FAIL_FAST`** to avoid unnecessary scans
2. **Enable caching** with `CACHE_MAX_SIZE` and `CACHE_TTL`
3. **Enable authentication** in production with `AUTH_TOKEN`
4. **Enable lazy loading** to improve startup time
5. **Use local models** to avoid downloading on each container start
6. **Allocate sufficient memory** - recommend at least 8GB RAM

## Troubleshooting

### Out-of-memory error
- Reduce number of enabled scanners in `config/scanners.yml`
- Enable `low_cpu_mem_usage` in scanner params
- Increase Docker memory limit

### Failed HTTP probe
- Increase `start_period` in healthcheck
- Enable `lazy_load` in configuration

### Slow startup
- Enable `lazy_load: true` in configuration
- Use local models

## References

- [LLM Guard Documentation](https://protectai.github.io/llm-guard/)
- [LLM Guard API Overview](https://protectai.github.io/llm-guard/api/overview/)
- [LLM Guard API Deployment](https://protectai.github.io/llm-guard/api/deployment/)
- [LLM Guard GitHub](https://github.com/protectai/llm-guard)
