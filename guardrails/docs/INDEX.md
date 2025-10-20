# Ollama Guard Proxy - Project Files Index

## Overview

Complete solution for deploying a secure Ollama proxy with LLM Guard integration and IP-based access control.

**Created**: October 16, 2025  
**Version**: 1.0  
**Status**: Production Ready

---

## File Structure

```
guardrails/
├── ollama_guard_proxy.py       # Main application
├── client_example.py           # Python client example
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Service orchestration
├── nginx-guard.conf            # Nginx reverse proxy config
├── config.example.yaml         # Configuration template
├── requirements.txt            # Python dependencies
├── SOLUTION.md                 # Project overview & architecture
├── USAGE.md                    # Comprehensive user guide
├── DEPLOYMENT.md               # Deployment & scaling guide
├── QUICKREF.md                 # Quick reference commands
├── README                      # Original LLM Guard README
└── INDEX.md                    # This file
```

---

## Core Files

### 1. `ollama_guard_proxy.py` (700+ lines)
**Purpose**: Main FastAPI application  
**Key Features**:
- LLM Guard integration for input/output scanning
- IP whitelist/blacklist access control
- Streaming and non-streaming request handling
- OpenAI-compatible chat endpoint
- Health check and config endpoints
- Comprehensive logging

**Key Classes**:
- `Config`: Configuration management
- `IPAccessControl`: IP filtering with CIDR support
- `LLMGuardManager`: LLM Guard initialization and scanning

**Usage**:
```bash
python ollama_guard_proxy.py
# or
uvicorn ollama_guard_proxy:app --host 0.0.0.0 --port 8080
```

---

### 2. `client_example.py` (300+ lines)
**Purpose**: Python client demonstrating all proxy features  
**Key Features**:
- Health checks
- Configuration retrieval
- Text generation (streaming and non-streaming)
- Chat completion requests
- Command-line interface

**Usage**:
```bash
python client_example.py --prompt "What is AI?"
python client_example.py --chat "Hello!"
python client_example.py --health
```

---

### 3. `Dockerfile` (30 lines)
**Purpose**: Docker container image definition  
**Base**: Python 3.11 slim  
**Includes**:
- System dependencies installation
- Python packages installation
- Health check configuration
- Proper signal handling

**Usage**:
```bash
docker build -t ollama-guard-proxy .
docker run -p 8080:8080 ollama-guard-proxy
```

---

### 4. `docker-compose.yml` (50+ lines)
**Purpose**: Complete service orchestration  
**Services**:
- `ollama`: Ollama backend service
- `ollama-guard-proxy`: Guard proxy service

**Features**:
- Volume persistence for Ollama data
- Environment configuration
- Health checks
- Internal networking
- Restart policies
- Logging configuration

**Usage**:
```bash
docker-compose up -d
docker-compose down
docker-compose logs -f
```

---

### 5. `nginx-guard.conf` (150+ lines)
**Purpose**: Production-ready Nginx configuration  
**Features**:
- HTTPS/SSL support
- Load balancing across multiple instances
- Security headers (HSTS, X-Content-Type-Options, etc.)
- Buffer optimization for large responses
- Health check endpoints
- Admin-restricted config access
- Error handling

**Usage**:
```bash
sudo cp nginx-guard.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx
```

---

### 6. `config.example.yaml` (60+ lines)
**Purpose**: Configuration template  
**Sections**:
- Ollama backend settings
- Proxy server configuration
- IP access control rules
- LLM Guard scanner settings
- Logging configuration

**Usage**:
```bash
cp config.example.yaml config.yaml
# Edit with your settings
python ollama_guard_proxy.py
```

---

### 7. `requirements.txt` (10 lines)
**Purpose**: Python dependency specification  
**Packages**:
- fastapi: Web framework
- uvicorn: ASGI server
- requests: HTTP client
- pydantic: Data validation
- pyyaml: YAML parsing
- llm-guard: LLM security scanning

**Usage**:
```bash
pip install -r requirements.txt
```

---

## Documentation Files

### 8. `SOLUTION.md` (Comprehensive)
**Purpose**: Project overview and architecture documentation  
**Sections**:
- Project summary
- Components overview
- Architecture diagram
- Features implemented
- Quick start guide
- Configuration examples
- API examples
- Security considerations
- Performance characteristics
- File summary
- Next steps

**Best For**: Understanding the complete solution

---

### 9. `USAGE.md` (Comprehensive)
**Purpose**: User guide and API documentation  
**Sections**:
- Installation instructions (local and Docker)
- Configuration guide (env vars and YAML)
- API usage examples (curl and Python)
- IP-based access control guide
- LLM Guard scanners description
- Response format examples
- Logging guide
- Advanced usage patterns
- Troubleshooting

**Best For**: Using the proxy in practice

---

### 10. `DEPLOYMENT.md` (Comprehensive)
**Purpose**: Deployment and operational guide  
**Sections**:
- Local development setup
- Docker single container and compose
- Production deployment checklist
- Nginx integration with SSL
- Scaling strategies (Docker, Kubernetes)
- Monitoring and logging setup
- Security hardening
- Performance tuning
- Troubleshooting
- Maintenance procedures

**Best For**: Deploying to production

---

### 11. `QUICKREF.md` (Quick Reference)
**Purpose**: Quick lookup for common commands  
**Sections**:
- Installation (all options)
- Configuration (env vars and YAML)
- API endpoints (all operations)
- Python client usage
- Docker commands
- Nginx setup
- Monitoring and debugging
- Common issues
- Production checklist
- Performance tuning
- Backup and restore
- Testing commands

**Best For**: Quick command lookup during operation

---

### 12. `README` (Original)
**Purpose**: LLM Guard documentation  
**Content**: Original README from the guardrails folder  
**Best For**: Understanding LLM Guard capabilities

---

## Quick Start Paths

### Path 1: Local Development (5 minutes)
1. Read: `QUICKREF.md` - Installation section
2. Run: 
   ```bash
   pip install -r requirements.txt
   cp config.example.yaml config.yaml
   python ollama_guard_proxy.py
   ```
3. Test:
   ```bash
   python client_example.py --health
   ```

### Path 2: Docker Deployment (2 minutes)
1. Read: `QUICKREF.md` - Docker section
2. Run:
   ```bash
   docker-compose up -d
   ```
3. Test:
   ```bash
   curl http://localhost:8080/health
   ```

### Path 3: Production Setup (30 minutes)
1. Read: `DEPLOYMENT.md` - Production Deployment section
2. Follow deployment steps
3. Configure IP filtering
4. Set up Nginx with SSL
5. Enable monitoring
6. Run security hardening

### Path 4: Understanding the Architecture
1. Read: `SOLUTION.md` - Project Summary
2. Read: `SOLUTION.md` - Architecture section
3. Review: `ollama_guard_proxy.py` - Key Classes section
4. Read: `USAGE.md` - API Examples section

---

## Configuration Examples

### Development (All Guards Enabled)
```yaml
ollama_url: http://127.0.0.1:11434
enable_input_guard: true
enable_output_guard: true
enable_ip_filter: false
```

### Testing (IP Filtering Enabled)
```yaml
ollama_url: http://127.0.0.1:11434
enable_ip_filter: true
ip_whitelist: "127.0.0.1,192.168.1.0/24"
enable_input_guard: true
enable_output_guard: true
```

### Production (Strict Validation)
```yaml
ollama_url: http://ollama:11434
enable_ip_filter: true
ip_whitelist: "10.0.0.0/8"
enable_input_guard: true
enable_output_guard: true
block_on_guard_error: false
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/generate` | POST | Ollama API generation (streaming support) |
| `/v1/chat/completions` | POST | OpenAI-compatible chat endpoint |
| `/health` | GET | Health check and status |
| `/config` | GET | View current configuration |

---

## Features Checklist

### Input Scanning
- [x] Prompt Injection Detection
- [x] Toxicity Analysis
- [x] Secret Detection
- [x] Code Injection Prevention
- [x] Token Limit Enforcement
- [x] Custom Substring Banning

### Output Scanning
- [x] Response Toxicity Checking
- [x] Bias Detection
- [x] Malicious URL Detection
- [x] Refusal Pattern Detection
- [x] Custom Substring Banning

### Access Control
- [x] IP Whitelist Support
- [x] IP Blacklist Support
- [x] CIDR Range Support
- [x] Dynamic IP Validation

### Operational
- [x] Streaming Support
- [x] Non-Streaming Support
- [x] Comprehensive Logging
- [x] Error Handling
- [x] Health Checks
- [x] Docker Support
- [x] Nginx Integration
- [x] Horizontal Scaling

---

## Dependencies

### Python Packages
- **fastapi** (0.104.1): Web framework
- **uvicorn** (0.24.0): ASGI server
- **requests** (2.31.0): HTTP client
- **pydantic** (2.5.0): Data validation
- **pyyaml** (6.0.1): YAML parsing
- **llm-guard** (0.3.18): LLM security scanning

### System Requirements
- Python 3.9+
- Docker & Docker Compose (for containerized deployment)
- Nginx (for production reverse proxy)
- Ollama (backend service)

---

## File Statistics

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| ollama_guard_proxy.py | Python | 700+ | Main application |
| client_example.py | Python | 300+ | Client example |
| Dockerfile | Config | 30 | Container definition |
| docker-compose.yml | Config | 50+ | Service orchestration |
| nginx-guard.conf | Config | 150+ | Reverse proxy config |
| config.example.yaml | Config | 60+ | Config template |
| requirements.txt | Config | 10 | Dependencies |
| SOLUTION.md | Doc | 400+ | Architecture & overview |
| USAGE.md | Doc | 600+ | User guide |
| DEPLOYMENT.md | Doc | 800+ | Deployment guide |
| QUICKREF.md | Doc | 300+ | Quick reference |
| **TOTAL** | - | **3000+** | - |

---

## Common Workflows

### Add Custom Scanner
1. Edit `ollama_guard_proxy.py`
2. Modify `_init_input_guard()` or `_init_output_guard()`
3. Restart: `docker-compose restart`

### Enable IP Filtering
1. Edit `config.yaml` or set env vars
2. Set `enable_ip_filter: true`
3. Configure whitelist/blacklist
4. Restart: `docker-compose restart`

### Scale to Multiple Instances
1. Run: `docker-compose up -d --scale ollama-guard-proxy=5`
2. Copy: `nginx-guard.conf` to Nginx
3. Reload: `sudo nginx -t && sudo systemctl reload nginx`

### Deploy to Production
1. Read: `DEPLOYMENT.md` - Production section
2. Follow deployment checklist
3. Configure Nginx with SSL
4. Enable monitoring

---

## Support Resources

### Documentation
- **SOLUTION.md**: Architecture and overview
- **USAGE.md**: User guide and examples
- **DEPLOYMENT.md**: Production deployment
- **QUICKREF.md**: Quick command lookup

### External Resources
- **LLM Guard**: https://protectai.github.io/llm-guard/
- **Ollama**: https://github.com/ollama/ollama
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker**: https://docs.docker.com/

### Troubleshooting
1. Check logs: `docker-compose logs -f`
2. Test health: `curl http://localhost:8080/health`
3. Verify config: `curl http://localhost:8080/config`
4. See QUICKREF.md for common issues

---

## Next Steps

1. **Choose Your Path**
   - Development? → Follow Path 1
   - Quick Docker? → Follow Path 2
   - Production? → Follow Path 3

2. **Review Relevant Documentation**
   - Start with appropriate documentation file
   - Customize configuration
   - Test locally first

3. **Deployment**
   - Start with Docker Compose
   - Move to Nginx when ready
   - Scale and monitor in production

4. **Ongoing**
   - Monitor logs and health
   - Keep LLM Guard updated
   - Adjust scanners as needed
   - Scale based on load

---

## Project Information

- **Created**: October 16, 2025
- **Version**: 1.0
- **Status**: Production Ready
- **Repository**: ai4team
- **Owner**: RadteamBaoDA
- **Branch**: main
- **License**: MIT (following LLM Guard)

---

## Support

For questions or issues:
1. Check the appropriate documentation file above
2. Review QUICKREF.md for common commands
3. Check proxy logs: `docker-compose logs`
4. Verify Ollama connectivity
5. Review LLM Guard documentation

---

**Happy deploying! 🚀**
