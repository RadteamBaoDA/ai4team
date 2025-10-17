#!/bin/bash

################################################################################
# LiteLLM Proxy Startup Script with nohup
# Starts the LiteLLM proxy with custom guardrails in background
# Logs are saved to logs/litellm_proxy.log
################################################################################

set -e  # Exit on error

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
CONFIG_FILE="${CONFIG_FILE:-./litellm_config.yaml}"
LOG_DIR="${LOG_DIR:-./logs}"
LOG_FILE="${LOG_DIR}/litellm_proxy.log"
PID_FILE="${LOG_DIR}/litellm_proxy.pid"

# Proxy settings (from environment or defaults)
HOST="${LITELLM_HOST:-0.0.0.0}"
PORT="${LITELLM_PORT:-8000}"
WORKERS="${LITELLM_WORKERS:-4}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# Functions
################################################################################

print_header() {
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if process is running
check_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(<"$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Process is running
        else
            return 1  # PID file exists but process not running
        fi
    fi
    return 1  # No PID file
}

# Get process status
get_status() {
    if check_running; then
        local pid=$(<"$PID_FILE")
        print_success "LiteLLM proxy is running (PID: $pid)"
        return 0
    else
        print_warning "LiteLLM proxy is not running"
        return 1
    fi
}

# Install dependencies
install_deps() {
    print_header "Installing Dependencies"
    
    if [ -f "requirements.txt" ]; then
        print_info "Installing from requirements.txt..."
        python3 -m pip install -r requirements.txt
        print_success "Dependencies installed from requirements.txt"
    else
        print_info "Running dependency installer..."
        if [ -f "install_dependencies.py" ]; then
            python3 install_dependencies.py
            print_success "Dependencies installed"
        else
            print_error "install_dependencies.py not found"
            return 1
        fi
    fi
}

# Validate configuration
validate_config() {
    print_header "Validating Configuration"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        return 1
    fi
    
    print_info "Configuration file: $CONFIG_FILE"
    print_success "Configuration file validated"
    
    # Try to validate with Python
    if python3 run_litellm_proxy.py --validate-only >/dev/null 2>&1; then
        print_success "Guardrail configuration validated"
    else
        print_warning "Could not validate guardrail (may not be installed yet)"
    fi
    
    return 0
}

# Stop the proxy
stop_proxy() {
    print_header "Stopping LiteLLM Proxy"
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(<"$PID_FILE")
        
        if kill -0 "$pid" 2>/dev/null; then
            print_info "Stopping process $pid..."
            
            # Try graceful shutdown first
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "Process still running, forcing shutdown..."
                kill -9 "$pid" 2>/dev/null || true
                sleep 1
            fi
            
            print_success "LiteLLM proxy stopped"
        fi
        
        rm -f "$PID_FILE"
    else
        print_warning "No PID file found"
    fi
}

# Start the proxy
start_proxy() {
    print_header "Starting LiteLLM Proxy with nohup"
    
    # Check if already running
    if check_running; then
        local pid=$(<"$PID_FILE")
        print_warning "LiteLLM proxy already running (PID: $pid)"
        return 1
    fi
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Display startup info
    print_info "Configuration file: $CONFIG_FILE"
    print_info "Bind address: $HOST:$PORT"
    print_info "Workers: $WORKERS"
    print_info "Log level: $LOG_LEVEL"
    print_info "Log file: $LOG_FILE"
    print_info "PID file: $PID_FILE"
    
    # Start proxy with nohup
    print_info "Starting LiteLLM proxy..."
    
    nohup python3 run_litellm_proxy.py \
        --config "$CONFIG_FILE" \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL" \
        > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment for startup
    sleep 2
    
    # Check if process is still running
    if kill -0 "$pid" 2>/dev/null; then
        print_success "LiteLLM proxy started (PID: $pid)"
        
        # Print useful info
        echo ""
        print_header "Proxy Information"
        print_info "API Base: http://$HOST:$PORT/v1"
        print_info "Chat Completions: http://$HOST:$PORT/v1/chat/completions"
        print_info "Models: http://$HOST:$PORT/v1/models"
        print_info "Health Check: http://$HOST:$PORT/health"
        print_info "Logs: tail -f $LOG_FILE"
        print_info "Status: ./start_proxy.sh status"
        print_info "Stop: ./start_proxy.sh stop"
        
        return 0
    else
        print_error "Failed to start LiteLLM proxy"
        print_error "Check logs: cat $LOG_FILE"
        return 1
    fi
}

# Restart the proxy
restart_proxy() {
    print_header "Restarting LiteLLM Proxy"
    
    stop_proxy
    sleep 2
    start_proxy
}

# Tail logs
tail_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_error "Log file not found: $LOG_FILE"
        return 1
    fi
    
    print_header "LiteLLM Proxy Logs (Ctrl+C to exit)"
    tail -f "$LOG_FILE"
}

# Show help
show_help() {
    cat << EOF
${BLUE}LiteLLM Proxy Startup Script${NC}

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start       Start the proxy with nohup (default)
    stop        Stop the running proxy
    restart     Restart the proxy
    status      Show proxy status
    logs        Tail proxy logs (Ctrl+C to exit)
    install     Install dependencies
    validate    Validate configuration
    help        Show this help message

Options (for start command):
    --config FILE       Configuration file (default: ./litellm_config.yaml)
    --host HOST         Bind host (default: 0.0.0.0)
    --port PORT         Bind port (default: 8000)
    --workers N         Number of workers (default: 4)
    --log-level LEVEL   Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)

Environment Variables:
    CONFIG_FILE         Configuration file path
    LOG_DIR             Log directory (default: ./logs)
    LITELLM_HOST        Host to bind (default: 0.0.0.0)
    LITELLM_PORT        Port to bind (default: 8000)
    LITELLM_WORKERS     Number of workers (default: 4)
    LOG_LEVEL           Log level (default: INFO)

Examples:
    # Start with default settings
    $0 start

    # Start on different port
    LITELLM_PORT=9000 $0 start

    # Start with custom config
    $0 start --config ./my_config.yaml

    # Check status
    $0 status

    # View logs
    $0 logs

    # Restart proxy
    $0 restart

    # Stop proxy
    $0 stop

    # Install dependencies
    $0 install

    # Validate configuration
    $0 validate
EOF
}

################################################################################
# Main Script
################################################################################

main() {
    local command="${1:-start}"
    
    case "$command" in
        start)
            validate_config || exit 1
            start_proxy
            ;;
        
        stop)
            stop_proxy
            ;;
        
        restart)
            restart_proxy
            ;;
        
        status)
            get_status
            ;;
        
        logs)
            tail_logs
            ;;
        
        install)
            install_deps
            ;;
        
        validate)
            validate_config
            ;;
        
        help|--help|-h)
            show_help
            ;;
        
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
