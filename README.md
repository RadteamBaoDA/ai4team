# AI4Team - Production-Grade LLM Infrastructure with Security & Knowledge Base

A comprehensive, production-ready platform combining secure LLM deployment, knowledge base management, and enterprise infrastructure for AI-powered applications.

## 🎯 Overview

**AI4Team** is a complete suite for deploying Large Language Models (LLMs) in enterprise environments with:

- 🛡️ **Advanced Security**: LLM Guard integration with multilingual error handling
- 📚 **Knowledge Base**: RAGFlow-powered document processing and retrieval
- 💬 **Real-time Chat**: Load-balanced chat service with Nginx
- 📦 **S3 Storage**: MinIO for artifact and model storage
- 🐳 **Container-Native**: Docker Compose for multi-environment deployment
- 🌍 **Multilingual**: Automatic language detection with localized responses
- ⚙️ **Enterprise Ready**: Nginx load balancing, rate limiting, SSL/TLS

## 📁 Project Structure

```
ai4team/
├── guardrails/              # LLM Security & Proxy Layer (PyPI-Ready Package)
│   ├── src/ollama_guardrails/        # Modern src-layout package structure  
│   ├── tests/                        # Test suite (unit & integration)
│   ├── models/                       # Pre-trained model storage (9 models)
│   ├── config/                       # Configuration files
│   ├── docker/                       # Docker deployment configs
│   ├── pyproject.toml                # Modern Python packaging (PEP 518/621)
│   ├── README.md                     # 📖 Detailed setup & usage guide
│   └── docs/                         # Comprehensive documentation
│
├── reranker/                # Document Reranking Service  
│   ├── src/reranker/                 # Organized package structure
│   ├── tests/                        # Test suite
│   ├── config/                       # Environment configurations
│   ├── pyproject.toml                # Modern Python packaging
│   └── README.md                     # 📖 Setup & configuration guide
│
├── llm/                     # LiteLLM Proxy with Guard Integration
│   ├── litellm_config.yaml           # LiteLLM configuration
│   ├── docker-compose.yml            # Docker deployment
│   ├── requirements.txt              # Python dependencies
│   └── README.md                     # 📖 Deployment & integration guide
│
├── knowledgebase/           # RAGFlow Knowledge Base
│   ├── docker-compose*.yml           # Multiple deployment configs
│   ├── nginx/                        # Nginx proxy configuration
│   └── README.md                     # 📖 Knowledge base setup guide
│
├── chat/                    # Real-time Chat Service
│   ├── *.compose.yaml                # Master/slave deployment configs
│   └── README.md                     # 📖 Chat service setup guide
│
├── s3/                      # MinIO S3-Compatible Storage
│   ├── *.compose.yml                 # Master/slave deployment configs
│   └── README.md                     # 📖 S3 storage setup guide
│
└── monitor/                 # Monitoring & Observability
    ├── langfuse.compose.yml          # Langfuse deployment
    └── README.md                     # 📖 Monitoring setup guide

### Local Utilities
- **structure_understand/** – A lightweight CLI that walks a codebase, summarizes files with Ollama/OpenAI, and emits Markdown, JSON, and Tabler-styled HTML reports (complete with searchable tables, path filters, and raw JSON dumps). Run the tool with `uv run python structure_understand/app.py` or `PYTHONPATH=src python structure_understand/app.py` to ensure the new `src` layout is respected when you edit the modules in-tree. The HTML output now renders a Tabler `<table>`, exposes the serialized payload, and shows plain-text summaries for quick review while the CLI writes the same data to a configurable `json_output_file` for downstream tooling.
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9-3.12 (for local development)
- 8GB+ RAM (recommended)
- NVIDIA GPU (optional, for faster inference)

### Quick Setup

Each service can be deployed independently. See individual README files for detailed instructions:

```bash
# 1. Guardrails (LLM Security Proxy) 
cd guardrails && pip install -e . && ollama-guardrails
# 📖 See guardrails/README.md for full setup guide

# 2. Knowledge Base (RAGFlow)
cd knowledgebase && docker-compose up -d  
# � See knowledgebase/README.md for configuration

# 3. Reranker Service
cd reranker && pip install -e . && reranker
# 📖 See reranker/README.md for deployment options

# 4. LiteLLM Proxy  
cd llm && python run_litellm_proxy.py
# 📖 See llm/README.md for integration guide

# 5. Chat Service
cd chat && docker-compose -f master.compose.yaml up -d
# 📖 See chat/README.md for load balancing setup

# 6. S3 Storage (MinIO)
cd s3 && docker-compose -f master.compose.yml up -d
# 📖 See s3/README.md for storage configuration

# 7. Monitoring (Langfuse)
cd monitor && docker-compose -f langfuse.compose.yml up -d
# 📖 See monitor/README.md for observability setup
```

**🔗 Component Documentation:**
- **[Guardrails](./guardrails/README.md)** - Security proxy with LLM Guard integration
- **[Reranker](./reranker/README.md)** - Document reranking with quantization support  
- **[LLM Proxy](./llm/README.md)** - Multi-provider LLM gateway with guardrails
- **[Knowledge Base](./knowledgebase/README.md)** - RAGFlow document processing
- **[Chat Service](./chat/README.md)** - Real-time chat with load balancing
- **[S3 Storage](./s3/README.md)** - MinIO distributed storage
- **[Monitoring](./monitor/README.md)** - Langfuse observability platform

## 🔐 Core Features

### Security (Guardrails)
- **LLM Guard Integration**: 12 scanners (7 input + 5 output) for comprehensive security
- **Multilingual Support**: Error messages in 7 languages with automatic detection
- **Rate Limiting**: Nginx-based load balancing with SSL/TLS
- **📖 [Full Security Guide](./guardrails/README.md)**

### Knowledge Management 
- **RAGFlow Integration**: Document processing and semantic search
- **Multi-modal Support**: Text, images, PDFs, and more
- **📖 [Knowledge Base Guide](./knowledgebase/README.md)**

### Document Processing
- **Advanced Reranking**: Quantization support and smart batching
- **Multi-backend Support**: HuggingFace, MLX (Apple Silicon)
- **📖 [Reranker Service Guide](./reranker/README.md)**

### LLM Gateway
- **Multi-provider Support**: OpenAI, Anthropic, Azure, AWS Bedrock
- **Custom Guardrails**: Integrated security scanning
- **📖 [LLM Proxy Guide](./llm/README.md)**

### Infrastructure
- **Distributed Chat**: Master/slave load-balanced chat service
- **S3 Storage**: MinIO with automatic failover
- **Monitoring**: Langfuse observability and tracing
- **📖 [Infrastructure Guides](./chat/README.md) | [Storage](./s3/README.md) | [Monitoring](./monitor/README.md)**

## 🔧 Configuration & Testing

Each service has its own configuration and testing setup. See individual README files for detailed information:

- **[Guardrails Configuration](./guardrails/README.md#configuration)** - YAML config, environment variables, security settings
- **[Reranker Configuration](./reranker/README.md#configuration)** - Environment configs for dev/prod/Apple Silicon
- **[LLM Proxy Configuration](./llm/README.md#configuration)** - Multi-provider setup and guardrail hooks
- **[Knowledge Base Configuration](./knowledgebase/README.md#configuration)** - Docker compose and service configs
- **[Infrastructure Configuration](./chat/README.md)** - Load balancing and distributed setup

### Quick Health Check

```bash
# Test all services
curl http://localhost:8080/health    # Guardrails
curl http://localhost:8001/health    # Reranker  
curl http://localhost:8000/health    # LLM Proxy
curl http://localhost:9380           # Knowledge Base
curl http://localhost:3000           # Monitoring
```

## 📖 Documentation

Each service includes comprehensive documentation in its respective folder:

- **[📖 Guardrails](./guardrails/README.md)** - Setup, API reference, security configuration
- **[📖 Reranker](./reranker/README.md)** - Deployment, performance optimization, quantization  
- **[📖 LLM Proxy](./llm/README.md)** - Multi-provider setup, guardrail integration
- **[📖 Knowledge Base](./knowledgebase/README.md)** - RAGFlow configuration, document processing
- **[📖 Chat Service](./chat/README.md)** - Load balancing, master/slave setup
- **[📖 S3 Storage](./s3/README.md)** - MinIO deployment, distributed storage
- **[📖 Monitoring](./monitor/README.md)** - Langfuse observability, metrics

### Additional Documentation
- **[📋 Deployment Guides](./guardrails/docs/)** - Production deployment checklist
- **[🔧 Configuration Examples](./*/config/)** - Service-specific configuration files
- **[🧪 Testing Guides](./*/tests/)** - Unit and integration testing

## 🚢 Deployment

### Quick Stack Deployment

```bash
# Deploy all services using Docker Compose
docker-compose -f guardrails/docker/docker-compose.yml \
               -f knowledgebase/docker-compose.yml \
               -f llm/docker-compose.yml \
               -f chat/master.compose.yaml \
               -f s3/master.compose.yml \
               -f monitor/langfuse.compose.yml up -d

# Or deploy services individually (see individual README files)
```

**📖 [Full Deployment Guide](./guardrails/docs/DEPLOYMENT.md)**

## 📝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support & Community

- 📖 **Documentation**: See individual service README files for detailed guides
- 🐛 **Issues**: [GitHub Issues](https://github.com/RadteamBaoDA/ai4team/issues)  
- 💬 **Discussions**: [GitHub Discussions](https://github.com/RadteamBaoDA/ai4team/discussions)
- **Repository**: [github.com/RadteamBaoDA/ai4team](https://github.com/RadteamBaoDA/ai4team)

## 🎓 Learning Resources

- [Ollama](https://ollama.ai) | [LLM Guard](https://protectai.github.io/llm-guard/) | [RAGFlow](https://docs.ragflow.io)
- [FastAPI](https://fastapi.tiangolo.com/) | [Nginx](https://nginx.org/en/docs/)

## 📊 Project Stats

- **Total Endpoints**: 20+ (Ollama, OpenAI, Admin APIs)
- **Supported Languages**: 7 (Chinese, Vietnamese, Japanese, Korean, Russian, Arabic, English)
- **Security Scanners**: 12 (7 input + 5 output scanners)
- **Pre-trained Models**: 9 specialized models for security scanning
- **Core Services**: 6 (Guardrails, Reranker, LLM Proxy, Knowledge Base, Chat, S3)
- **Package Structure**: Modern src-layout with 5 organized subpackages
- **CLI Commands**: 2 entry points (ollama-guardrails, guardrails-server)
- **Source Files**: 120+ Python files across all services
- **Documentation Files**: 50+ comprehensive guides
- **Configuration Options**: 100+ settings across all services
- **Docker Compose Files**: 16 deployment configurations
- **Python Compatibility**: 3.9-3.12 with full type hints

## 🗓️ Version History

### v2.1.0 (Current - November 2025)
- ✅ **PyPI-Ready Package**: Complete src-layout structure with pyproject.toml
- ✅ **CLI Interface**: `ollama-guardrails` and `guardrails-server` commands
- ✅ **Modern Packaging**: PEP 518/621 compliant with optional dependencies
- ✅ **Model Organization**: Pre-configured model storage directories
- ✅ **Enhanced Testing**: Unit and integration test structure
- ✅ **Development Tools**: Black, isort, flake8, mypy configuration
- ✅ **Type Safety**: Full type hints with mypy validation
- ✅ **Package Structure**: Organized api/, core/, guards/, middleware/, utils/

### v2.0.0 (January 2025)
- ✅ **Major Architecture Refactor**: Modularized monolithic codebase
- ✅ **Enhanced Guardrails**: 12 scanners (7 input + 5 output)
- ✅ **Reranker Service**: Complete package with quantization support
- ✅ **LiteLLM Integration**: Custom guardrail hooks
- ✅ **Concurrency Control**: Per-model request management
- ✅ **Caching Layer**: Redis + in-memory fallback
- ✅ **Cross-platform Scripts**: Linux, macOS, Windows support
- ✅ **Modern Packaging**: pyproject.toml, structured modules

### v1.0.0 (December 2024)
- ✅ Complete LLM Guard integration
- ✅ Multilingual error messages (7 languages)
- ✅ Nginx load balancing with rate limiting
- ✅ Knowledge base integration (RAGFlow)
- ✅ S3 storage with MinIO
- ✅ Docker Compose deployment
- ✅ Comprehensive documentation

## 🎉 Acknowledgments

Built with:
- [Ollama](https://ollama.ai) - LLM runtime
- [LLM Guard](https://protectai.github.io/llm-guard/) - Security scanning
- [RAGFlow](https://github.com/infiniflow/ragflow) - Knowledge base
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Nginx](https://nginx.org/) - Load balancing
- [MinIO](https://min.io/) - S3 storage
- [Docker](https://docker.com/) - Containerization

---

**Last Updated**: November 1, 2025  
**Version**: v2.1.0 (PyPI-Ready Package with Modern Structure)  
**Maintained By**: [RadteamBaoDA](https://github.com/RadteamBaoDA)  
**License**: MIT
