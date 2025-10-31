#!/bin/bash

# Ollama Guardrails Docker Management Script
# Provides easy commands to manage the Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ollama-guardrails"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the docker directory
cd "$COMPOSE_DIR"

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

show_help() {
    cat << EOF
Ollama Guardrails Docker Management Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
  up [PROFILE]        Start services (default: all services)
  down                Stop and remove services
  restart [SERVICE]   Restart specific service or all services
  build [SERVICE]     Build or rebuild services
  logs [SERVICE]      Show logs for specific service or all services
  status              Show status of all services
  clean               Remove stopped containers, unused networks and volumes
  deep-clean          Remove everything including images (DESTRUCTIVE)
  shell SERVICE       Open shell in running container
  exec SERVICE CMD    Execute command in running container
  update              Pull latest images and rebuild
  dev                 Start development environment with hot reload
  prod                Start production environment
  macos               Start macOS optimized environment
  redis               Start only Redis (for external proxy)
  monitor             Start with monitoring stack (Prometheus + Grafana)
  
Profiles:
  default             Standard services (proxy, ollama, redis)
  dev                 Development services + debugging tools
  monitoring          Add Prometheus and Grafana
  
Services:
  ollama-guard-proxy  The main proxy service
  ollama              Ollama LLM service
  redis               Redis cache service
  redis-commander     Redis web UI (dev profile only)
  prometheus          Metrics collection (monitoring profile)
  grafana             Metrics dashboard (monitoring profile)

Examples:
  $0 up                    # Start all default services
  $0 up dev               # Start with development profile
  $0 dev                  # Start development environment
  $0 logs proxy           # Show proxy logs
  $0 shell proxy          # Open shell in proxy container
  $0 build proxy          # Rebuild only the proxy service
  $0 restart              # Restart all services
  $0 clean                # Clean up unused resources

EOF
}

# Check if docker and docker-compose are available
check_requirements() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
}

# Get service name mapping
get_service_name() {
    case "$1" in
        "proxy"|"guard"|"guardrails") echo "ollama-guard-proxy" ;;
        "ollama"|"llm") echo "ollama" ;;
        "redis"|"cache") echo "redis" ;;
        "redis-ui"|"redis-commander") echo "redis-commander" ;;
        "prometheus"|"prom") echo "prometheus" ;;
        "grafana") echo "grafana" ;;
        *) echo "$1" ;;
    esac
}

# Start services
start_services() {
    local profile="$1"
    local compose_files="-f $COMPOSE_FILE"
    
    case "$profile" in
        "dev"|"development")
            compose_files="$compose_files -f docker-compose.override.yml"
            log_info "Starting development environment..."
            docker-compose $compose_files --profile dev up -d
            ;;
        "prod"|"production") 
            log_info "Starting production environment..."
            docker-compose $compose_files up -d
            ;;
        "macos"|"mac")
            compose_files="-f docker-compose-macos.yml"
            log_info "Starting macOS optimized environment..."
            docker-compose $compose_files up -d
            ;;
        "redis"|"cache-only")
            compose_files="-f docker-compose-redis.yml"
            log_info "Starting Redis only..."
            docker-compose $compose_files up -d
            ;;
        "monitoring"|"monitor")
            compose_files="$compose_files -f docker-compose.override.yml"
            log_info "Starting with monitoring stack..."
            docker-compose $compose_files --profile monitoring up -d
            ;;
        *)
            if [[ -n "$profile" ]]; then
                compose_files="$compose_files --profile $profile"
            fi
            log_info "Starting services..."
            docker-compose $compose_files up -d
            ;;
    esac
    
    log_success "Services started successfully!"
    show_status
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    docker-compose -f $COMPOSE_FILE -f docker-compose.override.yml -f docker-compose-macos.yml -f docker-compose-redis.yml down
    log_success "Services stopped successfully!"
}

# Restart services
restart_services() {
    local service="$1"
    if [[ -n "$service" ]]; then
        service=$(get_service_name "$service")
        log_info "Restarting service: $service"
        docker-compose restart "$service"
    else
        log_info "Restarting all services..."
        docker-compose restart
    fi
    log_success "Service(s) restarted successfully!"
}

# Build services
build_services() {
    local service="$1"
    if [[ -n "$service" ]]; then
        service=$(get_service_name "$service")
        log_info "Building service: $service"
        docker-compose build --no-cache "$service"
    else
        log_info "Building all services..."
        docker-compose build --no-cache
    fi
    log_success "Build completed successfully!"
}

# Show logs
show_logs() {
    local service="$1"
    if [[ -n "$service" ]]; then
        service=$(get_service_name "$service")
        log_info "Showing logs for: $service"
        docker-compose logs -f "$service"
    else
        log_info "Showing logs for all services..."
        docker-compose logs -f
    fi
}

# Show status
show_status() {
    log_info "Service Status:"
    docker-compose ps
    echo
    log_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Clean up resources
clean_resources() {
    log_info "Cleaning up unused resources..."
    docker system prune -f
    docker volume prune -f
    log_success "Cleanup completed!"
}

# Deep clean (remove everything)
deep_clean() {
    log_warning "This will remove ALL Docker resources for this project!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Performing deep clean..."
        stop_services
        docker-compose down --rmi all --volumes --remove-orphans
        docker system prune -a -f --volumes
        log_success "Deep clean completed!"
    else
        log_info "Deep clean cancelled."
    fi
}

# Open shell in container
open_shell() {
    local service="$1"
    if [[ -z "$service" ]]; then
        log_error "Service name required for shell command"
        return 1
    fi
    
    service=$(get_service_name "$service")
    local container=$(docker-compose ps -q "$service")
    
    if [[ -z "$container" ]]; then
        log_error "Service '$service' is not running"
        return 1
    fi
    
    log_info "Opening shell in $service container..."
    docker exec -it "$container" /bin/bash
}

# Execute command in container
exec_command() {
    local service="$1"
    shift
    local cmd="$@"
    
    if [[ -z "$service" ]] || [[ -z "$cmd" ]]; then
        log_error "Service name and command required"
        return 1
    fi
    
    service=$(get_service_name "$service")
    local container=$(docker-compose ps -q "$service")
    
    if [[ -z "$container" ]]; then
        log_error "Service '$service' is not running"
        return 1
    fi
    
    log_info "Executing command in $service: $cmd"
    docker exec -it "$container" $cmd
}

# Update services
update_services() {
    log_info "Updating services..."
    docker-compose pull
    docker-compose build --pull
    docker-compose up -d
    log_success "Services updated successfully!"
}

# Main command handler
main() {
    check_requirements
    
    local command="$1"
    shift || true
    
    case "$command" in
        "up"|"start")
            start_services "$@"
            ;;
        "down"|"stop")
            stop_services
            ;;
        "restart")
            restart_services "$@"
            ;;
        "build")
            build_services "$@"
            ;;
        "logs"|"log")
            show_logs "$@"
            ;;
        "status"|"ps")
            show_status
            ;;
        "clean")
            clean_resources
            ;;
        "deep-clean"|"nuke")
            deep_clean
            ;;
        "shell"|"bash")
            open_shell "$@"
            ;;
        "exec")
            exec_command "$@"
            ;;
        "update")
            update_services
            ;;
        "dev"|"development")
            start_services "dev"
            ;;
        "prod"|"production")
            start_services "prod"
            ;;
        "macos"|"mac")
            start_services "macos"
            ;;
        "redis")
            start_services "redis"
            ;;
        "monitor"|"monitoring")
            start_services "monitoring"
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "")
            log_error "No command specified. Use '$0 help' for usage information."
            exit 1
            ;;
        *)
            log_error "Unknown command: $command. Use '$0 help' for usage information."
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"