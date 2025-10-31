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

# Get script directory (scripts/) and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/proxy.pid"
LOG_FILE="$LOG_DIR/proxy.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create log directory
mkdir -p "$LOG_DIR"

# Virtual environment setup
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv}"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
USE_VENV="${USE_VENV:-true}"

# Default configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9999}"
LOG_LEVEL="${LOG_LEVEL:-info}"             # info, debug, warning, error
RELOAD="${RELOAD:-false}"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_ROOT/config/config.yaml}"
PROXY_MODULE="src.ollama_guard_proxy:app"
LLM_GUARD_USE_LOCAL_MODELS="True"
SCAN_FAIL_FAST="True"
# Command to execute (start, stop, restart, status, logs, run)
COMMAND="${1:-help}"
shift 1 >/dev/null 2>&1 || true

# Function to export all necessary environment variables
export_variables() {
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
    export LLM_GUARD_USE_LOCAL_MODELS="${LLM_GUARD_USE_LOCAL_MODELS:-True}"
    export SCAN_FAIL_FAST="${SCAN_FAIL_FAST:-True}"
    
    # Cache configuration
    export CACHE_ENABLED="${CACHE_ENABLED:-true}"
    export CACHE_BACKEND="${CACHE_BACKEND:-auto}"
    export CACHE_TTL="${CACHE_TTL:-3600}"
    export CACHE_MAX_SIZE="${CACHE_MAX_SIZE:-1000}"
    
    # Redis configuration
    export REDIS_ENABLED="${REDIS_ENABLED:-true}"
    export REDIS_HOST="${REDIS_HOST:-localhost}"
    export REDIS_PORT="${REDIS_PORT:-6379}"
    export REDIS_DB="${REDIS_DB:-0}"
    export REDIS_PASSWORD="${REDIS_PASSWORD:-}"
    export REDIS_MAX_CONNECTIONS="${REDIS_MAX_CONNECTIONS:-50}"
    
    # Concurrency configuration (Ollama-style)
    export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-auto}"
    export OLLAMA_MAX_QUEUE="${OLLAMA_MAX_QUEUE:-512}"
    export REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-300}"
}

# Function to run the uvicorn server
run_server() {
    # Set working directory and Python path
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

    # Activate virtual environment if enabled
    if [ "$USE_VENV" = "true" ] && [ -f "$VENV_ACTIVATE" ]; then
        echo "[VENV] Activating virtual environment: $VENV_ACTIVATE"
        # shellcheck source=/dev/null
        source "$VENV_ACTIVATE"
    fi

    # Build uvicorn command
    UVICORN_CMD="uvicorn $PROXY_MODULE"
    UVICORN_CMD="$UVICORN_CMD --host $HOST"
    UVICORN_CMD="$UVICORN_CMD --port $PORT"
    UVICORN_CMD="$UVICORN_CMD --log-level $LOG_LEVEL"
    UVICORN_CMD="$UVICORN_CMD --forwarded-allow-ips='*'"

    # Add reload flag for development
    if [ "$RELOAD" = "true" ]; then
        UVICORN_CMD="$UVICORN_CMD --reload"
    fi

    echo "[START] Running command: $UVICORN_CMD"
    
    # Export all variables and execute
    export_variables
    exec $UVICORN_CMD
}

# Functions for process management
start_proxy() {
  # Check if already running
  if [ -f "$PID_FILE" ]; then
    local old_pid
    old_pid=$(cat "$PID_FILE")
    if ps -p "$old_pid" > /dev/null 2>&1; then
      echo "✗ Proxy is already running (PID: $old_pid)"
      return 1
    fi
  fi

  echo "Starting Ollama Guard Proxy in background..."
  
  # Create log directory if it doesn't exist
  mkdir -p "$LOG_DIR"
  
  # Run the server in the background
  nohup bash -c "$(declare -f export_variables run_server); run_server" > "$LOG_FILE" 2>&1 &
  
  local pid=$!
  echo "$pid" > "$PID_FILE"
  sleep 2  # Give more time to detect startup errors
  
  # Verify process started
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "✓ Proxy started successfully (PID: $pid)"
    echo "  Log file: $LOG_FILE"
    echo "  Access:   http://$HOST:$PORT/health"
    echo "  To view logs, run: ./run_proxy.sh logs"
    return 0
  else
    echo "✗ Failed to start proxy. Check logs for details:"
    echo "  $LOG_FILE"
    echo "─────────────────────────────────────────────────────────────"
    tail -20 "$LOG_FILE" 2>/dev/null || echo "(No log file available)"
    echo "─────────────────────────────────────────────────────────────"
    return 1
  fi
}

stop_proxy() {
  if [ ! -f "$PID_FILE" ]; then
    echo "✗ Proxy is not running (no PID file)"
    return 1
  fi
  
  local pid
  pid=$(cat "$PID_FILE")
  
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
  
  local pid
  pid=$(cat "$PID_FILE")
  
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "✓ Proxy is running (PID: $pid)"
    echo "  Host: $HOST"
    echo "  Port: $PORT"
    echo "  Config: $CONFIG_FILE"
    echo "  Ollama URL: ${OLLAMA_URL:-http://127.0.0.1:11434}"
    echo "  Concurrency: ${OLLAMA_NUM_PARALLEL:-auto} parallel, ${OLLAMA_MAX_QUEUE:-512} queue"
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
  --port PORT              Server port (default: 9999)
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
  $0 run --port 8080 --debug

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
  
Concurrency Variables (Ollama-style):
  OLLAMA_NUM_PARALLEL        Max parallel requests per model
                             "auto" selects 4 if >=16GB free RAM else 1; or set explicit: 1, 2, 4, 8
                             (default: auto)
  OLLAMA_MAX_QUEUE           Max queued requests before rejection
                             (default: 512)
  REQUEST_TIMEOUT            Request timeout in seconds
                             (default: 300)

Log Files:
  All logs are written to: $LOG_DIR/proxy.log
  PID file: $PID_FILE

EOF
}

run_interactive() {
  echo "Starting Ollama Guard Proxy in foreground..."

  # --- Pre-run Checks ---
  cd "$PROJECT_ROOT"
  export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

  # 1. Check for Python
  PYTHON_CMD=$(command -v python3 || command -v python)
  if [ -z "$PYTHON_CMD" ]; then
    echo "✗ Error: Python not found. Please install Python 3.9+."
    exit 1
  fi

  # 2. Check and activate virtual environment
  VENV_ACTIVATED=false
  if [ "$USE_VENV" = "true" ]; then
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_ACTIVATE" ]; then
      echo "✗ Error: Python virtual environment not found or incomplete."
      echo "  Expected directory: $VENV_DIR"
      echo "  Expected script:    $VENV_ACTIVATE"
      echo "  To create it, run:"
      echo "    $PYTHON_CMD -m venv $VENV_DIR"
      echo "    source $VENV_DIR/bin/activate"
      echo "    pip install -r requirements.txt"
      exit 1
    fi
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
    VENV_ACTIVATED=true
    echo "✓ Virtual environment activated: $VENV_DIR"
  else
    echo "⚠ Venv disabled. Using system Python."
  fi

  # 3. Check for critical dependencies
  if [ -f "requirements.txt" ]; then
    # Use pip freeze and grep to check for installed packages efficiently
    INSTALLED_PACKAGES=$($PYTHON_CMD -m pip freeze)
    MISSING_PACKAGES=()
    for pkg in uvicorn fastapi pydantic requests llm-guard; do
      if ! echo "$INSTALLED_PACKAGES" | grep -q -i "^$pkg=="; then
        MISSING_PACKAGES+=("$pkg")
      fi
    done

    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
      echo "✗ Error: Missing required Python packages: ${MISSING_PACKAGES[*]}"
      echo "  To install them, run:"
      if [ "$VENV_ACTIVATED" = true ]; then
        echo "    pip install -r requirements.txt"
      else
        echo "    $PYTHON_CMD -m pip install -r requirements.txt"
      fi
      exit 1
    fi
    echo "✓ Dependencies checked."
  else
    echo "⚠ Warning: requirements.txt not found. Skipping dependency check."
  fi

  # 4. Check for config file
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠ Warning: Config file '$CONFIG_FILE' not found. Using default settings."
  else
    echo "✓ Config file found: $CONFIG_FILE"
  fi
  
  # --- Final Startup Display ---
  export_variables
  
  UVICORN_CMD_DISPLAY="uvicorn $PROXY_MODULE --host $HOST --port $PORT --log-level $LOG_LEVEL"
  [ "$RELOAD" = "true" ] && UVICORN_CMD_DISPLAY="$UVICORN_CMD_DISPLAY --reload"

  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║         Ollama Guard Proxy - Uvicorn Server                    ║"
  echo "╠════════════════════════════════════════════════════════════════╣"
  echo "║ Host:       $HOST"
  echo "║ Port:       $PORT"
  echo "║ Log Level:  $LOG_LEVEL"
  echo "║ Reload:     $RELOAD"
  echo "║ Ollama URL: $OLLAMA_URL"
  echo "║"
  echo "║ Command: $UVICORN_CMD_DISPLAY"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
  echo "Server starting... (Press Ctrl+C to stop)"
  echo ""

  # Run Uvicorn with configuration
  run_server
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
