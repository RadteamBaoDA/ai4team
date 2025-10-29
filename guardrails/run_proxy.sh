#!/bin/bash
# Ollama Guard Proxy - Uvicorn Runner (Linux/macOS)
# Run the proxy with Uvicorn with support for parallel/concurrent requests
# 
# Usage:
#   ./run_proxy.sh start                     # Start proxy as background process (nohup)
#   ./run_proxy.sh stop                      # Stop running proxy
#   ./run_proxy.sh restart                   # Restart proxy
#   ./run_proxy.sh status                    # Check proxy status
#   ./run_proxy.sh logs                      # Show proxy logs
#   ./run_proxy.sh run [OPTIONS]             # Run proxy in foreground (interactive)
#
# Run Proxy with Options (foreground mode):
#   ./run_proxy.sh run                       # Default: single worker, 4 concurrent
#   ./run_proxy.sh run --workers 4 --concurrency 8
#   ./run_proxy.sh run --host 0.0.0.0 --port 8080
#   ./run_proxy.sh run --reload              # Auto-reload on code changes
#   ./run_proxy.sh run --debug               # Show debug logs
#
# Nginx-Only Access (restrict to Nginx proxy):
#   export NGINX_WHITELIST="127.0.0.1"                    # Single Nginx IP
#   export NGINX_WHITELIST="192.168.1.10,192.168.1.11"    # Multiple IPs
#   export NGINX_WHITELIST="192.168.1.0/24"               # CIDR range
#   ./run_proxy.sh start                                   # Start with whitelist
#
# Python Virtual Environment:
#   python3 -m venv venv                                    # Create venv
#   pip install -r requirements.txt                        # Install dependencies
#   export VENV_DIR="./venv"                               # Custom venv location
#   export USE_VENV="true"                                 # Enable venv (default)
#   ./run_proxy.sh start                                   # Start with venv
#
# Features:
#   - Uvicorn ASGI server
#   - Multi-worker support for parallel requests
#   - Configurable concurrency per worker
#   - Environment variable support
#   - Health check endpoint
#   - Request logging
#   - Background process management with nohup
#   - Automatic log file generation

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR"
PID_FILE="$LOG_DIR/proxy.pid"
LOG_FILE="$LOG_DIR/proxy.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Virtual environment setup
VENV_DIR="${VENV_DIR:-./venv}"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
USE_VENV="${USE_VENV:-true}"

# Default configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9999}"
WORKERS="${WORKERS:-4}"                    # Number of worker processes
CONCURRENCY="${CONCURRENCY:-128}"          # Concurrent connections per worker
LOG_LEVEL="${LOG_LEVEL:-info}"             # info, debug, warning, error
RELOAD="${RELOAD:-false}"
CONFIG_FILE="${CONFIG_FILE:-config.yaml}"
PROXY_MODULE="ollama_guard_proxy:app"

PROXY_MODULE="ollama_guard_proxy:app"
LLM_GUARD_USE_LOCAL_MODELS="True"

# Command to execute (start, stop, restart, status, logs, run)
COMMAND="${1:-help}"
shift 2>/dev/null || true

# Functions for process management
start_proxy() {
  # Check if already running
  if [ -f "$PID_FILE" ]; then
    local old_pid=$(cat "$PID_FILE")
    if ps -p "$old_pid" > /dev/null 2>&1; then
      echo "✗ Proxy is already running (PID: $old_pid)"
      return 1
    fi
  fi

  echo "Starting Ollama Guard Proxy..."
  
  # Create log directory if it doesn't exist
  mkdir -p "$LOG_DIR"
  
  # Debug: Show environment setup
  {
    echo "═══════════════════════════════════════════════════════════════"
    echo "STARTUP DEBUG INFO - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Script Configuration:"
    echo "  Script Dir:      $SCRIPT_DIR"
    echo "  Log Dir:         $LOG_DIR"
    echo "  PID File:        $PID_FILE"
    echo "  Log File:        $LOG_FILE"
    echo ""
    echo "Virtual Environment Settings:"
    echo "  USE_VENV:        $USE_VENV"
    echo "  VENV_DIR:        $VENV_DIR"
    echo "  VENV_ACTIVATE:   $VENV_ACTIVATE"
    echo ""
    echo "Checking Virtual Environment..."
    
    # Check VENV_DIR existence
    if [ -d "$VENV_DIR" ]; then
      echo "  ✓ VENV_DIR exists: $VENV_DIR"
      echo "    Contents:"
      ls -la "$VENV_DIR" 2>/dev/null | head -10
    else
      echo "  ✗ VENV_DIR does NOT exist: $VENV_DIR"
    fi
    
    # Check activate script
    if [ -f "$VENV_ACTIVATE" ]; then
      echo "  ✓ Activate script found: $VENV_ACTIVATE"
    else
      echo "  ✗ Activate script NOT found: $VENV_ACTIVATE"
      echo "    Expected: $VENV_ACTIVATE"
    fi
    
    # Check for python in venv
    if [ -f "$VENV_DIR/bin/python" ]; then
      echo "  ✓ Python executable found in venv"
      "$VENV_DIR/bin/python" --version 2>&1 | sed 's/^/    /'
    else
      echo "  ✗ Python executable NOT found in $VENV_DIR/bin/python"
    fi
    
    # Check for pip in venv
    if [ -f "$VENV_DIR/bin/pip" ]; then
      echo "  ✓ Pip executable found in venv"
    else
      echo "  ✗ Pip executable NOT found in $VENV_DIR/bin/pip"
    fi
    
    # Check for uvicorn in venv
    if [ -f "$VENV_DIR/bin/uvicorn" ]; then
      echo "  ✓ Uvicorn executable found in venv"
    else
      echo "  ✗ Uvicorn executable NOT found in $VENV_DIR/bin/uvicorn"
      echo "    Install with: $VENV_DIR/bin/pip install -r requirements.txt"
    fi
    
    echo ""
    echo "Proxy Configuration:"
    echo "  HOST:            $HOST"
    echo "  PORT:            $PORT"
    echo "  WORKERS:         $WORKERS"
    echo "  CONCURRENCY:     $CONCURRENCY"
    echo "  LOG_LEVEL:       $LOG_LEVEL"
    echo "  CONFIG_FILE:     $CONFIG_FILE"
    echo "  PROXY_MODULE:    $PROXY_MODULE"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
  } | tee -a "$LOG_FILE"
  
  # Check if virtual environment exists and is valid
  VENV_CMD=""
  if [ "$USE_VENV" = "true" ]; then
    if [ -f "$VENV_ACTIVATE" ]; then
      echo "✓ Using Python virtual environment: $VENV_DIR"
      VENV_CMD="source $VENV_ACTIVATE && "
    else
      echo "✗ Virtual environment activation FAILED!"
      echo ""
      echo "Reasons:"
      if [ ! -d "$VENV_DIR" ]; then
        echo "  1. VENV_DIR does not exist: $VENV_DIR"
      else
        echo "  1. VENV_DIR exists but activate script missing"
      fi
      if [ ! -f "$VENV_ACTIVATE" ]; then
        echo "  2. Activate script not found: $VENV_ACTIVATE"
      fi
      echo ""
      echo "To fix this, run:"
      echo "  python3 -m venv $VENV_DIR"
      echo "  source $VENV_ACTIVATE"
      echo "  pip install -r requirements.txt"
      echo ""
      echo "Or disable venv with: export USE_VENV=false"
      return 1
    fi
  else
    echo "⚠ Virtual environment disabled (USE_VENV=false)"
  fi
  
  # Start proxy with nohup, logging to current folder
  nohup bash -c "
    set -x  # Enable debug mode to see what's happening
    echo '[STARTUP] Starting Ollama Guard Proxy...'
    echo '[DEBUG] Bash version:' \"\$BASH_VERSION\"
    
    # Set working directory and Python path
    cd '$SCRIPT_DIR'
    export PYTHONPATH=\"$SCRIPT_DIR:\$PYTHONPATH\"
    echo '[PATH] Working directory:' \$(pwd)
    echo '[PATH] PYTHONPATH:' \$PYTHONPATH
    
    # Try to activate venv
    if [ -n \"$VENV_CMD\" ]; then
      echo '[VENV] Attempting to activate: $VENV_ACTIVATE'
      $VENV_CMD echo '[VENV] Successfully activated'
      if [ \$? -ne 0 ]; then
        echo '[ERROR] Failed to activate virtual environment'
        exit 1
      fi
    fi
    
    # Show Python info
    echo '[PYTHON] Python path:' \$(which python)
    echo '[PYTHON] Python version:' \$(python --version 2>&1)
    
    # Check uvicorn
    if ! python -c 'import uvicorn' 2>&1; then
      echo '[ERROR] uvicorn not installed. Install with: pip install uvicorn'
      exit 1
    fi
    echo '[UVICORN] uvicorn is available'
    
    # Check if guardrails module can be imported
    echo '[GUARD] Testing guardrails module import...'
    if ! python -c 'from guardrails.config import Config' 2>&1; then
      echo '[ERROR] Failed to import guardrails.config'
      echo '[ERROR] Current directory:' \$(pwd)
      echo '[ERROR] PYTHONPATH: '\$PYTHONPATH
      echo '[ERROR] Contents of current directory:'
      ls -la | head -20
      exit 1
    fi
    echo '[GUARD] Successfully imported guardrails.config'
    
    # Export environment variables
    export OLLAMA_URL=\"\${OLLAMA_URL:-http://127.0.0.1:11434}\"
    export PROXY_PORT=\"$PORT\"
    export CONFIG_FILE=\"$CONFIG_FILE\"
    export NGINX_WHITELIST=\"\${NGINX_WHITELIST:-}\"
    export ENABLE_INPUT_GUARD=\"\${ENABLE_INPUT_GUARD:-}\"
    export ENABLE_OUTPUT_GUARD=\"\${ENABLE_OUTPUT_GUARD:-}\"
    export ENABLE_IP_FILTER=\"\${ENABLE_IP_FILTER:-}\"
    export IP_WHITELIST=\"\${IP_WHITELIST:-}\"
    export IP_BLACKLIST=\"\${IP_BLACKLIST:-}\"
    export LLM_GUARD_USE_LOCAL_MODELS=\"\${LLM_GUARD_USE_LOCAL_MODELS:false}\"
    echo '[START] Running uvicorn with config:'
    echo '[START]   Module: $PROXY_MODULE'
    echo '[START]   Host: $HOST'
    echo '[START]   Port: $PORT'
    echo '[START]   Workers: $WORKERS'
    echo '[START]   Log Level: $LOG_LEVEL'
    echo '[START]   Using local model: $LLM_GUARD_USE_LOCAL_MODELS'
    echo ''
    
    uvicorn $PROXY_MODULE \\
      --host $HOST \\
      --port $PORT \\
      --workers $WORKERS \\
      --log-level $LOG_LEVEL
  " > "$LOG_FILE" 2>&1 &
  
  local pid=$!
  echo "$pid" > "$PID_FILE"
  sleep 2  # Give more time to detect startup errors
  
  # Verify process started
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "✓ Proxy started successfully (PID: $pid)"
    echo "✓ Log file: $LOG_FILE"
    echo "✓ Access: http://$HOST:$PORT/health"
    echo ""
    echo "View logs with: tail -f $LOG_FILE"
    return 0
  else
    echo "✗ Failed to start proxy (PID: $pid died)"
    echo ""
    echo "Debug information:"
    echo "─────────────────────────────────────────────────────────────"
    tail -30 "$LOG_FILE" 2>/dev/null || echo "(No log file available)"
    echo "─────────────────────────────────────────────────────────────"
    return 1
  fi
}

stop_proxy() {
  if [ ! -f "$PID_FILE" ]; then
    echo "✗ Proxy is not running (no PID file)"
    return 1
  fi
  
  local pid=$(cat "$PID_FILE")
  
  if ! ps -p "$pid" > /dev/null 2>&1; then
    echo "✗ Proxy is not running (PID $pid not found)"
    rm -f "$PID_FILE"
    return 1
  fi
  
  echo "Stopping Ollama Guard Proxy (PID: $pid)..."
  kill "$pid" 2>/dev/null || true
  
  # Wait for process to terminate
  local count=0
  while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
    sleep 0.5
    count=$((count + 1))
  done
  
  # Force kill if still running
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "Force killing proxy..."
    kill -9 "$pid" 2>/dev/null || true
    sleep 1
  fi
  
  rm -f "$PID_FILE"
  echo "✓ Proxy stopped"
  return 0
}

restart_proxy() {
  echo "Restarting Ollama Guard Proxy..."
  stop_proxy || true
  sleep 1
  start_proxy
}

status_proxy() {
  if [ ! -f "$PID_FILE" ]; then
    echo "✗ Proxy is not running (no PID file)"
    return 1
  fi
  
  local pid=$(cat "$PID_FILE")
  
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "✓ Proxy is running (PID: $pid)"
    echo "  Host: $HOST"
    echo "  Port: $PORT"
    echo "  Workers: $WORKERS"
    echo "  Config: $CONFIG_FILE"
    echo "  Ollama URL: $OLLAMA_URL"
    echo "  Nginx Whitelist: ${NGINX_WHITELIST:-empty (unrestricted)}"
    echo "  Log file: $LOG_FILE"
    echo "  Using local mode: $LLM_GUARD_USE_LOCAL_MODELS"
    echo ""
    echo "Recent logs:"
    tail -5 "$LOG_FILE"
    return 0
  else
    echo "✗ Proxy is not running (PID $pid not found)"
    rm -f "$PID_FILE"
    return 1
  fi
}

show_logs() {
  if [ ! -f "$LOG_FILE" ]; then
    echo "✗ No log file found: $LOG_FILE"
    return 1
  fi
  
  echo "Following logs from: $LOG_FILE (Press Ctrl+C to stop)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  tail -f "$LOG_FILE"
}

run_foreground() {
  # Parse arguments for run mode
  while [[ $# -gt 0 ]]; do
    case $1 in
      --host)
        HOST="$2"; shift 2
        ;;
      --port)
        PORT="$2"; shift 2
        ;;
      --workers)
        WORKERS="$2"; shift 2
        ;;
      --concurrency)
        CONCURRENCY="$2"; shift 2
        ;;
      --log-level)
        LOG_LEVEL="$2"; shift 2
        ;;
      --reload)
        RELOAD="true"; shift
        ;;
      --debug)
        LOG_LEVEL="debug"; shift
        ;;
      --config)
        CONFIG_FILE="$2"; shift 2
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      *)
        echo "Unknown option: $1"
        exit 1
        ;;
    esac
  done
  
  run_interactive
}

show_help() {
  cat << EOF
Ollama Guard Proxy - Process Manager

Usage: $0 <command> [OPTIONS]

Commands:
  start                    Start proxy as background process (nohup)
  stop                     Stop running proxy
  restart                  Restart proxy
  status                   Check proxy status
  logs                     View live proxy logs (tail -f)
  run [OPTIONS]            Run proxy in foreground (interactive)
  help                     Show this help message

Run Mode Options (with 'run' command):
  --host HOST              Server bind address (default: 0.0.0.0)
  --port PORT              Server port (default: 8080)
  --workers N              Number of worker processes (default: 4)
  --concurrency N          Concurrent requests per worker (default: 128)
  --log-level LEVEL        Logging level: debug, info, warning, error (default: info)
  --reload                 Auto-reload on code changes (development only)
  --debug                  Enable debug logging
  --config FILE            Config file path (default: config.yaml)
  --help                   Show this help message

Examples:
  # Start proxy as background service
  $0 start

  # Stop proxy
  $0 stop

  # Restart proxy
  $0 restart

  # Check status
  $0 status

  # View logs in real-time
  $0 logs

  # Run in foreground with custom settings
  $0 run --workers 8 --port 8080 --debug

  # Development mode with auto-reload
  $0 run --reload --debug

Environment Variables:
  OLLAMA_URL                 Ollama backend URL (e.g., http://127.0.0.1:11434)
  PROXY_PORT                 Proxy port
  NGINX_WHITELIST            Comma-separated IPs/CIDR for Nginx-only access
                             (e.g., "127.0.0.1,192.168.1.0/24")
                             Empty = allow all, for local dev only
  ENABLE_INPUT_GUARD         true/false
  ENABLE_OUTPUT_GUARD        true/false
  ENABLE_IP_FILTER           true/false
  IP_WHITELIST               Comma-separated IPs
  IP_BLACKLIST               Comma-separated IPs
  CONFIG_FILE                Configuration file path
  VENV_DIR                   Python virtual environment directory
                             (default: ./venv)
  USE_VENV                   true/false - Enable/disable venv activation
                             (default: true)
  LLM_GUARD_USE_LOCAL_MODELS true/false - Enable/disable local models

Log Files:
  All logs are written to: $LOG_DIR/proxy.log
  PID file: $PID_FILE

EOF
}

run_interactive() {

  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║         Ollama Guard Proxy - DEBUG Mode Startup                 ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
  
  # Set working directory and Python path immediately
  cd "$SCRIPT_DIR"
  export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
  echo "Note: Working directory set to: $(pwd)"
  echo "Note: PYTHONPATH includes: $SCRIPT_DIR"
  echo ""
  
  # ======================================================================
  # 1. CHECK PYTHON AVAILABILITY
  # ======================================================================
  echo "Step 1: Checking Python availability..."
  echo "─────────────────────────────────────────────────────────────────"
  
  PYTHON_CMD=""
  for py_version in python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$py_version" &> /dev/null; then
      echo "✓ Found: $py_version"
      version=$($py_version --version 2>&1)
      echo "  Version: $version"
      PYTHON_CMD="$py_version"
      break
    fi
  done
  
  if [ -z "$PYTHON_CMD" ]; then
    echo "✗ Error: No Python found. Please install Python 3.9+"
    echo ""
    echo "Debug Info:"
    echo "  PATH: $PATH"
    echo "  which python3: $(which python3 2>&1 || echo 'NOT FOUND')"
    echo "  which python: $(which python 2>&1 || echo 'NOT FOUND')"
    exit 1
  fi
  echo ""
  
  # ======================================================================
  # 2. CHECK AND ACTIVATE VIRTUAL ENVIRONMENT
  # ======================================================================
  echo "Step 2: Checking Virtual Environment..."
  echo "─────────────────────────────────────────────────────────────────"
  echo "  USE_VENV:      $USE_VENV"
  echo "  VENV_DIR:      $VENV_DIR"
  echo "  VENV_ACTIVATE: $VENV_ACTIVATE"
  echo ""
  
  VENV_ACTIVATED=false
  
  if [ "$USE_VENV" = "true" ]; then
    # Check directory
    if [ ! -d "$VENV_DIR" ]; then
      echo "✗ Virtual environment directory does NOT exist:"
      echo "  Expected: $VENV_DIR"
      echo ""
      echo "Debug Info:"
      ls -la "$(dirname "$VENV_DIR")" 2>/dev/null | grep -E "^d|^total" || echo "(parent directory not accessible)"
      echo ""
      echo "Fix: Create venv with:"
      echo "  $PYTHON_CMD -m venv $VENV_DIR"
      echo "  source $VENV_ACTIVATE"
      echo "  pip install -r requirements.txt"
      echo ""
      read -p "Create venv now? (y/n) " -n 1 -r
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR" || { echo "✗ Failed to create venv"; exit 1; }
        echo "✓ Venv created"
      else
        echo "Continuing without venv (will use system Python)..."
        USE_VENV=false
      fi
    else
      echo "✓ Virtual environment directory exists"
    fi
    
    # Check activate script
    if [ -f "$VENV_ACTIVATE" ]; then
      echo "✓ Activate script found"
      
      # Try to source it
      if source "$VENV_ACTIVATE" 2>&1; then
        echo "✓ Successfully activated virtual environment"
        VENV_ACTIVATED=true
      else
        echo "✗ Failed to activate virtual environment"
        echo "  Error output:"
        source "$VENV_ACTIVATE" 2>&1 | sed 's/^/    /'
        exit 1
      fi
    else
      echo "✗ Activate script NOT found: $VENV_ACTIVATE"
      echo ""
      echo "Expected structure:"
      echo "  $VENV_DIR/"
      echo "  ├── bin/"
      echo "  │   ├── activate           <-- THIS IS MISSING"
      echo "  │   ├── python"
      echo "  │   └── pip"
      echo "  └── lib/"
      echo ""
      echo "Current directory contents:"
      if [ -d "$VENV_DIR" ]; then
        ls -la "$VENV_DIR/" | head -15
      fi
      exit 1
    fi
    
    # Check for python in venv
    VENV_PYTHON="$VENV_DIR/bin/python"
    if [ ! -f "$VENV_PYTHON" ]; then
      echo "✗ Python executable NOT found in venv: $VENV_PYTHON"
      exit 1
    fi
    echo "✓ Python in venv: $($VENV_PYTHON --version 2>&1)"
    
  else
    echo "⚠ Virtual environment disabled (USE_VENV=false)"
    echo "  Using system Python: $PYTHON_CMD"
  fi
  echo ""
  
  # ======================================================================
  # 3. CHECK REQUIREMENTS
  # ======================================================================
  echo "Step 3: Checking Dependencies..."
  echo "─────────────────────────────────────────────────────────────────"
  
  # Check if requirements.txt exists
  if [ ! -f requirements.txt ]; then
    echo "⚠ Warning: requirements.txt not found"
    echo "  Skipping dependency check"
  else
    echo "✓ requirements.txt found"
    echo ""
    echo "  Checking required packages:"
    
    # Array of critical packages to check
    CRITICAL_PACKAGES=("uvicorn" "fastapi" "pydantic" "requests")
    MISSING_PACKAGES=()
    
    # Check each critical package
    for pkg in "${CRITICAL_PACKAGES[@]}"; do
      # Convert package name to import name (e.g., llm-guard -> llm_guard)
      import_name="${pkg//-/_}"
      
      if $PYTHON_CMD -c "import $import_name" 2>/dev/null; then
        version=$($PYTHON_CMD -c "import $import_name; print(getattr($import_name, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        echo "    ✓ $pkg (version: $version)"
      else
        echo "    ✗ $pkg NOT installed"
        MISSING_PACKAGES+=("$pkg")
      fi
    done
    
    # Check llm-guard separately (special case)
    if $PYTHON_CMD -c "import llm_guard" 2>/dev/null; then
      version=$($PYTHON_CMD -c "import llm_guard; print(getattr(llm_guard, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
      echo "    ✓ llm-guard (version: $version)"
    else
      echo "    ✗ llm-guard NOT installed"
      MISSING_PACKAGES+=("llm-guard")
    fi
    
    # If any packages are missing, prompt to install
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
      echo ""
      echo "✗ Missing packages: ${MISSING_PACKAGES[*]}"
      echo ""
      echo "Install all dependencies with:"
      if [ "$VENV_ACTIVATED" = true ]; then
        echo "  pip install -r requirements.txt"
      else
        echo "  $PYTHON_CMD -m pip install -r requirements.txt"
      fi
      echo ""
      read -p "Install missing packages now? (y/n) " -n 1 -r
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing dependencies..."
        if [ "$VENV_ACTIVATED" = true ]; then
          pip install -r requirements.txt || { echo "✗ Failed to install dependencies"; exit 1; }
        else
          $PYTHON_CMD -m pip install -r requirements.txt || { echo "✗ Failed to install dependencies"; exit 1; }
        fi
        echo "✓ Dependencies installed"
      else
        echo "Skipping installation. Some features may not work."
      fi
    else
      echo ""
      echo "✓ All required packages are installed"
    fi
  fi
  echo ""
  
  # ======================================================================
  # 4. CHECK CONFIGURATION
  # ======================================================================
  echo "Step 4: Checking Configuration..."
  echo "─────────────────────────────────────────────────────────────────"
  
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠ Warning: Config file '$CONFIG_FILE' not found"
    echo "  The proxy will use default configuration"
  else
    echo "✓ Config file found: $CONFIG_FILE"
  fi
  echo ""
  

  
  # ======================================================================
  # 5. FINAL STARTUP DISPLAY
  # ======================================================================
  echo "Step 5: Starting Uvicorn Server..."
  echo "─────────────────────────────────────────────────────────────────"
  
  # Export environment variables
  export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
  export PROXY_PORT="$PORT"
  export CONFIG_FILE="$CONFIG_FILE"
  export NGINX_WHITELIST="${NGINX_WHITELIST:-}"
  export ENABLE_INPUT_GUARD="${ENABLE_INPUT_GUARD:-true}"
  export ENABLE_OUTPUT_GUARD="${ENABLE_OUTPUT_GUARD:-true}"
  export ENABLE_IP_FILTER="${ENABLE_IP_FILTER:-}"
  export IP_WHITELIST="${IP_WHITELIST:-}"
  export IP_BLACKLIST="${IP_BLACKLIST:-}"
  export LLM_GUARD_USE_LOCAL_MODELS="${LLM_GUARD_USE_LOCAL_MODELS:-}"

  # Build uvicorn command
  UVICORN_CMD="uvicorn $PROXY_MODULE"
  UVICORN_CMD="$UVICORN_CMD --host $HOST"
  UVICORN_CMD="$UVICORN_CMD --port $PORT"
  UVICORN_CMD="$UVICORN_CMD --workers $WORKERS" 
  UVICORN_CMD="$UVICORN_CMD --log-level $LOG_LEVEL"

  # Add reload flag for development
  if [ "$RELOAD" = "true" ]; then
    UVICORN_CMD="$UVICORN_CMD --reload"
  fi

  # Display startup information
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║         Ollama Guard Proxy - Uvicorn Server                    ║"
  echo "╠════════════════════════════════════════════════════════════════╣"
  echo "║ Server Configuration:"
  echo "║   Host:       $HOST"
  echo "║   Port:       $PORT"
  echo "║   Workers:    $WORKERS"
  echo "║   Python Env:"
  if [ "$VENV_ACTIVATED" = true ]; then
    echo "║     ✓ Venv: $VENV_DIR (ACTIVE)"
  else
    echo "║     ✓ System Python: $PYTHON_CMD"
  fi
  echo "║"
  echo "║ Runtime Settings:"
  echo "║   Concurrency:     $CONCURRENCY per worker"
  echo "║   Log Level:       $LOG_LEVEL"
  echo "║   Reload:         $RELOAD"
  echo "║   Config File:    $CONFIG_FILE"
  echo "║   Working Dir:    $(pwd)"
  echo "║   PYTHONPATH:     $PYTHONPATH"
  echo "║"
  echo "║ Environment Variables:"
  echo "║   OLLAMA_URL:              $OLLAMA_URL"
  echo "║   NGINX_WHITELIST:         ${NGINX_WHITELIST:-empty (unrestricted)}"
  echo "║   ENABLE_INPUT_GUARD:      ${ENABLE_INPUT_GUARD:-not set}"
  echo "║   ENABLE_OUTPUT_GUARD:     ${ENABLE_OUTPUT_GUARD:-not set}"
  echo "║   ENABLE_IP_FILTER:        ${ENABLE_IP_FILTER:-not set}"
  echo "║   LLM_GUARD_USE_LOCAL_MODELS:        ${LLM_GUARD_USE_LOCAL_MODELS:-not set}"
  echo "║"
  echo "║ Testing proxy:"
  echo "║   curl http://$HOST:$PORT/health"
  echo "║"
  echo "║ Send request:"
  echo "║   curl -X POST http://$HOST:$PORT/v1/generate \\"
  echo "║     -H 'Content-Type: application/json' \\"
  echo "║     -d '{\"model\":\"mistral\",\"prompt\":\"test\"}'"
  echo "║"
  echo "║ Command: $UVICORN_CMD"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
  echo "Server starting... (Press Ctrl+C to stop)"
  echo ""

  # Run Uvicorn with configuration
  exec $UVICORN_CMD
}

# Main command dispatch
case "$COMMAND" in
  start)
    start_proxy
    ;;
  stop)
    stop_proxy
    ;;
  restart)
    restart_proxy
    ;;
  status)
    status_proxy
    ;;
  logs)
    show_logs
    ;;
  run)
    run_foreground "$@"
    ;;
  help|--help|-h|"")
    show_help
    ;;
  *)
    echo "✗ Unknown command: $COMMAND"
    echo ""
    show_help
    exit 1
    ;;
esac
