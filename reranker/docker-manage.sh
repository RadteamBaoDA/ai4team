#!/bin/bash

# Docker management script for reranker service
# Usage: ./docker-manage.sh [command] [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default configuration
DEFAULT_COMPOSE_FILE="docker-compose.yml"
DEFAULT_ENV="production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage information
show_help() {
    cat << EOF
Docker Management Script for Reranker Service

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    build [ENV]         Build Docker images
    up [ENV]           Start services
    down [ENV]         Stop services
    restart [ENV]      Restart services
    logs [SERVICE]     Show logs
    shell [SERVICE]    Open shell in container
    status             Show service status
    clean              Clean up containers and images
    scale [N]          Scale reranker service to N instances
    update             Update and restart services

ENVIRONMENTS:
    dev                Development configuration (docker-compose.dev.yml)
    macos              Apple Silicon optimized (docker-compose.macos.yml)
    gpu                GPU optimized (docker-compose.gpu.yml)
    production         Production configuration (docker-compose.yml) [default]

OPTIONS:
    -f, --file FILE    Use specific docker-compose file
    -p, --profile PROF Enable specific profile
    --no-cache         Build without cache
    --pull             Pull latest images before build
    -d, --detach       Run in detached mode
    -v, --verbose      Verbose output

EXAMPLES:
    $0 build dev                 # Build development images
    $0 up gpu                    # Start GPU-optimized services
    $0 scale 3                   # Scale to 3 reranker instances
    $0 logs reranker             # Show reranker logs
    $0 shell reranker            # Open shell in reranker container
    $0 up --profile monitoring   # Start with monitoring services

EOF
}

# Get compose file based on environment
get_compose_file() {
    local env="${1:-$DEFAULT_ENV}"
    case "$env" in
        "dev"|"development")
            echo "docker-compose.dev.yml"
            ;;
        "macos"|"apple")
            echo "docker-compose.macos.yml"
            ;;
        "gpu"|"nvidia")
            echo "docker-compose.gpu.yml"
            ;;
        "scale"|"multi")
            echo "docker-compose.yml -f docker-compose.scale.yml"
            ;;
        "prod"|"production"|*)
            echo "docker-compose.yml"
            ;;
    esac
}

# Build Docker images
docker_build() {
    local env="${1:-$DEFAULT_ENV}"
    local compose_file=$(get_compose_file "$env")
    
    log_info "Building Docker images for environment: $env"
    
    local build_args=""
    if [[ "$*" == *"--no-cache"* ]]; then
        build_args="$build_args --no-cache"
    fi
    
    if [[ "$*" == *"--pull"* ]]; then
        build_args="$build_args --pull"
    fi
    
    docker-compose -f $compose_file build $build_args
    log_success "Build completed successfully"
}

# Start services
docker_up() {
    local env="${1:-$DEFAULT_ENV}"
    local compose_file=$(get_compose_file "$env")
    
    log_info "Starting services for environment: $env"
    
    local up_args=""
    if [[ "$*" == *"--detach"* ]] || [[ "$*" == *"-d"* ]]; then
        up_args="$up_args -d"
    fi
    
    # Extract profile if specified
    if [[ "$*" == *"--profile"* ]]; then
        local profile=$(echo "$*" | sed -n 's/.*--profile \([^ ]*\).*/\1/p')
        up_args="$up_args --profile $profile"
    fi
    
    docker-compose -f $compose_file up $up_args
    log_success "Services started successfully"
}

# Stop services
docker_down() {
    local env="${1:-$DEFAULT_ENV}"
    local compose_file=$(get_compose_file "$env")
    
    log_info "Stopping services for environment: $env"
    docker-compose -f $compose_file down
    log_success "Services stopped successfully"
}

# Restart services
docker_restart() {
    local env="${1:-$DEFAULT_ENV}"
    log_info "Restarting services for environment: $env"
    docker_down "$env"
    sleep 2
    docker_up "$env" -d
}

# Show logs
docker_logs() {
    local service="${1:-reranker}"
    local env="${2:-$DEFAULT_ENV}"
    local compose_file=$(get_compose_file "$env")
    
    log_info "Showing logs for service: $service"
    docker-compose -f $compose_file logs -f "$service"
}

# Open shell in container
docker_shell() {
    local service="${1:-reranker}"
    local env="${2:-$DEFAULT_ENV}"
    local compose_file=$(get_compose_file "$env")
    
    log_info "Opening shell in service: $service"
    docker-compose -f $compose_file exec "$service" bash
}

# Show service status
docker_status() {
    local env="${1:-$DEFAULT_ENV}"
    local compose_file=$(get_compose_file "$env")
    
    log_info "Service status:"
    docker-compose -f $compose_file ps
    
    echo ""
    log_info "Docker system information:"
    docker system df
}

# Clean up
docker_clean() {
    log_warning "Cleaning up Docker containers and images..."
    
    # Stop all reranker containers
    docker-compose -f docker-compose.yml down 2>/dev/null || true
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    docker-compose -f docker-compose.macos.yml down 2>/dev/null || true
    docker-compose -f docker-compose.gpu.yml down 2>/dev/null || true
    
    # Remove containers
    docker container prune -f
    
    # Remove images (ask for confirmation)
    read -p "Remove reranker Docker images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker images | grep reranker | awk '{print $3}' | xargs -r docker rmi -f
        log_success "Images removed"
    fi
    
    # Remove unused volumes and networks
    docker volume prune -f
    docker network prune -f
    
    log_success "Cleanup completed"
}

# Scale services
docker_scale() {
    local replicas="${1:-3}"
    
    log_info "Scaling reranker service to $replicas instances"
    docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale reranker="$replicas"
    log_success "Scaled to $replicas instances"
}

# Update services
docker_update() {
    local env="${1:-$DEFAULT_ENV}"
    
    log_info "Updating services for environment: $env"
    docker_build "$env" --pull
    docker_restart "$env"
    log_success "Update completed"
}

# Health check
health_check() {
    local port="${1:-8000}"
    
    log_info "Checking service health on port $port..."
    
    for i in {1..30}; do
        if curl -f -s "http://localhost:$port/health" > /dev/null; then
            log_success "Service is healthy!"
            return 0
        fi
        log_info "Waiting for service to be ready... ($i/30)"
        sleep 2
    done
    
    log_error "Service health check failed"
    return 1
}

# Main command processing
case "${1:-help}" in
    "build")
        shift
        docker_build "$@"
        ;;
    "up"|"start")
        shift
        docker_up "$@"
        ;;
    "down"|"stop")
        shift
        docker_down "$@"
        ;;
    "restart")
        shift
        docker_restart "$@"
        ;;
    "logs")
        shift
        docker_logs "$@"
        ;;
    "shell"|"exec")
        shift
        docker_shell "$@"
        ;;
    "status"|"ps")
        shift
        docker_status "$@"
        ;;
    "clean"|"cleanup")
        docker_clean
        ;;
    "scale")
        shift
        docker_scale "$@"
        ;;
    "update")
        shift
        docker_update "$@"
        ;;
    "health")
        shift
        health_check "$@"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac