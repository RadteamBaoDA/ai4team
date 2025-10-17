# LiteLLM Proxy Deployment Scripts

Complete guide for deploying and managing the LiteLLM proxy with custom guardrails.

## Quick Start

### Linux/macOS
```bash
# Install dependencies
./start_proxy.sh install

# Start the proxy
./start_proxy.sh start

# Check status
./start_proxy.sh status

# View logs
./start_proxy.sh logs

# Stop the proxy
./start_proxy.sh stop

# Restart the proxy
./start_proxy.sh restart
```

### Windows
```cmd
# Install dependencies
start_proxy.bat install

# Start the proxy
start_proxy.bat start

# Check status
start_proxy.bat status

# View logs
start_proxy.bat logs

# Stop the proxy
start_proxy.bat stop

# Restart the proxy
start_proxy.bat restart
```

## Files Overview

### 1. `install_dependencies.py`
Python script that installs and verifies all required dependencies.

**Features:**
- Python 3.8+ version checking
- pip automatic upgrade
- 10 packages with pinned versions
- Installation verification (critical packages only)
- Requirements.txt support as alternative

**Installation Methods:**

```bash
# Method 1: Using the Python script directly
python install_dependencies.py

# Method 2: Using the startup script
./start_proxy.sh install          # Linux/macOS
start_proxy.bat install           # Windows

# Method 3: Using requirements.txt directly
pip install -r requirements.txt

# Method 4: With pip upgrade
python install_dependencies.py --upgrade
pip install --upgrade -r requirements.txt
```

**Output:**
```
Checking Python version... ✓ Python 3.11.0
Upgrading pip... ✓ pip upgraded to 23.3.1
Installing packages:
  litellm==1.41.0                    ✓
  llm-guard==0.3.18                  ✓
  pyyaml==6.0.1                      ✓
  pydantic==2.5.0                    ✓
  fastapi==0.104.1                   ✓
  uvicorn==0.24.0                    ✓
  requests==2.31.0                   ✓
  redis==5.0.0                       ✓
  prometheus-client==0.19.0          ✓
  python-dotenv==1.0.0               ✓
Verifying installation... ✓ All critical packages verified
Installation complete!
```

### 2. `start_proxy.sh` (Linux/macOS)
Main startup script using nohup for background process management.

**Commands:**

#### Start
```bash
./start_proxy.sh start
```
- Validates configuration
- Creates logs directory
- Starts proxy with nohup
- Saves process ID
- Returns startup information

**Options:**
```bash
# Custom configuration
./start_proxy.sh start --config /path/to/config.yaml

# Custom port
LITELLM_PORT=9000 ./start_proxy.sh start

# Custom host
LITELLM_HOST=127.0.0.1 ./start_proxy.sh start

# Custom workers
LITELLM_WORKERS=8 ./start_proxy.sh start

# Custom log level
LOG_LEVEL=DEBUG ./start_proxy.sh start
```

#### Status
```bash
./start_proxy.sh status
```
Shows if proxy is running with process ID.

#### Logs
```bash
./start_proxy.sh logs
```
Tails the proxy log file (Ctrl+C to exit).

#### Stop
```bash
./start_proxy.sh stop
```
- Gracefully terminates the process
- Removes PID file
- Waits for clean shutdown

#### Restart
```bash
./start_proxy.sh restart
```
- Stops the running proxy
- Waits 2 seconds
- Starts a new proxy instance

#### Validate
```bash
./start_proxy.sh validate
```
- Checks configuration file exists
- Validates guardrail setup
- Tests language detection

#### Install
```bash
./start_proxy.sh install
```
Installs all dependencies (uses install_dependencies.py or requirements.txt).

### 3. `start_proxy.bat` (Windows)
Windows batch script for proxy management.

**Commands:**

```cmd
# Start
start_proxy.bat start

# Status
start_proxy.bat status

# Logs
start_proxy.bat logs

# Stop
start_proxy.bat stop

# Restart
start_proxy.bat restart

# Validate
start_proxy.bat validate

# Install
start_proxy.bat install

# Help
start_proxy.bat help
```

**Environment Variables (Windows):**
```cmd
# Set custom port
set LITELLM_PORT=9000
start_proxy.bat start

# Set custom host
set LITELLM_HOST=192.168.1.100
start_proxy.bat start

# Set multiple variables
set LITELLM_PORT=9000 & set LITELLM_WORKERS=8 & start_proxy.bat start
```

### 4. `requirements.txt`
Standard Python requirements file listing all dependencies.

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

**Usage:**
```bash
pip install -r requirements.txt
```

## Deployment Workflow

### Initial Setup

```bash
# 1. Clone/navigate to LLM directory
cd ~/ai4team/llm

# 2. Install dependencies
./start_proxy.sh install

# 3. Validate configuration
./start_proxy.sh validate

# 4. Start the proxy
./start_proxy.sh start

# 5. Check status
./start_proxy.sh status

# 6. Verify logs
./start_proxy.sh logs
```

### Monitoring

```bash
# Real-time log viewing
./start_proxy.sh logs

# Check process
./start_proxy.sh status

# Manual log inspection
tail -f logs/litellm_proxy.log    # Linux/macOS
type logs\litellm_proxy.log       # Windows

# Count lines in log
wc -l logs/litellm_proxy.log

# Search for errors
grep -i "error" logs/litellm_proxy.log
```

### Maintenance

```bash
# Restart after config change
./start_proxy.sh restart

# Clean restart (stop, wait, start)
./start_proxy.sh stop
sleep 5
./start_proxy.sh start

# Emergency stop (kill process)
pkill -f "run_litellm_proxy.py"   # Linux/macOS
taskkill /F /IM python.exe       # Windows (caution!)

# Upgrade dependencies
./start_proxy.sh install --upgrade
```

## Configuration

### Environment Variables

All scripts respect these environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CONFIG_FILE` | `./litellm_config.yaml` | Path to LiteLLM config |
| `LOG_DIR` | `./logs` | Directory for log files |
| `LITELLM_HOST` | `0.0.0.0` | Bind host address |
| `LITELLM_PORT` | `8000` | Bind port number |
| `LITELLM_WORKERS` | `4` | Number of uvicorn workers |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Configuration File

The proxy reads `litellm_config.yaml`:

```yaml
guardrails:
  - id: "llm-guard-input"
    name: "LLM Guard Input"
    type: "custom_guardrail"
    fn: "litellm_guard_hooks.py"
    
  - id: "llm-guard-output"
    name: "LLM Guard Output"
    type: "custom_guardrail"
    fn: "litellm_guard_hooks.py"

model_list:
  - model_name: "ollama-mistral"
    litellm_params:
      model: "ollama/mistral"
      api_base: "http://192.168.1.2:11434"
    guardrails:
      - "llm-guard-input"
      - "llm-guard-output"
```

## Log Files

### Location
```
logs/
└── litellm_proxy.log    # Main proxy log
```

### Log Levels

- **DEBUG**: Detailed tracing, includes all API calls
- **INFO**: Normal operations, important events (default)
- **WARNING**: Potential issues, recoverable errors
- **ERROR**: Critical failures, unrecoverable errors

### Log Analysis

```bash
# View recent lines
tail -20 logs/litellm_proxy.log

# View all errors
grep ERROR logs/litellm_proxy.log

# View specific time range
sed -n '/2024-01-15 10:00/,/2024-01-15 11:00/p' logs/litellm_proxy.log

# Count events
grep -c "guardrail" logs/litellm_proxy.log

# Watch real-time
tail -f logs/litellm_proxy.log
```

## Testing the Deployment

### Health Check

```bash
# HTTP health endpoint
curl http://localhost:8000/health

# Expected response
{"status": "healthy"}
```

### API Test

```bash
# List available models
curl http://localhost:8000/v1/models

# Simple completion request
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-mistral",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

### Security Test

```bash
# Test SQL injection detection
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-mistral",
    "messages": [{"role": "user", "content": "'; DROP TABLE users; --"}],
    "max_tokens": 100
  }'

# Should return guardrail error, not execute
```

## Troubleshooting

### Process Won't Start

```bash
# Check configuration
./start_proxy.sh validate

# Check if port is in use
lsof -i :8000              # Linux/macOS
netstat -ano | find ":8000" # Windows

# Check logs
tail -50 logs/litellm_proxy.log

# Try with debug logging
LOG_LEVEL=DEBUG ./start_proxy.sh start
```

### Process Crashes

```bash
# Check for Python errors
python run_litellm_proxy.py --validate-only

# Check dependencies
python -c "import litellm; import llm_guard"

# Reinstall packages
./start_proxy.sh install --upgrade
```

### Memory Issues

```bash
# Monitor memory usage
# Linux/macOS
top -p $(cat logs/litellm_proxy.pid)

# Windows
tasklist /FI "PID eq <PID>"

# Reduce workers if needed
LITELLM_WORKERS=2 ./start_proxy.sh start
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000              # Linux/macOS
netstat -ano | grep 8000   # Windows

# Use different port
LITELLM_PORT=9000 ./start_proxy.sh start
```

## Advanced Usage

### Running Multiple Instances

```bash
# Terminal 1: Port 8000
./start_proxy.sh start

# Terminal 2: Port 9000
LITELLM_PORT=9000 ./start_proxy.sh start

# Terminal 3: Port 10000
LITELLM_PORT=10000 ./start_proxy.sh start
```

### Custom Configuration

```bash
# Create custom config
cp litellm_config.yaml litellm_config.prod.yaml
# Edit litellm_config.prod.yaml

# Start with custom config
CONFIG_FILE=litellm_config.prod.yaml ./start_proxy.sh start
```

### High Concurrency

```bash
# Increase workers for high load
LITELLM_WORKERS=16 ./start_proxy.sh start

# Or modify script to use CPU count
LITELLM_WORKERS=$(nproc) ./start_proxy.sh start
```

## Docker Integration

### Using in Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN chmod +x start_proxy.sh
RUN ./start_proxy.sh install

EXPOSE 8000

CMD ["./start_proxy.sh", "start"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  litellm-proxy:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LITELLM_PORT=8000
      - LITELLM_WORKERS=4
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./litellm_config.yaml:/app/litellm_config.yaml
```

## Performance Tuning

| Setting | Recommendation | Impact |
|---------|---|---|
| Workers | CPU cores × 2 | Throughput |
| Host | 0.0.0.0 | Accepts all connections |
| Port | 8000-9000 | Standard API range |
| Log Level | INFO | Performance vs detail |

## Systemd Service (Linux)

### Create Service File

```ini
# /etc/systemd/system/litellm-proxy.service
[Unit]
Description=LiteLLM Proxy with Custom Guardrails
After=network.target

[Service]
Type=forking
User=litellm
WorkingDirectory=/opt/litellm
ExecStart=/opt/litellm/start_proxy.sh start
ExecStop=/opt/litellm/start_proxy.sh stop
ExecReload=/opt/litellm/start_proxy.sh restart
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Manage Service

```bash
sudo systemctl enable litellm-proxy
sudo systemctl start litellm-proxy
sudo systemctl status litellm-proxy
sudo systemctl logs -f litellm-proxy
```

## Summary

| Task | Command |
|------|---------|
| Install | `./start_proxy.sh install` |
| Start | `./start_proxy.sh start` |
| Check | `./start_proxy.sh status` |
| Logs | `./start_proxy.sh logs` |
| Restart | `./start_proxy.sh restart` |
| Stop | `./start_proxy.sh stop` |
| Validate | `./start_proxy.sh validate` |

All scripts are production-ready and include error handling, logging, and status reporting.
