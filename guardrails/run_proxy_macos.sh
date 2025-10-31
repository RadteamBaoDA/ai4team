#!/bin/bash
# Optimized Ollama Guard Proxy Runner for macOS with Apple Silicon (M1/M2/M3)
# 
# Features:
# - Automatic MPS (Metal Performance Shaders) GPU detection
# - Apple Silicon performance optimizations
# - Memory and CPU monitoring
# - Uvicorn multi-worker support optimized for ARM64
#
# Usage:
#   ./run_proxy_macos.sh start      # Start proxy as background process
#   ./run_proxy_macos.sh stop       # Stop running proxy
#   ./run_proxy_macos.sh restart    # Restart proxy
#   ./run_proxy_macos.sh status     # Check proxy status
#   ./run_proxy_macos.sh logs       # Show proxy logs
#   ./run_proxy_macos.sh run        # Run proxy in foreground

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$LOG_DIR/proxy.pid"
LOG_FILE="$LOG_DIR/proxy_macos.log"
CACHE_DIR="$SCRIPT_DIR/cache"
MODELS_DIR="$SCRIPT_DIR/models"

# Virtual environment
VENV_DIR="${VENV_DIR:-./venv}"
USE_VENV="${USE_VENV:-true}"

# Proxy configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
CONFIG_FILE="${CONFIG_FILE:-config.yaml}"
PROXY_MODULE="ollama_guard_proxy:app"

# Detect CPU cores for optimal worker count
if command -v sysctl &> /dev/null; then
    CPU_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "4")
else
    CPU_CORES=$(nproc 2>/dev/null || echo "4")
fi

# Apple Silicon optimizations
LOG_LEVEL="${LOG_LEVEL:-info}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_header() {
    echo -e "${BLUE}$1${NC}"
}

# Detect macOS and Apple Silicon
detect_platform() {
    log_header "═══════════════════════════════════════════════════════════════"
    log_header "Platform Detection - macOS Apple Silicon Optimization"
    log_header "═══════════════════════════════════════════════════════════════"
    
    # Check if running on macOS
    if [[ "$(uname)" != "Darwin" ]]; then
        log_error "This script is optimized for macOS. Detected: $(uname)"
        log_warn "Use run_proxy.sh for non-macOS systems"
        return 1
    fi
    
    log_info "Operating System: macOS $(sw_vers -productVersion)"
    
    # Check for Apple Silicon
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        log_info "Architecture: ARM64 (Apple Silicon detected)"
        APPLE_SILICON=true
    else
        log_warn "Architecture: $ARCH (Not Apple Silicon, optimizations may be limited)"
        APPLE_SILICON=false
    fi
    
    # Display hardware info
    if command -v sysctl &> /dev/null; then
        CHIP_NAME=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
        MEMORY_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo "0") / 1024 / 1024 / 1024 ))
        
        log_info "Chip: $CHIP_NAME"
        log_info "CPU Cores: $CPU_CORES"
        log_info "Memory: ${MEMORY_GB}GB"
    fi
    
    echo ""
    return 0
}

# Check for MPS (Metal Performance Shaders) support
check_mps_support() {
    log_header "Checking MPS (Metal Performance Shaders) GPU Support..."
    
    if [[ "$APPLE_SILICON" != "true" ]]; then
        log_warn "MPS requires Apple Silicon (M1/M2/M3)"
        export LLM_GUARD_DEVICE="cpu"
        return 1
    fi
    
    # Check if Python and PyTorch are available
    if [[ "$USE_VENV" == "true" ]] && [[ -f "$VENV_DIR/bin/python" ]]; then
        PYTHON_CMD="$VENV_DIR/bin/python"
    else
        PYTHON_CMD="python3"
    fi
    
    # Test MPS availability with Python
    if $PYTHON_CMD -c "import torch; assert torch.backends.mps.is_available(); print('MPS available')" 2>/dev/null; then
        log_info "MPS GPU is available and functional"
        export LLM_GUARD_DEVICE="mps"
        export PYTORCH_ENABLE_MPS_FALLBACK="1"
        export MPS_ENABLE_FP16="true"
        return 0
    else
        log_warn "MPS not available, falling back to CPU"
        export LLM_GUARD_DEVICE="cpu"
        return 1
    fi
    
    echo ""
}

# Check Redis connection
check_redis_connection() {
    if [[ "$REDIS_ENABLED" != "true" ]]; then
        log_warn "Redis caching disabled"
        return 0
    fi
    
    log_header "Checking Redis Connection..."
    
    # Check if redis-cli is available
    if ! command -v redis-cli &> /dev/null; then
        log_warn "redis-cli not installed, skipping connection check"
        log_info "Redis connection will be tested by the application"
        return 0
    fi
    
    # Test Redis connection
    local redis_cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    if [[ -n "$REDIS_PASSWORD" ]]; then
        redis_cmd="$redis_cmd -a $REDIS_PASSWORD --no-auth-warning"
    fi
    
    if $redis_cmd ping &>/dev/null; then
        log_info "Redis connection OK ($REDIS_HOST:$REDIS_PORT)"
        
        # Get Redis info
        local redis_version=$($redis_cmd INFO server 2>/dev/null | grep redis_version | cut -d':' -f2 | tr -d '\r')
        local redis_memory=$($redis_cmd INFO memory 2>/dev/null | grep used_memory_human | cut -d':' -f2 | tr -d '\r')
        
        if [[ -n "$redis_version" ]]; then
            log_info "Redis version: $redis_version"
        fi
        if [[ -n "$redis_memory" ]]; then
            log_info "Redis memory: $redis_memory"
        fi
    else
        log_warn "Cannot connect to Redis ($REDIS_HOST:$REDIS_PORT)"
        log_warn "Proxy will fall back to in-memory cache"
    fi
    
    echo ""
}

# Setup environment with Apple Silicon optimizations
setup_environment() {
    log_header "Setting up environment for Apple Silicon..."
    
    # Create necessary directories
    mkdir -p "$LOG_DIR" "$CACHE_DIR" "$MODELS_DIR"
    
    # Apple Silicon specific environment variables
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    
    # Threading optimizations for ARM64
    export OMP_NUM_THREADS=$CPU_CORES
    export MKL_NUM_THREADS=$CPU_CORES
    export OPENBLAS_NUM_THREADS=$CPU_CORES
    export VECLIB_MAXIMUM_THREADS=$CPU_CORES
    
    # Memory optimizations
    export MALLOC_ARENA_MAX=2
    export MALLOC_MMAP_THRESHOLD_=131072
    export MALLOC_TRIM_THRESHOLD_=131072
    
    # PyTorch optimizations
    export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
    
    # LLM Guard configuration
    export LLM_GUARD_USE_LOCAL_MODELS="${LLM_GUARD_USE_LOCAL_MODELS:-false}"
    export LLM_GUARD_MODELS_PATH="$MODELS_DIR"
    
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
    
    # Proxy configuration
    export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
    export PROXY_PORT="$PORT"
    export CONFIG_FILE="$CONFIG_FILE"
    
    log_info "Environment configured for Apple Silicon"
    log_info "Device: ${LLM_GUARD_DEVICE}"
    log_info "Threads per worker: $CPU_CORES"
    log_info "Concurrency: Parallel=${OLLAMA_NUM_PARALLEL}, Queue=${OLLAMA_MAX_QUEUE}"
    
    echo ""
}

# Activate virtual environment
activate_venv() {
    if [[ "$USE_VENV" != "true" ]]; then
        log_warn "Virtual environment disabled"
        return 0
    fi
    
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        log_error "Virtual environment not found: $VENV_DIR"
        log_info "Create with: python3 -m venv $VENV_DIR"
        return 1
    fi
    
    source "$VENV_DIR/bin/activate"
    log_info "Virtual environment activated: $VENV_DIR"
    
    # Verify uvicorn is installed
    if ! command -v uvicorn &> /dev/null; then
        log_error "uvicorn not found. Install with: pip install -r requirements.txt"
        return 1
    fi
    
    log_info "Python: $(python --version 2>&1)"
    log_info "Uvicorn: $(uvicorn --version 2>&1 | head -1)"
    
    echo ""
    return 0
}

# Start proxy
start_proxy() {
    log_header "═══════════════════════════════════════════════════════════════"
    log_header "Starting Ollama Guard Proxy for macOS"
    log_header "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Check if already running
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_error "Proxy is already running (PID: $pid)"
            return 1
        fi
    fi
    
    # Platform detection and setup
    detect_platform || return 1
    check_mps_support
    check_redis_connection
    setup_environment
    activate_venv || return 1
    
    log_header "Starting Uvicorn server..."
    
    # Start proxy with nohup
    nohup uvicorn $PROXY_MODULE \
        --host $HOST \
        --port $PORT \
        --log-level $LOG_LEVEL \
        --forwarded-allow-ips="*" \
        --timeout-keep-alive 5 \
        > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    sleep 3
    
    # Verify process started
    if ps -p "$pid" > /dev/null 2>&1; then
        log_info "Proxy started successfully (PID: $pid)"
        log_info "Log file: $LOG_FILE"
        log_info "Listening on: http://$HOST:$PORT"
        log_info "Health check: http://localhost:$PORT/health"
        echo ""
        log_info "View logs: tail -f $LOG_FILE"
        return 0
    else
        log_error "Failed to start proxy"
        echo ""
        log_header "Error log (last 20 lines):"
        tail -20 "$LOG_FILE" 2>/dev/null || log_error "No log file available"
        return 1
    fi
}

# Stop proxy
stop_proxy() {
    if [[ ! -f "$PID_FILE" ]]; then
        log_error "Proxy is not running (no PID file)"
        return 1
    fi
    
    local pid=$(cat "$PID_FILE")
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        log_error "Proxy is not running (PID $pid not found)"
        rm -f "$PID_FILE"
        return 1
    fi
    
    log_info "Stopping proxy (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    
    # Wait for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
        sleep 0.5
        count=$((count + 1))
    done
    
    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        log_warn "Force killing proxy..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    rm -f "$PID_FILE"
    log_info "Proxy stopped"
    return 0
}

# Status check
status_proxy() {
    if [[ ! -f "$PID_FILE" ]]; then
        log_error "Proxy is not running (no PID file)"
        return 1
    fi
    
    local pid=$(cat "$PID_FILE")
    
    if ps -p "$pid" > /dev/null 2>&1; then
        log_info "Proxy is running (PID: $pid)"
        echo ""
        echo "Configuration:"
        echo "  Host: $HOST"
        echo "  Port: $PORT"
        echo "  Device: ${LLM_GUARD_DEVICE:-auto}"
        echo "  Cache: ${CACHE_BACKEND:-auto} (TTL: ${CACHE_TTL:-3600}s)"
        echo "  Concurrency: ${OLLAMA_NUM_PARALLEL:-auto} parallel, ${OLLAMA_MAX_QUEUE:-512} queue"
        echo "  Log: $LOG_FILE"
        echo ""
        
        # Check Redis status if enabled
        if [[ "$REDIS_ENABLED" == "true" ]] && command -v redis-cli &> /dev/null; then
            local redis_cmd="redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379}"
            if [[ -n "$REDIS_PASSWORD" ]]; then
                redis_cmd="$redis_cmd -a $REDIS_PASSWORD --no-auth-warning"
            fi
            
            if $redis_cmd ping &>/dev/null; then
                echo "Redis:"
                local redis_keys=$($redis_cmd DBSIZE 2>/dev/null | grep -o '[0-9]*' || echo "0")
                local redis_memory=$($redis_cmd INFO memory 2>/dev/null | grep used_memory_human | cut -d':' -f2 | tr -d '\r' || echo "N/A")
                echo "  Status: Connected ($REDIS_HOST:$REDIS_PORT)"
                echo "  Keys: $redis_keys"
                echo "  Memory: $redis_memory"
                echo ""
            else
                echo "Redis:"
                echo "  Status: Disconnected (using in-memory cache)"
                echo ""
            fi
        fi
        
        echo "Recent logs:"
        tail -5 "$LOG_FILE" 2>/dev/null || log_warn "No logs available"
        return 0
    else
        log_error "Proxy is not running (PID $pid not found)"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Show logs
show_logs() {
    if [[ ! -f "$LOG_FILE" ]]; then
        log_error "No log file found: $LOG_FILE"
        return 1
    fi
    
    log_info "Following logs from: $LOG_FILE (Press Ctrl+C to stop)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -f "$LOG_FILE"
}

# Run in foreground
run_foreground() {
    detect_platform || exit 1
    check_mps_support
    check_redis_connection
    setup_environment
    activate_venv || exit 1
    
    log_header "═══════════════════════════════════════════════════════════════"
    log_header "Ollama Guard Proxy - macOS Apple Silicon"
    log_header "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Configuration:"
    echo "  Host: $HOST"
    echo "  Port: $PORT"
    echo "  Device: ${LLM_GUARD_DEVICE}"
    echo "  Log Level: $LOG_LEVEL"
    echo "  Concurrency: ${OLLAMA_NUM_PARALLEL:-auto} parallel, ${OLLAMA_MAX_QUEUE:-512} queue"
    echo ""
    log_info "Starting Uvicorn server... (Press Ctrl+C to stop)"
    echo ""
    
    exec uvicorn $PROXY_MODULE \
        --host $HOST \
        --port $PORT \
        --log-level $LOG_LEVEL \
        --forwarded-allow-ips="*" \
        --timeout-keep-alive 5 \
        --access-log \
        --use-colors
}

# Main command dispatch
COMMAND="${1:-help}"

case "$COMMAND" in
    start)
        start_proxy
        ;;
    stop)
        stop_proxy
        ;;
    restart)
        log_info "Restarting proxy..."
        stop_proxy || true
        sleep 2
        start_proxy
        ;;
    status)
        status_proxy
        ;;
    logs)
        show_logs
        ;;
    run)
        run_foreground
        ;;
    help|--help|-h)
        echo "Ollama Guard Proxy - macOS Apple Silicon Runner"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  start    - Start proxy as background process"
        echo "  stop     - Stop running proxy"
        echo "  restart  - Restart proxy"
        echo "  status   - Check proxy status"
        echo "  logs     - View live logs"
        echo "  run      - Run in foreground (interactive)"
        echo "  help     - Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  HOST                        - Server host (default: 0.0.0.0)"
        echo "  PORT                        - Server port (default: 8080)"
        echo "  WORKERS                     - Number of workers (default: CPU cores)"
        echo "  OLLAMA_URL                  - Ollama backend URL"
        echo "  LLM_GUARD_DEVICE            - Device: mps, cuda, cpu (default: auto)"
        echo "  LLM_GUARD_USE_LOCAL_MODELS  - Use local models (default: false)"
        echo "  USE_VENV                    - Use virtual environment (default: true)"
        echo "  VENV_DIR                    - Venv directory (default: ./venv)"
        echo ""
        echo "Cache/Redis Variables:"
        echo "  CACHE_ENABLED               - Enable caching (default: true)"
        echo "  CACHE_BACKEND               - Backend: auto, redis, memory (default: auto)"
        echo "  CACHE_TTL                   - Cache TTL in seconds (default: 3600)"
        echo "  REDIS_ENABLED               - Enable Redis (default: true)"
        echo "  REDIS_HOST                  - Redis host (default: localhost)"
        echo "  REDIS_PORT                  - Redis port (default: 6379)"
        echo "  REDIS_PASSWORD              - Redis password (default: empty)"
        echo "  REDIS_DB                    - Redis database number (default: 0)"
        echo "  REDIS_MAX_CONNECTIONS       - Max connections (default: 50)"
        echo ""
        echo "Concurrency Variables (Ollama-style):"
        echo "  OLLAMA_NUM_PARALLEL         - Max parallel requests per model"
    echo "                                'auto' selects 4 if >=16GB free RAM else 1; or set 1,2,4,8"
        echo "                                (default: auto)"
        echo "  OLLAMA_MAX_QUEUE            - Max queued requests before rejection"
        echo "                                (default: 512)"
        echo "  REQUEST_TIMEOUT             - Request timeout in seconds"
        echo "                                (default: 300)"
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
