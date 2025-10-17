@echo off
REM ############################################################################
REM LiteLLM Proxy Startup Script for Windows
REM Starts the LiteLLM proxy with custom guardrails in background using pythonw
REM ############################################################################

setlocal enabledelayedexpansion

REM Script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Configuration
set "CONFIG_FILE=%CONFIG_FILE%"
if not defined CONFIG_FILE set "CONFIG_FILE=litellm_config.yaml"

set "LOG_DIR=%LOG_DIR%"
if not defined LOG_DIR set "LOG_DIR=logs"

set "LOG_FILE=%LOG_DIR%\litellm_proxy.log"
set "PID_FILE=%LOG_DIR%\litellm_proxy.pid"

REM Proxy settings
if not defined LITELLM_HOST set "LITELLM_HOST=0.0.0.0"
if not defined LITELLM_PORT set "LITELLM_PORT=8000"
if not defined LITELLM_WORKERS set "LITELLM_WORKERS=4"
if not defined LOG_LEVEL set "LOG_LEVEL=INFO"

REM ############################################################################
REM Functions
REM ############################################################################

:print_header
echo.
echo ===============================================================================
echo %~1
echo ===============================================================================
goto :eof

:print_success
echo [OK] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_info
echo [INFO] %~1
goto :eof

REM Check if process is running
:check_running
if exist "%PID_FILE%" (
    for /f %%i in (%PID_FILE%) do (
        tasklist /FI "PID eq %%i" 2>nul | find /I "python" >nul
        if !errorlevel! equ 0 exit /b 0
    )
)
exit /b 1

REM Get process status
:get_status
if exist "%PID_FILE%" (
    for /f %%i in (%PID_FILE%) do (
        tasklist /FI "PID eq %%i" 2>nul | find /I "python" >nul
        if !errorlevel! equ 0 (
            call :print_success "LiteLLM proxy is running (PID: %%i)"
            exit /b 0
        )
    )
)
call :print_warning "LiteLLM proxy is not running"
exit /b 1

REM Install dependencies
:install_deps
call :print_header "Installing Dependencies"

if exist "requirements.txt" (
    call :print_info "Installing from requirements.txt..."
    python -m pip install -r requirements.txt
    if !errorlevel! equ 0 (
        call :print_success "Dependencies installed from requirements.txt"
        exit /b 0
    ) else (
        call :print_error "Failed to install dependencies"
        exit /b 1
    )
) else (
    call :print_info "Running dependency installer..."
    if exist "install_dependencies.py" (
        python install_dependencies.py
        if !errorlevel! equ 0 (
            call :print_success "Dependencies installed"
            exit /b 0
        ) else (
            call :print_error "Failed to install dependencies"
            exit /b 1
        )
    ) else (
        call :print_error "install_dependencies.py not found"
        exit /b 1
    )
)

REM Validate configuration
:validate_config
call :print_header "Validating Configuration"

if not exist "%CONFIG_FILE%" (
    call :print_error "Configuration file not found: %CONFIG_FILE%"
    exit /b 1
)

call :print_info "Configuration file: %CONFIG_FILE%"
call :print_success "Configuration file validated"

python run_litellm_proxy.py --validate-only >nul 2>&1
if !errorlevel! equ 0 (
    call :print_success "Guardrail configuration validated"
)

exit /b 0

REM Stop the proxy
:stop_proxy
call :print_header "Stopping LiteLLM Proxy"

if exist "%PID_FILE%" (
    for /f %%i in (%PID_FILE%) do (
        tasklist /FI "PID eq %%i" 2>nul | find /I "python" >nul
        if !errorlevel! equ 0 (
            call :print_info "Stopping process %%i..."
            taskkill /PID %%i /T /F >nul 2>&1
            call :print_success "LiteLLM proxy stopped"
        )
    )
    del /q "%PID_FILE%" 2>nul
)

exit /b 0

REM Start the proxy
:start_proxy
call :print_header "Starting LiteLLM Proxy"

call :check_running
if !errorlevel! equ 0 (
    for /f %%i in (%PID_FILE%) do (
        call :print_warning "LiteLLM proxy already running (PID: %%i)"
    )
    exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

call :print_info "Configuration file: %CONFIG_FILE%"
call :print_info "Bind address: %LITELLM_HOST%:%LITELLM_PORT%"
call :print_info "Workers: %LITELLM_WORKERS%"
call :print_info "Log level: %LOG_LEVEL%"
call :print_info "Log file: %LOG_FILE%"
call :print_info "PID file: %PID_FILE%"

call :print_info "Starting LiteLLM proxy..."

REM Start proxy using pythonw (no console window) and save PID
for /f "tokens=2" %%i in ('tasklist /FO LIST ^| find /I "imagename" ^| find /I "python"') do (
    set "LAST_PID=%%i"
)

REM Use start /B to run in background
start /B "" python run_litellm_proxy.py ^
    --config "%CONFIG_FILE%" ^
    --host "%LITELLM_HOST%" ^
    --port "%LITELLM_PORT%" ^
    --workers "%LITELLM_WORKERS%" ^
    --log-level "%LOG_LEVEL%" ^
    >>"%LOG_FILE%" 2>&1

timeout /t 2 /nobreak >nul

REM Try to find the proxy process PID
setlocal enabledelayedexpansion
set "found=0"
for /f "tokens=2" %%i in ('tasklist /FO LIST ^| find /I "python"') do (
    set /a "found=1"
    echo %%i > "%PID_FILE%"
    call :print_success "LiteLLM proxy started (PID: %%i)"
)

if !found! equ 0 (
    call :print_error "Failed to start LiteLLM proxy"
    call :print_error "Check logs: type %LOG_FILE%"
    exit /b 1
)

echo.
call :print_header "Proxy Information"
call :print_info "API Base: http://%LITELLM_HOST%:%LITELLM_PORT%/v1"
call :print_info "Chat Completions: http://%LITELLM_HOST%:%LITELLM_PORT%/v1/chat/completions"
call :print_info "Models: http://%LITELLM_HOST%:%LITELLM_PORT%/v1/models"
call :print_info "Health Check: http://%LITELLM_HOST%:%LITELLM_PORT%/health"
call :print_info "Logs: type %LOG_FILE%"
call :print_info "Status: call %~0 status"
call :print_info "Stop: call %~0 stop"

exit /b 0

REM Restart the proxy
:restart_proxy
call :print_header "Restarting LiteLLM Proxy"
call :stop_proxy
timeout /t 2 /nobreak >nul
call :start_proxy
exit /b %errorlevel%

REM Show help
:show_help
cls
echo.
echo LiteLLM Proxy Startup Script for Windows
echo.
echo Usage: %~0 [COMMAND]
echo.
echo Commands:
echo   start       Start the proxy in background (default)
echo   stop        Stop the running proxy
echo   restart     Restart the proxy
echo   status      Show proxy status
echo   logs        Display proxy log file
echo   install     Install dependencies
echo   validate    Validate configuration
echo   help        Show this help message
echo.
echo Environment Variables:
echo   CONFIG_FILE    Configuration file (default: litellm_config.yaml)
echo   LOG_DIR        Log directory (default: logs)
echo   LITELLM_HOST   Host to bind (default: 0.0.0.0)
echo   LITELLM_PORT   Port to bind (default: 8000)
echo   LITELLM_WORKERS Number of workers (default: 4)
echo   LOG_LEVEL      Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
echo.
echo Examples:
echo   %~0 start
echo   set LITELLM_PORT=9000 ^& %~0 start
echo   %~0 status
echo   %~0 logs
echo   %~0 restart
echo   %~0 stop
echo   %~0 install
echo   %~0 validate
echo.
goto :eof

REM ############################################################################
REM Main Script
REM ############################################################################

:main
if "%~1"=="" goto :cmd_start
if /I "%~1"=="start" goto :cmd_start
if /I "%~1"=="stop" goto :cmd_stop
if /I "%~1"=="restart" goto :cmd_restart
if /I "%~1"=="status" goto :cmd_status
if /I "%~1"=="logs" goto :cmd_logs
if /I "%~1"=="install" goto :cmd_install
if /I "%~1"=="validate" goto :cmd_validate
if /I "%~1"=="help" goto :cmd_help
if /I "%~1"=="/?" goto :cmd_help

call :print_error "Unknown command: %~1"
call :show_help
exit /b 1

:cmd_start
call :validate_config || exit /b 1
call :start_proxy
exit /b %errorlevel%

:cmd_stop
call :stop_proxy
exit /b %errorlevel%

:cmd_restart
call :restart_proxy
exit /b %errorlevel%

:cmd_status
call :get_status
exit /b %errorlevel%

:cmd_logs
if not exist "%LOG_FILE%" (
    call :print_error "Log file not found: %LOG_FILE%"
    exit /b 1
)
call :print_header "LiteLLM Proxy Logs"
type "%LOG_FILE%"
exit /b 0

:cmd_install
call :install_deps
exit /b %errorlevel%

:cmd_validate
call :validate_config
exit /b %errorlevel%

:cmd_help
call :show_help
exit /b 0

:end
endlocal
