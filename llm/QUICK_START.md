# 🚀 Quick Reference Card - LiteLLM Proxy Deployment

## 5-Minute Setup

```bash
cd ~/ai4team/llm
./start_proxy.sh install    # Install all dependencies
./start_proxy.sh start      # Start the proxy
./start_proxy.sh status     # Verify it's running
curl http://localhost:8000/v1/models  # Test API
```

## All Commands

| Command | Purpose |
|---------|---------|
| `./start_proxy.sh install` | Install 10 dependencies |
| `./start_proxy.sh start` | Start proxy (background) |
| `./start_proxy.sh stop` | Stop proxy |
| `./start_proxy.sh restart` | Restart proxy |
| `./start_proxy.sh status` | Check if running |
| `./start_proxy.sh logs` | View live logs |
| `./start_proxy.sh validate` | Test configuration |
| `./start_proxy.sh help` | Show all options |

## Environment Variables

```bash
# Custom port
LITELLM_PORT=9000 ./start_proxy.sh start

# Custom config
CONFIG_FILE=my_config.yaml ./start_proxy.sh start

# Debug logging
LOG_LEVEL=DEBUG ./start_proxy.sh start
```

## Windows Commands

```cmd
start_proxy.bat install
start_proxy.bat start
start_proxy.bat status
start_proxy.bat logs
start_proxy.bat stop
```

## API Endpoints

```bash
# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-mistral",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Log Files

```bash
# Real-time logs
./start_proxy.sh logs

# Recent 50 lines
tail -50 logs/litellm_proxy.log

# Search for errors
grep ERROR logs/litellm_proxy.log

# Count requests
grep "chat/completions" logs/litellm_proxy.log | wc -l
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | `LITELLM_PORT=9000 ./start_proxy.sh start` |
| Installation fails | `python install_dependencies.py --upgrade` |
| Config validation fails | `./start_proxy.sh validate` (see logs) |
| Proxy won't start | `tail -20 logs/litellm_proxy.log` |
| Process not found | `./start_proxy.sh status` (check logs) |

## Files Reference

| File | Purpose |
|------|---------|
| `start_proxy.sh` | Main startup script (Linux/macOS) |
| `start_proxy.bat` | Windows startup script |
| `install_dependencies.py` | Dependency installer |
| `requirements.txt` | pip packages list |
| `litellm_config.yaml` | Proxy configuration |
| `litellm_guard_hooks.py` | Security guardrails |
| `DEPLOYMENT_SCRIPTS.md` | Full documentation |

## Security Features

- ✅ 10 security scanners
- ✅ 7 languages supported
- ✅ Input validation
- ✅ Output validation
- ✅ Streaming protection
- ✅ Automatic error response

## Performance Tuning

```bash
# Increase workers
LITELLM_WORKERS=8 ./start_proxy.sh start

# Use all CPU cores
LITELLM_WORKERS=$(nproc) ./start_proxy.sh start
```

## Production Deployment

```bash
# Install once
./start_proxy.sh install

# Start and keep running
nohup ./start_proxy.sh start > startup.log 2>&1 &

# Or use systemd (see DEPLOYMENT_SCRIPTS.md)
sudo systemctl start litellm-proxy
```

## Docker Quick Start

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN chmod +x start_proxy.sh
RUN ./start_proxy.sh install
EXPOSE 8000
CMD ["./start_proxy.sh", "start"]
```

```bash
# Build and run
docker build -t litellm-proxy .
docker run -p 8000:8000 litellm-proxy
```

## Advanced Options

```bash
# Multiple instances
LITELLM_PORT=8000 ./start_proxy.sh start &
LITELLM_PORT=9000 ./start_proxy.sh start &
LITELLM_PORT=10000 ./start_proxy.sh start &

# Custom log directory
LOG_DIR=/var/log/litellm ./start_proxy.sh start

# Custom workers
LITELLM_WORKERS=16 ./start_proxy.sh start
```

## Quick Tests

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. List models
curl http://localhost:8000/v1/models

# 3. Simple prompt
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "ollama-mistral", "messages": [{"role": "user", "content": "hi"}]}'

# 4. Security test (should be blocked)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "ollama-mistral", "messages": [{"role": "user", "content": "DROP DATABASE;"}]}'
```

## Status Check

```bash
# Is it running?
./start_proxy.sh status

# What's the process ID?
cat logs/litellm_proxy.pid

# How many requests processed?
grep -c "POST /v1/chat/completions" logs/litellm_proxy.log

# Any errors?
grep -c ERROR logs/litellm_proxy.log
```

## Restart Procedure

```bash
# Graceful restart
./start_proxy.sh restart

# Or manual restart
./start_proxy.sh stop
sleep 2
./start_proxy.sh start
```

## Documentation Links

- **Full Deployment Guide**: `DEPLOYMENT_SCRIPTS.md`
- **Guardrail Details**: `CUSTOM_GUARDRAIL_GUIDE.md`
- **API Reference**: `QUICK_REFERENCE.md`
- **Project Overview**: `PROJECT_COMPLETE.md`
- **All Deliverables**: `DELIVERABLES.md`

## Dependencies

```
litellm==1.41.0
llm-guard==0.3.18
pyyaml==6.0.1
pydantic==2.5.0
fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
redis==5.0.0
prometheus-client==0.19.0
python-dotenv==1.0.0
```

## One-Liners

```bash
# Start fresh
./start_proxy.sh install && ./start_proxy.sh start

# Check everything
./start_proxy.sh validate && ./start_proxy.sh status

# Monitor
watch -n 1 'tail logs/litellm_proxy.log | tail -5'

# Clean stop and restart
./start_proxy.sh stop; sleep 2; ./start_proxy.sh start

# Full reset
rm -rf logs/; ./start_proxy.sh start
```

---

**For more details, see DEPLOYMENT_SCRIPTS.md**

Last Updated: October 17, 2025
