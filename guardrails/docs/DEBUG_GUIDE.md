# Ollama Guard Proxy - Debug Guide

## Overview

The updated `run_proxy.sh` script includes comprehensive debugging capabilities to help diagnose virtual environment and startup issues.

## What's New

### 1. **Enhanced Background Startup (`./run_proxy.sh start`)**

The `start` command now includes:

- **Pre-flight checks**: Validates the virtual environment setup before attempting to start
- **Detailed error messages**: Shows exactly what's wrong (missing venv, missing activate script, etc.)
- **Startup logs**: Writes debug information to the log file for later inspection
- **Automatic diagnosis**: Attempts to identify the root cause of failures

#### New Debug Output:

```
═══════════════════════════════════════════════════════════════
STARTUP DEBUG INFO - 2025-10-23 14:30:45
═══════════════════════════════════════════════════════════════

Script Configuration:
  Script Dir:      /home/local/ai4team/guardrails
  Log Dir:         /home/local/ai4team/guardrails
  PID File:        /home/local/ai4team/guardrails/proxy.pid
  Log File:        /home/local/ai4team/guardrails/proxy.log

Virtual Environment Settings:
  USE_VENV:        true
  VENV_DIR:        ./venv
  VENV_ACTIVATE:   ./venv/bin/activate

Checking Virtual Environment...
  ✗ VENV_DIR does NOT exist: ./venv
  ✗ Activate script NOT found: ./venv/bin/activate
  ✓ Python executable found: python3
  ✗ Pip executable NOT found: ./venv/bin/pip
  ✗ Uvicorn executable NOT found: ./venv/bin/uvicorn
    Install with: ./venv/bin/pip install -r requirements.txt
```

### 2. **Interactive Foreground Startup (`./run_proxy.sh run`)**

The `run` command now performs a **5-step startup validation**:

#### Step 1: Python Availability Check
- Searches for: `python3.12`, `python3.11`, `python3.10`, `python3.9`, `python3`, `python`
- Shows version information
- Lists available Python executables if none found

#### Step 2: Virtual Environment Validation
- Checks if venv directory exists
- Validates activate script exists
- Attempts to source the activate script
- **Interactive venv creation**: Offers to create venv if missing
- Shows detailed directory structure if venv is malformed
- Verifies Python executable inside venv

#### Step 3: Dependency Validation
- Checks for `uvicorn` installation
- Checks for `fastapi` installation
- Checks for `requirements.txt` file
- Shows package versions

#### Step 4: Configuration Validation
- Checks if config file exists
- Shows warning if using defaults

#### Step 5: Startup Information
- Displays complete server configuration
- Shows all environment variables
- Shows the exact uvicorn command being executed

## Common Issues and Solutions

### Issue 1: Virtual Environment Not Found

**Error Message:**
```
✗ Virtual environment directory does NOT exist:
  Expected: ./venv
```

**Solutions:**

**Option A - Create venv interactively (recommended):**
```bash
./run_proxy.sh run
# Say 'y' when asked to create venv
```

**Option B - Create venv manually:**
```bash
python3 -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
./run_proxy.sh start
```

**Option C - Use system Python:**
```bash
export USE_VENV=false
./run_proxy.sh start
```

### Issue 2: Activate Script Missing

**Error Message:**
```
✗ Activate script NOT found: ./venv/bin/activate

Expected structure:
  ./venv/
  ├── bin/
  │   ├── activate           <-- THIS IS MISSING
  │   ├── python
  │   └── pip
  └── lib/
```

**Solution:**

The venv directory is corrupted. Recreate it:

```bash
rm -rf ./venv
python3 -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
./run_proxy.sh start
```

### Issue 3: Uvicorn or FastAPI Not Installed

**Error Message:**
```
✗ Error: uvicorn not installed

Install with:
  pip install uvicorn
Or: python3 -m pip install -r requirements.txt
```

**Solution:**

```bash
# If using venv (after activating):
source ./venv/bin/activate
pip install -r requirements.txt

# If using system Python:
python3 -m pip install -r requirements.txt
```

### Issue 4: Python Not Found

**Error Message:**
```
✗ Error: No Python found. Please install Python 3.9+

Debug Info:
  PATH: /usr/bin:/bin:/usr/sbin:/sbin
  which python3: NOT FOUND
  which python: NOT FOUND
```

**Solution:**

Install Python:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.9 python3-pip python3-venv

# macOS
brew install python@3.9

# CentOS/RHEL
sudo yum install python39 python39-pip
```

## Debugging Features

### 1. **Detailed Log Files**

Background start logs are now more detailed:

```bash
tail -f ./proxy.log
```

Output includes:
- Startup timestamps
- Virtual environment activation logs
- Python environment information
- Uvicorn startup messages
- All error messages with context

### 2. **Debug Mode for Foreground Runs**

Enable debug logging:

```bash
./run_proxy.sh run --debug
```

This enables:
- `log-level: debug` for uvicorn
- More verbose error messages
- Full request/response logging

### 3. **Check Status Command**

View current proxy status with detailed information:

```bash
./run_proxy.sh status
```

Output shows:
- Running status (PID)
- Configuration
- Server settings
- Last 5 log entries

## Environment Variables for Debugging

### Control Venv Behavior

```bash
# Disable venv (use system Python)
export USE_VENV=false
./run_proxy.sh start

# Custom venv location
export VENV_DIR="/custom/path/to/venv"
./run_proxy.sh start

# Force venv (fail if not found)
export USE_VENV=true
./run_proxy.sh start
```

### Control Logging

```bash
# Change log level
export LOG_LEVEL=debug
./run_proxy.sh run

# Different log location
export LOG_DIR="/var/log/proxy"
./run_proxy.sh start
```

### Ollama Configuration

```bash
# Set Ollama backend URL
export OLLAMA_URL="http://192.168.1.2:11434"
./run_proxy.sh start

# Or for localhost
export OLLAMA_URL="http://127.0.0.1:11434"
./run_proxy.sh start
```

## Complete Startup Example

```bash
# Step 1: Navigate to directory
cd /home/local/ai4team/guardrails

# Step 2: Run with debug (interactive startup validation)
./run_proxy.sh run --debug

# You will see:
# ✓ Step 1: Checking Python availability... (finds python3)
# ✓ Step 2: Checking Virtual Environment... (creates venv interactively)
# ✓ Step 3: Checking Dependencies... (installs if needed)
# ✓ Step 4: Checking Configuration... (validates config)
# ✓ Step 5: Starting Uvicorn Server... (starts with full config display)

# Step 3: Test the proxy (in another terminal)
curl http://127.0.0.1:9999/health
# Response: {"status":"ok","version":"1.0"}

# Step 4: Send a test request
curl -X POST http://127.0.0.1:9999/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"Hello"}'
```

## Viewing Logs

### Background Process Logs

```bash
# View current logs
cat ./proxy.log

# Follow logs in real-time
tail -f ./proxy.log

# Use the built-in logs command
./run_proxy.sh logs

# View last N lines
tail -100 ./proxy.log

# Search for errors
grep -i error ./proxy.log

# Show debug messages
grep '\[DEBUG\]' ./proxy.log

# Show startup messages
grep '\[STARTUP\]\|\[VENV\]\|\[PYTHON\]\|\[UVICORN\]' ./proxy.log
```

### Process Information

```bash
# Check if running
./run_proxy.sh status

# See process details
ps aux | grep ollama_guard_proxy

# View resource usage
top -p $(cat ./proxy.pid 2>/dev/null)

# Kill with details
kill -v $(cat ./proxy.pid 2>/dev/null)
```

## Troubleshooting Commands

### Complete Reset

```bash
# Stop proxy
./run_proxy.sh stop

# Remove old venv
rm -rf ./venv

# Remove old PID file
rm -f ./proxy.pid

# Clear logs
> ./proxy.log

# Start fresh
./run_proxy.sh run --debug
```

### Verify Installation

```bash
# Check Python
python3 --version
python3 -m pip --version

# Check if venv module available
python3 -m venv --help

# Test venv creation
python3 -m venv /tmp/test_venv
source /tmp/test_venv/bin/activate
pip install uvicorn fastapi
python -c "import uvicorn; import fastapi; print('✓ All packages available')"
deactivate
rm -rf /tmp/test_venv
```

### Network Testing

```bash
# Test Ollama connection
curl http://127.0.0.1:11434/api/tags

# Test proxy health
curl http://127.0.0.1:9999/health

# Test with verbosity
curl -v http://127.0.0.1:9999/health

# Check if port is in use
lsof -i :9999
```

## Quick Reference

| Command | Purpose | Debug Info |
|---------|---------|-----------|
| `./run_proxy.sh start` | Start as background service | Pre-flight venv validation, detailed error messages |
| `./run_proxy.sh run` | Start in foreground (interactive) | 5-step validation, interactive venv creation, full config display |
| `./run_proxy.sh run --debug` | Start with debug logging | Enhanced logging, more verbose output |
| `./run_proxy.sh status` | Check running status | PID, configuration, last 5 log lines |
| `./run_proxy.sh logs` | Follow real-time logs | Continuous log display |
| `./run_proxy.sh stop` | Stop running proxy | Process termination info |

## Advanced Debugging

### Enable Bash Debug Mode

```bash
# Run with bash debug
bash -x ./run_proxy.sh run

# Shows every command being executed
```

### Custom Python Version

```bash
# Use specific Python version
export PYTHON_CMD=python3.9
./run_proxy.sh run

# Or install in custom venv
python3.9 -m venv ./venv39
source ./venv39/bin/activate
pip install -r requirements.txt
export VENV_DIR=./venv39
./run_proxy.sh start
```

### Port Issues

```bash
# If port 9999 is already in use
lsof -i :9999

# Use different port
./run_proxy.sh run --port 8888

# Kill existing process (if needed)
kill $(lsof -t -i :9999)
```

## Support Information

When reporting issues, include:

1. **Output from status command**:
   ```bash
   ./run_proxy.sh status
   ```

2. **Last 50 lines of log**:
   ```bash
   tail -50 ./proxy.log
   ```

3. **Python information**:
   ```bash
   python3 --version
   pip --version
   ```

4. **Virtual environment info**:
   ```bash
   ls -la ./venv/bin/
   ```

5. **Complete startup output** (from `./run_proxy.sh run --debug`)

