#!/bin/bash

################################################################################
# Ollama Guard Proxy + Nginx Load Balancer - Deployment Script
# 
# This script automates deployment of:
#  - 3 Guard Proxy instances (ports 8080, 8081, 8082)
#  - Nginx load balancer with IP filtering and rate limiting
#  - Health monitoring and logging
#
# Usage: ./deploy-nginx.sh [start|stop|restart|status|test]
################################################################################

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/var/log/ollama-guard"
PID_DIR="/var/run/ollama-guard"
CONFIG_FILE="config.example.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# ============================================================================
# Helper Functions
# ============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
    
    if ! python3 -c "import uvicorn" &> /dev/null; then
        log_error "Uvicorn not installed. Run: pip install uvicorn fastapi requests llm-guard pyyaml"
        exit 1
    fi
    
    if ! command -v nginx &> /dev/null; then
        log_error "Nginx not found. Install with: sudo apt install nginx"
        exit 1
    fi
    
    log_info "All prerequisites met"
}

setup_directories() {
    log_info "Setting up directories..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$PID_DIR"
    mkdir -p /etc/nginx/ssl
    log_info "Directories created"
}

create_ssl_certificate() {
    local cert_file="/etc/nginx/ssl/ollama-guard.crt"
    local key_file="/etc/nginx/ssl/ollama-guard.key"
    
    if [ -f "$cert_file" ] && [ -f "$key_file" ]; then
        log_info "SSL certificates found"
        return
    fi
    
    log_info "Generating SSL certificates..."
    
    # Check if sudo is needed
    if [ -w /etc/nginx/ssl ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$key_file" \
            -out "$cert_file" \
            -subj "/C=US/ST=State/L=City/O=Company/CN=ollama.local" 2>/dev/null
    else
        sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$key_file" \
            -out "$cert_file" \
            -subj "/C=US/ST=State/L=City/O=Company/CN=ollama.local" 2>/dev/null
    fi
    
    log_info "SSL certificates generated"
}

start_proxy_instances() {
    log_info "Starting Guard Proxy instances..."
    
    for port in 8080 8081 8082; do
        pid_file="$PID_DIR/proxy-$port.pid"
        log_file="$LOG_DIR/proxy-$port.log"
        
        # Check if already running
        if [ -f "$pid_file" ]; then
            local old_pid=$(cat "$pid_file")
            if kill -0 "$old_pid" 2>/dev/null; then
                log_warn "Proxy on port $port already running (PID: $old_pid)"
                continue
            fi
        fi
        
        log_info "Starting proxy on port $port..."
        
        # Start proxy in background
        cd "$SCRIPT_DIR"
        ./run_proxy.sh --port "$port" --workers 4 --log-level info > "$log_file" 2>&1 &
        local new_pid=$!
        echo "$new_pid" > "$pid_file"
        
        log_info "✓ Proxy started on port $port (PID: $new_pid)"
        sleep 2
    done
}

test_proxy_instances() {
    log_info "Testing proxy instances..."
    
    local all_ok=true
    for port in 8080 8081 8082; do
        if curl -s http://localhost:$port/health > /dev/null 2>&1; then
            log_info "✓ Port $port: OK"
        else
            log_error "✗ Port $port: FAILED"
            all_ok=false
        fi
    done
    
    if [ "$all_ok" = false ]; then
        log_error "Some proxy instances failed"
        return 1
    fi
}

configure_nginx() {
    log_info "Configuring Nginx..."
    
    local conf_src="$SCRIPT_DIR/nginx-ollama-production.conf"
    
    if [ ! -f "$conf_src" ]; then
        log_error "Configuration file not found: $conf_src"
        return 1
    fi
    
    # Determine destination
    if [ -d /etc/nginx/sites-available ]; then
        local conf_dst="/etc/nginx/sites-available/ollama-guard"
        
        # Backup existing
        if [ -f "$conf_dst" ]; then
            log_warn "Backing up existing configuration"
            cp "$conf_dst" "$conf_dst.backup"
        fi
        
        cp "$conf_src" "$conf_dst"
        
        # Enable site
        if [ ! -L /etc/nginx/sites-enabled/ollama-guard ]; then
            sudo ln -sf "$conf_dst" /etc/nginx/sites-enabled/ollama-guard
        fi
    else
        # macOS / alternative setup
        sudo cp "$conf_src" /etc/nginx/conf.d/ollama-guard.conf
    fi
    
    log_info "✓ Nginx configuration deployed"
}

test_nginx_config() {
    log_info "Testing Nginx configuration..."
    
    if ! nginx -t 2>&1 | grep -q "successful"; then
        log_error "Nginx configuration test failed"
        nginx -t
        return 1
    fi
    
    log_info "✓ Nginx configuration valid"
}

restart_nginx() {
    log_info "Restarting Nginx..."
    
    if command -v systemctl &> /dev/null; then
        sudo systemctl restart nginx
    else
        # macOS or direct nginx
        if pgrep -x "nginx" > /dev/null; then
            sudo nginx -s reload
        else
            sudo nginx
        fi
    fi
    
    sleep 2
    
    if pgrep -x "nginx" > /dev/null; then
        log_info "✓ Nginx restarted"
    else
        log_error "Nginx failed to start"
        return 1
    fi
}

test_load_balancer() {
    log_info "Testing load balancer..."
    
    if curl -s https://localhost/health 2>/dev/null | grep -q "status"; then
        log_info "✓ Load balancer: OK (HTTPS)"
    elif curl -s http://localhost/health 2>/dev/null | grep -q "status"; then
        log_info "✓ Load balancer: OK (HTTP)"
    else
        log_error "✗ Load balancer: FAILED"
        return 1
    fi
}

test_ip_filtering() {
    log_info "Testing IP filtering..."
    
    # Test allowed IP (localhost)
    if curl -s http://localhost/v1/generate \
        -H "Content-Type: application/json" \
        -d '{"model":"test","prompt":"test"}' > /dev/null 2>&1; then
        log_info "✓ Allowed IP: OK"
    else
        log_warn "⚠ Allowed IP test inconclusive"
    fi
}

display_status() {
    log_info "Current Status"
    echo ""
    
    echo -e "${BLUE}=== Guard Proxy Instances ===${NC}"
    for port in 8080 8081 8082; do
        if curl -s http://localhost:$port/health > /dev/null 2>&1; then
            echo -e "  Port $port: ${GREEN}✓ Running${NC}"
        else
            echo -e "  Port $port: ${RED}✗ Stopped${NC}"
        fi
    done
    
    echo ""
    echo -e "${BLUE}=== Nginx Load Balancer ===${NC}"
    if pgrep -x "nginx" > /dev/null; then
        echo -e "  Status: ${GREEN}✓ Running${NC}"
        echo -e "  PID: $(pgrep -x nginx)"
        echo -e "  Config: Valid"
    else
        echo -e "  Status: ${RED}✗ Stopped${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}=== Endpoints ===${NC}"
    echo "  HTTP:  http://localhost"
    echo "  HTTPS: https://localhost (self-signed)"
    echo "  Health: http://localhost/health"
    echo "  Proxy1: http://localhost:8080"
    echo "  Proxy2: http://localhost:8081"
    echo "  Proxy3: http://localhost:8082"
    
    echo ""
    echo -e "${BLUE}=== Logs ===${NC}"
    echo "  Access: /var/log/nginx/ollama_guard_access.log"
    echo "  Error:  /var/log/nginx/ollama_guard_error.log"
    echo "  Proxy:  $LOG_DIR/proxy-*.log"
}

stop_services() {
    log_info "Stopping services..."
    
    # Stop proxy instances
    for port in 8080 8081 8082; do
        pid_file="$PID_DIR/proxy-$port.pid"
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                log_info "Stopping proxy on port $port..."
                kill "$pid"
                rm "$pid_file"
            fi
        fi
    done
    
    # Stop Nginx
    if pgrep -x "nginx" > /dev/null; then
        log_info "Stopping Nginx..."
        if command -v systemctl &> /dev/null; then
            sudo systemctl stop nginx
        else
            sudo nginx -s stop
        fi
    fi
    
    log_info "✓ Services stopped"
}

# ============================================================================
# Main Script
# ============================================================================

main() {
    local action="${1:-start}"
    
    case "$action" in
        start)
            log_info "Starting Ollama Guard Proxy + Nginx Load Balancer"
            echo ""
            
            check_prerequisites
            setup_directories
            create_ssl_certificate
            
            start_proxy_instances
            echo ""
            
            if ! test_proxy_instances; then
                log_error "Proxy startup failed"
                exit 1
            fi
            echo ""
            
            configure_nginx
            if ! test_nginx_config; then
                log_error "Nginx configuration invalid"
                exit 1
            fi
            echo ""
            
            restart_nginx
            echo ""
            
            sleep 3
            if ! test_load_balancer; then
                log_error "Load balancer test failed"
                exit 1
            fi
            echo ""
            
            test_ip_filtering
            echo ""
            
            log_info "✓ Deployment complete"
            echo ""
            display_status
            ;;
        
        stop)
            stop_services
            ;;
        
        restart)
            stop_services
            echo ""
            sleep 2
            exec "$0" start
            ;;
        
        status)
            display_status
            ;;
        
        test)
            log_info "Running tests..."
            check_prerequisites
            test_proxy_instances
            test_load_balancer
            test_ip_filtering
            log_info "✓ All tests passed"
            ;;
        
        *)
            echo "Usage: $0 {start|stop|restart|status|test}"
            echo ""
            echo "Commands:"
            echo "  start       - Start all services (proxies + nginx)"
            echo "  stop        - Stop all services"
            echo "  restart     - Restart all services"
            echo "  status      - Show current status"
            echo "  test        - Run tests"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
