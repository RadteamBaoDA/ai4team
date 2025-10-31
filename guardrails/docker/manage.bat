@echo off
setlocal enabledelayedexpansion

REM Ollama Guardrails Docker Management Script for Windows
REM Provides easy commands to manage the Docker environment

set PROJECT_NAME=ollama-guardrails
set COMPOSE_FILE=docker-compose.yml
set COMPOSE_DIR=%~dp0

REM Change to the docker directory
cd /d "%COMPOSE_DIR%"

REM Colors for Windows (using ANSI escape sequences if supported)
set "RED="
set "GREEN="
set "YELLOW="
set "BLUE="
set "NC="

REM Helper functions
:log_info
echo [INFO] %~1
goto :eof

:log_success
echo [SUCCESS] %~1
goto :eof

:log_warning
echo [WARNING] %~1
goto :eof

:log_error
echo [ERROR] %~1
goto :eof

:show_help
echo Ollama Guardrails Docker Management Script for Windows
echo.
echo Usage: %~nx0 [COMMAND] [OPTIONS]
echo.
echo Commands:
echo   up [PROFILE]        Start services (default: all services)
echo   down                Stop and remove services
echo   restart [SERVICE]   Restart specific service or all services
echo   build [SERVICE]     Build or rebuild services
echo   logs [SERVICE]      Show logs for specific service or all services
echo   status              Show status of all services
echo   clean               Remove stopped containers, unused networks and volumes
echo   deep-clean          Remove everything including images (DESTRUCTIVE)
echo   shell SERVICE       Open shell in running container
echo   exec SERVICE CMD    Execute command in running container
echo   update              Pull latest images and rebuild
echo   dev                 Start development environment with hot reload
echo   prod                Start production environment
echo   macos               Start macOS optimized environment
echo   redis               Start only Redis (for external proxy)
echo   monitor             Start with monitoring stack (Prometheus + Grafana)
echo.
echo Profiles:
echo   default             Standard services (proxy, ollama, redis)
echo   dev                 Development services + debugging tools
echo   monitoring          Add Prometheus and Grafana
echo.
echo Services:
echo   ollama-guard-proxy  The main proxy service
echo   ollama              Ollama LLM service
echo   redis               Redis cache service
echo   redis-commander     Redis web UI (dev profile only)
echo   prometheus          Metrics collection (monitoring profile)
echo   grafana             Metrics dashboard (monitoring profile)
echo.
echo Examples:
echo   %~nx0 up                    # Start all default services
echo   %~nx0 up dev               # Start with development profile
echo   %~nx0 dev                  # Start development environment
echo   %~nx0 logs proxy           # Show proxy logs
echo   %~nx0 shell proxy          # Open shell in proxy container
echo   %~nx0 build proxy          # Rebuild only the proxy service
echo   %~nx0 restart              # Restart all services
echo   %~nx0 clean                # Clean up unused resources
echo.
goto :eof

:check_requirements
where docker >nul 2>nul
if errorlevel 1 (
    call :log_error "Docker is not installed or not in PATH"
    exit /b 1
)

where docker-compose >nul 2>nul
if errorlevel 1 (
    call :log_error "Docker Compose is not installed or not in PATH"
    exit /b 1
)
goto :eof

:get_service_name
set service_input=%~1
if "%service_input%"=="proxy" (set service_name=ollama-guard-proxy) else (
if "%service_input%"=="guard" (set service_name=ollama-guard-proxy) else (
if "%service_input%"=="guardrails" (set service_name=ollama-guard-proxy) else (
if "%service_input%"=="ollama" (set service_name=ollama) else (
if "%service_input%"=="llm" (set service_name=ollama) else (
if "%service_input%"=="redis" (set service_name=redis) else (
if "%service_input%"=="cache" (set service_name=redis) else (
if "%service_input%"=="redis-ui" (set service_name=redis-commander) else (
if "%service_input%"=="redis-commander" (set service_name=redis-commander) else (
if "%service_input%"=="prometheus" (set service_name=prometheus) else (
if "%service_input%"=="prom" (set service_name=prometheus) else (
if "%service_input%"=="grafana" (set service_name=grafana) else (
    set service_name=%service_input%
))))))))))))
goto :eof

:start_services
set profile=%~1
set compose_files=-f %COMPOSE_FILE%

if "%profile%"=="dev" (
    set compose_files=%compose_files% -f docker-compose.override.yml
    call :log_info "Starting development environment..."
    docker-compose %compose_files% --profile dev up -d
) else if "%profile%"=="development" (
    set compose_files=%compose_files% -f docker-compose.override.yml
    call :log_info "Starting development environment..."
    docker-compose %compose_files% --profile dev up -d
) else if "%profile%"=="prod" (
    call :log_info "Starting production environment..."
    docker-compose %compose_files% up -d
) else if "%profile%"=="production" (
    call :log_info "Starting production environment..."
    docker-compose %compose_files% up -d
) else if "%profile%"=="macos" (
    set compose_files=-f docker-compose-macos.yml
    call :log_info "Starting macOS optimized environment..."
    docker-compose %compose_files% up -d
) else if "%profile%"=="mac" (
    set compose_files=-f docker-compose-macos.yml
    call :log_info "Starting macOS optimized environment..."
    docker-compose %compose_files% up -d
) else if "%profile%"=="redis" (
    set compose_files=-f docker-compose-redis.yml
    call :log_info "Starting Redis only..."
    docker-compose %compose_files% up -d
) else if "%profile%"=="cache-only" (
    set compose_files=-f docker-compose-redis.yml
    call :log_info "Starting Redis only..."
    docker-compose %compose_files% up -d
) else if "%profile%"=="monitoring" (
    set compose_files=%compose_files% -f docker-compose.override.yml
    call :log_info "Starting with monitoring stack..."
    docker-compose %compose_files% --profile monitoring up -d
) else if "%profile%"=="monitor" (
    set compose_files=%compose_files% -f docker-compose.override.yml
    call :log_info "Starting with monitoring stack..."
    docker-compose %compose_files% --profile monitoring up -d
) else (
    if not "%profile%"=="" (
        set compose_files=%compose_files% --profile %profile%
    )
    call :log_info "Starting services..."
    docker-compose %compose_files% up -d
)

call :log_success "Services started successfully!"
call :show_status
goto :eof

:stop_services
call :log_info "Stopping services..."
docker-compose -f %COMPOSE_FILE% -f docker-compose.override.yml -f docker-compose-macos.yml -f docker-compose-redis.yml down
call :log_success "Services stopped successfully!"
goto :eof

:restart_services
set service=%~1
if not "%service%"=="" (
    call :get_service_name "%service%"
    call :log_info "Restarting service: !service_name!"
    docker-compose restart "!service_name!"
) else (
    call :log_info "Restarting all services..."
    docker-compose restart
)
call :log_success "Service(s) restarted successfully!"
goto :eof

:build_services
set service=%~1
if not "%service%"=="" (
    call :get_service_name "%service%"
    call :log_info "Building service: !service_name!"
    docker-compose build --no-cache "!service_name!"
) else (
    call :log_info "Building all services..."
    docker-compose build --no-cache
)
call :log_success "Build completed successfully!"
goto :eof

:show_logs
set service=%~1
if not "%service%"=="" (
    call :get_service_name "%service%"
    call :log_info "Showing logs for: !service_name!"
    docker-compose logs -f "!service_name!"
) else (
    call :log_info "Showing logs for all services..."
    docker-compose logs -f
)
goto :eof

:show_status
call :log_info "Service Status:"
docker-compose ps
echo.
call :log_info "Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
goto :eof

:clean_resources
call :log_info "Cleaning up unused resources..."
docker system prune -f
docker volume prune -f
call :log_success "Cleanup completed!"
goto :eof

:deep_clean
call :log_warning "This will remove ALL Docker resources for this project!"
set /p confirm="Are you sure? (y/N): "
if /i "%confirm%"=="y" (
    call :log_info "Performing deep clean..."
    call :stop_services
    docker-compose down --rmi all --volumes --remove-orphans
    docker system prune -a -f --volumes
    call :log_success "Deep clean completed!"
) else (
    call :log_info "Deep clean cancelled."
)
goto :eof

:open_shell
set service=%~1
if "%service%"=="" (
    call :log_error "Service name required for shell command"
    goto :eof
)

call :get_service_name "%service%"
for /f %%i in ('docker-compose ps -q "!service_name!"') do set container=%%i

if "%container%"=="" (
    call :log_error "Service '!service_name!' is not running"
    goto :eof
)

call :log_info "Opening shell in !service_name! container..."
docker exec -it "%container%" /bin/bash
goto :eof

:exec_command
set service=%~1
shift
set cmd=%*

if "%service%"=="" (
    call :log_error "Service name and command required"
    goto :eof
)
if "%cmd%"=="" (
    call :log_error "Service name and command required"
    goto :eof
)

call :get_service_name "%service%"
for /f %%i in ('docker-compose ps -q "!service_name!"') do set container=%%i

if "%container%"=="" (
    call :log_error "Service '!service_name!' is not running"
    goto :eof
)

call :log_info "Executing command in !service_name!: %cmd%"
docker exec -it "%container%" %cmd%
goto :eof

:update_services
call :log_info "Updating services..."
docker-compose pull
docker-compose build --pull
docker-compose up -d
call :log_success "Services updated successfully!"
goto :eof

REM Main command handler
call :check_requirements
if errorlevel 1 exit /b 1

set command=%~1
set param1=%~2
set param2=%~3
set param3=%~4

if "%command%"=="up" (call :start_services "%param1%") else (
if "%command%"=="start" (call :start_services "%param1%") else (
if "%command%"=="down" (call :stop_services) else (
if "%command%"=="stop" (call :stop_services) else (
if "%command%"=="restart" (call :restart_services "%param1%") else (
if "%command%"=="build" (call :build_services "%param1%") else (
if "%command%"=="logs" (call :show_logs "%param1%") else (
if "%command%"=="log" (call :show_logs "%param1%") else (
if "%command%"=="status" (call :show_status) else (
if "%command%"=="ps" (call :show_status) else (
if "%command%"=="clean" (call :clean_resources) else (
if "%command%"=="deep-clean" (call :deep_clean) else (
if "%command%"=="nuke" (call :deep_clean) else (
if "%command%"=="shell" (call :open_shell "%param1%") else (
if "%command%"=="bash" (call :open_shell "%param1%") else (
if "%command%"=="exec" (call :exec_command "%param1%" "%param2%" "%param3%") else (
if "%command%"=="update" (call :update_services) else (
if "%command%"=="dev" (call :start_services "dev") else (
if "%command%"=="development" (call :start_services "dev") else (
if "%command%"=="prod" (call :start_services "prod") else (
if "%command%"=="production" (call :start_services "prod") else (
if "%command%"=="macos" (call :start_services "macos") else (
if "%command%"=="mac" (call :start_services "macos") else (
if "%command%"=="redis" (call :start_services "redis") else (
if "%command%"=="monitor" (call :start_services "monitoring") else (
if "%command%"=="monitoring" (call :start_services "monitoring") else (
if "%command%"=="help" (call :show_help) else (
if "%command%"=="--help" (call :show_help) else (
if "%command%"=="-h" (call :show_help) else (
if "%command%"=="" (
    call :log_error "No command specified. Use '%~nx0 help' for usage information."
    exit /b 1
) else (
    call :log_error "Unknown command: %command%. Use '%~nx0 help' for usage information."
    exit /b 1
)))))))))))))))))))))))))))))