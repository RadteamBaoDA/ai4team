# Ollama Guardrails

Advanced LLM Guard Proxy for Ollama with comprehensive security scanning, built with modern Python practices.

## Features

- 🛡️ **Input/Output Scanning**: Comprehensive LLM Guard integration for content safety
- 🔒 **IP Whitelisting**: Restrict access to authorized IPs only  
- ⚡ **Streaming Support**: Full support for streaming responses
- 📊 **Performance Monitoring**: Built-in caching and performance metrics
- 🔄 **OpenAI Compatibility**: Drop-in replacement for OpenAI API endpoints
- 🐍 **Modern Python**: Built for Python 3.9+ with async/await and type hints

## Installation

### From PyPI (Recommended)

```bash
pip install ollama-guardrails
```

### From Source

```bash
git clone https://github.com/RadteamBaoDA/ai4team.git
cd ai4team/guardrails
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/RadteamBaoDA/ai4team.git
cd ai4team/guardrails
pip install -e ".[dev]"
```

## Quick Start

### Command Line

```bash
# Start the server
ollama-guardrails server

# With custom config
ollama-guardrails server --config config.yaml

# Validate configuration
ollama-guardrails validate-config --config config.yaml
```

### Python Module

```bash
# Run as module
python -m ollama_guardrails server

# With config
python -m ollama_guardrails server --config config.yaml
```

### Programmatic Usage

```python
from ollama_guardrails import create_app

# Create app instance
app = create_app(config_file="config.yaml")

# Run with uvicorn
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)
```

## Configuration

Create a `config.yaml` file:

```yaml
# Ollama backend
ollama_url: "http://localhost:11434"

# Proxy settings
proxy_host: "0.0.0.0"
proxy_port: 8080

# Guards
enable_input_guard: true
enable_output_guard: true

# Caching
cache_enabled: true
cache_backend: "memory"  # or "redis"
cache_ttl: 3600

# IP Whitelist (optional)
nginx_whitelist:
  - "127.0.0.1"
  - "192.168.1.0/24"
```

## API Endpoints

### Ollama API Compatibility
- `POST /api/generate` - Text generation
- `POST /api/chat` - Chat completions  
- `POST /api/embed` - Embeddings
- `GET /api/tags` - List models
- And more...

### OpenAI API Compatibility
- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `POST /v1/embeddings` - Embeddings
- `GET /v1/models` - List models

### Administrative
- `GET /health` - Health check
- `GET /stats` - Performance statistics
- `GET /config` - Current configuration
- `POST /admin/cache/clear` - Clear cache

## Offline Mode

For offline operation and to avoid downloading models from Azure or Hugging Face, configure both tiktoken and Hugging Face to use local cache:

**Quick Setup (Recommended):**

```bash
# Linux/macOS - Setup both tiktoken and Hugging Face
./init_tiktoken_new.sh

# Windows - Setup both tiktoken and Hugging Face
init_all_offline.bat

# Or use Python to setup both with custom models
python setup_tiktoken.py --models bert-base-uncased sentence-transformers/all-mpnet-base-v2

# Or use Python CLI directly
python -m ollama_guardrails tiktoken-download
python -m ollama_guardrails hf-download -m bert-base-uncased
```

**Verify setup:**
```bash
python -m ollama_guardrails tiktoken-info
python -m ollama_guardrails hf-info
```

**Start server** - uses local cache automatically:
```bash
python -m ollama_guardrails server
```

For complete setup guide, see [Tiktoken Setup Guide](docs/TIKTOKEN_SETUP_GUIDE.md) and [Tiktoken Offline Mode Documentation](docs/TIKTOKEN_OFFLINE_MODE.md).

## Development

### Project Structure

```
guardrails/
├── src/ollama_guardrails/           # Main package
│   ├── __init__.py                  # Package exports
│   ├── __main__.py                  # Module execution
│   ├── app.py                       # FastAPI application
│   ├── cli.py                       # Command line interface
│   ├── server.py                    # Server entry point
│   ├── api/                         # API endpoints
│   │   ├── endpoints_ollama.py      # Ollama endpoints
│   │   ├── endpoints_openai.py      # OpenAI endpoints
│   │   └── endpoints_admin.py       # Admin endpoints
│   ├── core/                        # Core functionality
│   │   ├── config.py                # Configuration management
│   │   ├── cache.py                 # Caching system
│   │   └── concurrency.py          # Concurrency management
│   ├── guards/                      # LLM Guard integration
│   │   └── guard_manager.py         # Guard manager
│   ├── middleware/                  # HTTP middleware
│   │   ├── ip_whitelist.py          # IP filtering
│   │   └── http_client.py           # HTTP client
│   └── utils/                       # Utilities
│       ├── utils.py                 # Helper functions
│       └── language.py              # Language support
├── tests/                           # Test suite
│   ├── unit/                        # Unit tests
│   └── integration/                 # Integration tests
├── pyproject.toml                   # Modern Python packaging
├── setup.py                         # Legacy compatibility
└── README.md                        # This file
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=ollama_guardrails

# Run specific test types
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

### Code Quality

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Docker Support

```bash
# Build image
docker build -t ollama-guardrails .

# Run container
docker run -p 8080:8080 \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  ollama-guardrails
```

## Performance

- **Async Architecture**: Built on FastAPI with full async support
- **Intelligent Caching**: Redis or in-memory caching for guard results  
- **Connection Pooling**: Efficient HTTP client management
- **Concurrency Control**: Intelligent request queuing and parallel processing

## Security Features

- **Input Sanitization**: Prompt injection, toxicity, and secret detection
- **Output Filtering**: Response content safety and bias detection
- **IP Whitelisting**: Network-level access control
- **Rate Limiting**: Built-in request throttling
- **Audit Logging**: Comprehensive request/response logging

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/RadteamBaoDA/ai4team/issues)
- Documentation: [Full documentation](docs/)
- Examples: [Usage examples](examples/)