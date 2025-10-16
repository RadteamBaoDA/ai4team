# Ollama Guard Proxy with LLM Guard Integration

A secure proxy for Ollama that applies LLM Guard scanners to both input prompts and model outputs, with IP-based access control.

## Features

- **Input Scanning**: Detect prompt injection, toxicity, secrets, code, and token limits
- **Output Scanning**: Detect toxicity, bias, malicious URLs, and refusal patterns
- **IP-based Access Control**: Whitelist/blacklist client IP addresses or CIDR ranges
- **Streaming Support**: Handle streaming responses with real-time content filtering
- **Multiple Endpoints**: Support both `/api/generate` and `/v1/chat/completions` endpoints
- **Configuration Flexibility**: Configure via YAML file or environment variables
- **Comprehensive Logging**: Track all requests, scans, and access decisions

## Installation

### Prerequisites
- Python 3.9+
- Ollama running locally or remotely
- Docker and Docker Compose (optional, for containerized deployment)

### Local Installation

1. Clone the repository:
```bash
cd d:\Project\ai4team\guardrails
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp config.example.yaml config.yaml
```

4. Edit `config.yaml` to customize settings (see Configuration section below)

5. Run the proxy:
```bash
python ollama_guard_proxy.py
```

The proxy will start on `http://0.0.0.0:8080` by default.

### Docker Installation

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

This will start both Ollama and the guard proxy in containers.

2. Or build manually:
```bash
docker build -t ollama-guard-proxy .
docker run -p 8080:8080 \
  -e OLLAMA_URL=http://ollama:11434 \
  -e ENABLE_INPUT_GUARD=true \
  -e ENABLE_OUTPUT_GUARD=true \
  ollama-guard-proxy
```

## Configuration

### Environment Variables

```bash
# Ollama backend
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_PATH=/api/generate

# Proxy server
PROXY_HOST=0.0.0.0
PROXY_PORT=8080

# IP Access Control
ENABLE_IP_FILTER=false
IP_WHITELIST=192.168.1.0/24,10.0.0.1
IP_BLACKLIST=192.168.1.100,10.0.0.0/8

# LLM Guard Settings
ENABLE_INPUT_GUARD=true
ENABLE_OUTPUT_GUARD=true
BLOCK_ON_GUARD_ERROR=false

# Configuration file
CONFIG_FILE=config.yaml
```

### YAML Configuration File

Create `config.yaml`:

```yaml
ollama_url: http://127.0.0.1:11434
ollama_path: /api/generate

proxy_host: 0.0.0.0
proxy_port: 8080

# IP Access Control
enable_ip_filter: true
ip_whitelist: "192.168.1.0/24,10.0.0.1"
ip_blacklist: "192.168.1.100"

# LLM Guard
enable_input_guard: true
enable_output_guard: true
block_on_guard_error: false

# Scanner-specific settings
input_scanners:
  toxicity:
    threshold: 0.5
  token_limit:
    limit: 4000

output_scanners:
  toxicity:
    threshold: 0.5
```

## Usage

### Basic API Call

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "prompt": "What is machine learning?",
    "stream": false
  }'
```

### Streaming Response

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Explain quantum computing",
    "stream": true
  }'
```

### Chat Completion Endpoint

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ],
    "stream": false
  }'
```

### With Python Client

```python
import requests

url = "http://localhost:8080/v1/generate"
payload = {
    "model": "mistral",
    "prompt": "Tell me about AI safety",
    "stream": False
}

response = requests.post(url, json=payload)
print(response.json())
```

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456",
  "guards": {
    "input_guard": "enabled",
    "output_guard": "enabled",
    "ip_filter": "disabled"
  }
}
```

### Get Current Configuration

```bash
curl http://localhost:8080/config
```

## IP-Based Access Control

### Whitelist Only (Allow specific IPs)

```bash
ENABLE_IP_FILTER=true
IP_WHITELIST="192.168.1.0/24,10.0.0.1,172.16.0.0/12"
```

Only requests from these IP ranges/addresses will be allowed.

### Blacklist Only (Block specific IPs)

```bash
ENABLE_IP_FILTER=true
IP_BLACKLIST="192.168.1.100,10.0.0.0/8"
```

Requests from these IPs will be blocked; all others allowed.

### Mixed Mode (Both whitelist and blacklist)

If both are defined, blacklist is checked first. If an IP is blacklisted, it's denied. Otherwise, if whitelist is defined, it must be in the whitelist to be allowed.

### CIDR Notation Examples

```
192.168.1.0/24    # 192.168.1.0 - 192.168.1.255
10.0.0.0/8        # 10.0.0.0 - 10.255.255.255
172.16.0.0/12     # 172.16.0.0 - 172.31.255.255
10.0.0.1/32       # Exactly 10.0.0.1
```

## LLM Guard Scanners

### Input Scanners

- **BanSubstrings**: Block prompts containing specific banned words
- **PromptInjection**: Detect prompt injection attacks
- **Toxicity**: Identify toxic/offensive language (configurable threshold)
- **Secrets**: Detect API keys, passwords, and other secrets
- **Code**: Identify if prompt contains executable code
- **TokenLimit**: Enforce maximum prompt length

### Output Scanners

- **BanSubstrings**: Block responses containing specific banned words
- **Toxicity**: Identify toxic/offensive language in responses
- **MaliciousURLs**: Detect potentially malicious URLs
- **NoRefusal**: Ensure model doesn't refuse appropriate requests
- **Bias**: Detect biased language
- **Deanonymize**: Prevent revealing anonymized information

## Response Format

### Success Response

```json
{
  "model": "mistral",
  "created_at": "2024-01-15T10:30:45.123456Z",
  "response": "Machine learning is a subset of artificial intelligence...",
  "done": true,
  "context": [1, 2, 3, ...],
  "total_duration": 5000000000,
  "load_duration": 1000000000,
  "prompt_eval_count": 10,
  "prompt_eval_duration": 2000000000,
  "eval_count": 50,
  "eval_duration": 2000000000
}
```

### Error Response (Prompt Blocked)

```json
{
  "error": "prompt_blocked",
  "details": {
    "allowed": false,
    "scanners": {
      "Toxicity": {
        "passed": false,
        "reason": "Prompt contains toxic content"
      },
      "PromptInjection": {
        "passed": true,
        "reason": null
      }
    }
  }
}
```

### Error Response (Access Denied)

```json
{
  "error": "access_denied",
  "reason": "IP 192.168.1.50 is not in whitelist"
}
```

## Logging

Logs are written to stdout and optionally to files in the `logs/` directory.

Example log output:
```
2024-01-15 10:30:45,123 - ollama_guard_proxy - INFO - Request from 192.168.1.100: POST /v1/generate
2024-01-15 10:30:45,456 - ollama_guard_proxy - INFO - Input passed guards: {'Toxicity': {'passed': True}, ...}
2024-01-15 10:30:46,789 - ollama_guard_proxy - INFO - Output passed guards: {'Toxicity': {'passed': True}, ...}
2024-01-15 10:30:46,890 - ollama_guard_proxy - INFO - Response status: 200
```

## Advanced Usage

### Running with Nginx Load Balancer

See `nginx-guard.conf` for a full Nginx configuration that load balances across multiple guard proxy instances.

### Using with Multiple Ollama Instances

Configure the proxy to forward requests to an Ollama cluster:

```bash
OLLAMA_URL=http://ollama-lb:80  # Point to your load balancer
```

### Custom Scanner Configuration

Modify `ollama_guard_proxy.py` in the `_init_input_guard()` and `_init_output_guard()` methods to customize scanner behavior:

```python
def _init_input_guard(self):
    input_scanners = [
        BanSubstrings(["custom_word1", "custom_word2"]),
        PromptInjection(),
        Toxicity(threshold=0.7),  # Higher threshold = less sensitive
        Secrets(),
        TokenLimit(limit=8000),  # Increase token limit
    ]
    self.input_guard = Guard(input_scanners=input_scanners)
```

## Performance Considerations

- **Streaming**: Real-time scanning of streaming responses may introduce slight latency
- **Large Prompts**: Scanning very large prompts (> 10KB) may take additional time
- **Guard Initialization**: First startup loads NLP models, which may take 30-60 seconds
- **IP Filtering**: Whitelist/blacklist checking is very fast (negligible overhead)

## Troubleshooting

### Connection Refused to Ollama

```
ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Solution**: Ensure Ollama is running and `OLLAMA_URL` points to the correct address.

```bash
curl http://127.0.0.1:11434/api/tags  # Test Ollama connectivity
```

### LLM Guard Import Error

```
ModuleNotFoundError: No module named 'llm_guard'
```

**Solution**: Install LLM Guard:
```bash
pip install llm-guard
```

### 400 Request Header Too Large

**Solution**: This is handled by the proxy. If you still see this error, increase buffer sizes in config or disable some scanners.

### All Requests Blocked

Check if IP filtering is too strict:
```bash
curl -H "X-Real-IP: 192.168.1.100" http://localhost:8080/health
```

Verify IP whitelist/blacklist configuration.

## Docker Deployment

### Production Deployment

1. Set environment variables in `.env` file:
```
OLLAMA_URL=http://ollama:11434
ENABLE_IP_FILTER=true
IP_WHITELIST=192.168.0.0/16
```

2. Start with Docker Compose:
```bash
docker-compose -f docker-compose.yml up -d
```

3. Monitor logs:
```bash
docker-compose logs -f ollama-guard-proxy
```

### Health Checks

Docker health check is configured in the compose file. Check status:
```bash
docker inspect --format='{{.State.Health.Status}}' ollama-guard-proxy
```

## Security Best Practices

1. **Enable IP Filtering** in production environments
2. **Use HTTPS** with a reverse proxy (Nginx/Apache) for encrypted communication
3. **Set Strong Thresholds** for toxicity and injection detection
4. **Monitor Logs** regularly for suspicious patterns
5. **Update LLM Guard** frequently to get latest security patches
6. **Limit Token Limits** to prevent resource exhaustion
7. **Use Secrets Scanner** to prevent credential leakage

## Architecture

```
Client Request
    ↓
IP Access Control Check
    ↓
Parse Request / Extract Prompt
    ↓
Input Guards (Toxicity, Injection, Secrets, etc.)
    ↓
Forward to Ollama Backend
    ↓
Output Guards (Toxicity, URLs, Bias, etc.)
    ↓
Return Response to Client
```

## Support

For issues or questions:

1. Check logs: `docker-compose logs ollama-guard-proxy`
2. Test connectivity: `curl http://localhost:8080/health`
3. Verify configuration: `curl http://localhost:8080/config`
4. Refer to LLM Guard documentation: https://protectai.github.io/llm-guard/

## License

MIT License - See LICENSE file in repository

## Contributing

Contributions welcome! Please submit pull requests or issues to the repository.
