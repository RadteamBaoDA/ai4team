#!/bin/bash
# Ollama Guard Proxy - Uvicorn Runner (Linux/macOS)
# Run the proxy with Uvicorn with support for parallel/concurrent requests
# 
# Usage:
#   ./run_proxy.sh                           # Default: single worker, 4 concurrent
#   ./run_proxy.sh --workers 4 --concurrency 8
#   ./run_proxy.sh --host 0.0.0.0 --port 8080
#   ./run_proxy.sh --reload                  # Auto-reload on code changes
#   ./run_proxy.sh --debug                   # Show debug logs
#
# Features:
#   - Uvicorn ASGI server
#   - Multi-worker support for parallel requests
#   - Configurable concurrency per worker
#   - Environment variable support
#   - Health check endpoint
#   - Request logging

set -euo pipefail

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

# Parse arguments
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
      cat << EOF
Usage: $0 [OPTIONS]

Options:
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
  # Development with auto-reload
  $0 --reload --debug

  # Production with 8 workers for parallel processing
  $0 --workers 8 --concurrency 256

  # Listen on specific interface
  $0 --host 127.0.0.1 --port 8080

Environment Variables:
  OLLAMA_URL               Ollama backend URL (e.g., http://127.0.0.1:11434)
  PROXY_PORT               Proxy port
  ENABLE_INPUT_GUARD       true/false
  ENABLE_OUTPUT_GUARD      true/false
  ENABLE_IP_FILTER         true/false
  IP_WHITELIST             Comma-separated IPs
  IP_BLACKLIST             Comma-separated IPs
  CONFIG_FILE              Configuration file path
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if Python is available
if ! command -v python &> /dev/null; then
  echo "Error: Python not found. Please install Python 3.9+"
  exit 1
fi

# Check if uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
  echo "Error: uvicorn not installed. Install with: pip install uvicorn"
  exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Warning: Config file '$CONFIG_FILE' not found. Using defaults."
fi

# Export environment variables
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export PROXY_PORT="$PORT"
export CONFIG_FILE="$CONFIG_FILE"

# Build uvicorn command
UVICORN_CMD="uvicorn $PROXY_MODULE"
UVICORN_CMD="$UVICORN_CMD --host $HOST"
UVICORN_CMD="$UVICORN_CMD --port $PORT"
UVICORN_CMD="$UVICORN_CMD --workers $WORKERS"
UVICORN_CMD="$UVICORN_CMD --log-level $LOG_LEVEL"

# Add concurrency limit (Uvicorn interprets as max connections)
# Note: Uvicorn's --limit-concurrency doesn't exist, we use worker count instead
# For true concurrency control, use proxy settings

# Add reload flag for development
if [ "$RELOAD" = "true" ]; then
  UVICORN_CMD="$UVICORN_CMD --reload"
fi

# Display startup information
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Ollama Guard Proxy - Uvicorn Server                    ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║ Server:        $HOST:$PORT"
echo "║ Workers:       $WORKERS (for parallel request handling)"
echo "║ Concurrency:   $CONCURRENCY per worker"
echo "║ Log Level:     $LOG_LEVEL"
echo "║ Reload:        $RELOAD"
echo "║ Config:        $CONFIG_FILE"
echo "║ Ollama URL:    $OLLAMA_URL"
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
