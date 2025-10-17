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
#   python -m venv venv                                    # Create venv
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
VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/venv}"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
USE_VENV="${USE_VENV:-true}"

# Default configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-4}"                    # Number of worker processes
WORKERS="${1:-$WORKERS}"
CONCURRENCY="${CONCURRENCY:-128}"          # Concurrent connections per worker
LOG_LEVEL="${LOG_LEVEL:-info}"             # info, debug, warning, error
RELOAD="${RELOAD:-false}"
CONFIG_FILE="${CONFIG_FILE:-config.yaml}"
PROXY_MODULE="ollama_guard_proxy:app"

# Default configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-4}"                    # Number of worker processes
CONCURRENCY="${CONCURRENCY:-128}"          # Concurrent connections per worker
LOG_LEVEL="${LOG_LEVEL:-info}"             # info, debug, warning, error
RELOAD="${RELOAD:-false}"
CONFIG_FILE="${CONFIG_FILE:-config.yaml}"
PROXY_MODULE="ollama_guard_proxy:app"

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
  
  # Check if virtual environment exists
  if [ "$USE_VENV" = "true" ] && [ -f "$VENV_ACTIVATE" ]; then
    echo "✓ Using Python virtual environment: $VENV_DIR"
    VENV_CMD="source $VENV_ACTIVATE && "
  else
    echo "⚠ Virtual environment not found at $VENV_DIR"
    echo "  Tip: Create venv with: python -m venv $VENV_DIR"
    echo "  Tip: Or set VENV_DIR to another location"
    VENV_CMD=""
  fi
  
  # Start proxy with nohup, logging to current folder
  nohup bash -c "
    $VENV_CMD
    export OLLAMA_URL=\"\${OLLAMA_URL:-http://127.0.0.1:11434}\"
    export PROXY_PORT=\"$PORT\"
    export CONFIG_FILE=\"$CONFIG_FILE\"
    export NGINX_WHITELIST=\"\${NGINX_WHITELIST:-}\"
    export ENABLE_INPUT_GUARD=\"\${ENABLE_INPUT_GUARD:-}\"
    export ENABLE_OUTPUT_GUARD=\"\${ENABLE_OUTPUT_GUARD:-}\"
    export ENABLE_IP_FILTER=\"\${ENABLE_IP_FILTER:-}\"
    export IP_WHITELIST=\"\${IP_WHITELIST:-}\"
    export IP_BLACKLIST=\"\${IP_BLACKLIST:-}\"
    
    uvicorn $PROXY_MODULE \\
      --host $HOST \\
      --port $PORT \\
      --workers $WORKERS \\
      --log-level $LOG_LEVEL
  " > "$LOG_FILE" 2>&1 &
  
  local pid=$!
  echo "$pid" > "$PID_FILE"
  sleep 1
  
  # Verify process started
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "✓ Proxy started successfully (PID: $pid)"
    echo "✓ Log file: $LOG_FILE"
    echo "✓ Access: http://$HOST:$PORT/health"
    return 0
  else
    echo "✗ Failed to start proxy"
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
  OLLAMA_URL               Ollama backend URL (e.g., http://127.0.0.1:11434)
  PROXY_PORT               Proxy port
  NGINX_WHITELIST          Comma-separated IPs/CIDR for Nginx-only access
                           (e.g., "127.0.0.1,192.168.1.0/24")
                           Empty = allow all, for local dev only
  ENABLE_INPUT_GUARD       true/false
  ENABLE_OUTPUT_GUARD      true/false
  ENABLE_IP_FILTER         true/false
  IP_WHITELIST             Comma-separated IPs
  IP_BLACKLIST             Comma-separated IPs
  CONFIG_FILE              Configuration file path
  VENV_DIR                 Python virtual environment directory
                           (default: ./venv)
  USE_VENV                 true/false - Enable/disable venv activation
                           (default: true)

Log Files:
  All logs are written to: $LOG_DIR/proxy.log
  PID file: $PID_FILE

EOF
}

run_interactive() {

  # Check if Python is available
  if ! command -v python &> /dev/null; then
    echo "✗ Error: Python not found. Please install Python 3.9+"
    exit 1
  fi

  # Check and activate virtual environment
  if [ "$USE_VENV" = "true" ]; then
    if [ -f "$VENV_ACTIVATE" ]; then
      echo "✓ Activating Python virtual environment: $VENV_DIR"
      source "$VENV_ACTIVATE"
    else
      echo "⚠ Virtual environment not found at $VENV_DIR"
      echo "  Tip: Create venv with: python -m venv $VENV_DIR"
      echo "  Tip: Or set VENV_DIR to another location"
      echo "  Continuing with system Python..."
    fi
  fi

  # Check if uvicorn is installed
  if ! python -c "import uvicorn" 2>/dev/null; then
    echo "✗ Error: uvicorn not installed. Install with: pip install uvicorn"
    exit 1
  fi

  # Check if config file exists
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠ Warning: Config file '$CONFIG_FILE' not found. Using defaults."
  fi

  # Export environment variables
  export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
  export PROXY_PORT="$PORT"
  export CONFIG_FILE="$CONFIG_FILE"
  export NGINX_WHITELIST="${NGINX_WHITELIST:-}"
  export ENABLE_INPUT_GUARD="${ENABLE_INPUT_GUARD:-}"
  export ENABLE_OUTPUT_GUARD="${ENABLE_OUTPUT_GUARD:-}"
  export ENABLE_IP_FILTER="${ENABLE_IP_FILTER:-}"
  export IP_WHITELIST="${IP_WHITELIST:-}"
  export IP_BLACKLIST="${IP_BLACKLIST:-}"

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
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║         Ollama Guard Proxy - Uvicorn Server                    ║"
  echo "╠════════════════════════════════════════════════════════════════╣"
  echo "║ Server Configuration:"
  echo "║   Host:       $HOST"
  echo "║   Port:       $PORT"
  echo "║   Workers:    $WORKERS"
  echo "║ Python Environment:"
  if [ "$USE_VENV" = "true" ]; then
    if [ -f "$VENV_ACTIVATE" ]; then
      echo "║   Venv:       $VENV_DIR (ACTIVE)"
    else
      echo "║   Venv:       $VENV_DIR (NOT FOUND - using system Python)"
    fi
  else
    echo "║   Venv:       DISABLED (using system Python)"
  fi
  echo "║ Runtime Settings:"
  echo "║   Concurrency:     $CONCURRENCY per worker"
  echo "║   Log Level:       $LOG_LEVEL"
  echo "║   Reload:         $RELOAD"
  echo "║   Config File:    $CONFIG_FILE"
  echo "╠════════════════════════════════════════════════════════════════╣"
  echo "║ Environment Variables:"
  echo "║   OLLAMA_URL:              $OLLAMA_URL"
  echo "║   NGINX_WHITELIST:         ${NGINX_WHITELIST:-empty (unrestricted)}"
  echo "║   ENABLE_INPUT_GUARD:      ${ENABLE_INPUT_GUARD:-not set}"
  echo "║   ENABLE_OUTPUT_GUARD:     ${ENABLE_OUTPUT_GUARD:-not set}"
  echo "║   ENABLE_IP_FILTER:        ${ENABLE_IP_FILTER:-not set}"
  echo "║   IP_WHITELIST:            ${IP_WHITELIST:-not set}"
  echo "║   IP_BLACKLIST:            ${IP_BLACKLIST:-not set}"
  echo "╠════════════════════════════════════════════════════════════════╣"
  echo "║ Testing proxy:"
  echo "║   curl http://$HOST:$PORT/health"
  echo "║ Generating:"
  echo "║   curl -X POST http://$HOST:$PORT/v1/generate \\"
  echo "║     -d '{\"model\":\"mistral\",\"prompt\":\"test\"}'"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""

  # Run Uvicorn with configuration
  echo "Starting server: $UVICORN_CMD"
  echo ""
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
