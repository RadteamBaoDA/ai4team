@echo off
REM ============================================================================
REM Ollama Guard Proxy + Nginx Load Balancer - Deployment Script (Windows)
REM
REM This script automates deployment of:
REM  - 3 Guard Proxy instances (ports 8080, 8081, 8082)
REM  - Nginx load balancer with IP filtering and rate limiting
REM
REM Usage: deploy-nginx.bat [start|stop|restart|status|test]
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuration
set SCRIPT_DIR=%~dp0
set LOG_DIR=%TEMP%\ollama-guard-logs
set PID_FILE=%TEMP%\ollama-guard-pids.txt

REM Nginx paths (adjust as needed)
set NGINX_PATH=C:\nginx
set NGINX_EXE=%NGINX_PATH%\nginx.exe
set NGINX_CONF_SRC=%SCRIPT_DIR%nginx-ollama-production.conf
set NGINX_CONF_DST=%NGINX_PATH%\conf\servers\ollama-guard.conf

REM ============================================================================
REM Color output (simulated)
REM ============================================================================

REM [INFO] = blue
REM [WARN] = yellow
REM [ERROR] = red
REM [OK] = green

REM ============================================================================
REM Helper Functions
REM ============================================================================

:check_prerequisites
echo.
echo [INFO] Checking prerequisites...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    exit /b 1
)

REM Check Uvicorn
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Uvicorn not installed. Run: pip install uvicorn fastapi requests llm-guard pyyaml
    exit /b 1
)

REM Check Nginx
if not exist "%NGINX_EXE%" (
    echo [ERROR] Nginx not found at %NGINX_EXE%
    echo Please install Nginx or update NGINX_PATH in this script
    exit /b 1
)

echo [OK] All prerequisites met
goto :eof

:setup_directories
echo [INFO] Setting up directories...
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
echo [OK] Directories created
goto :eof

:start_proxy_instances
echo [INFO] Starting Guard Proxy instances...
echo.

for %%P in (8080 8081 8082) do (
    set PORT=%%P
    set LOG_FILE="%LOG_DIR%\proxy-!PORT!.log"
    
    echo [INFO] Starting proxy on port !PORT!...
    
    REM Start in new window
    start "Ollama Guard Proxy !PORT!" ^
        cmd /k "cd /d "%SCRIPT_DIR%" && run_proxy.bat --port !PORT! --workers 4 --log-level info"
    
    REM Give it time to start
    timeout /t 2 /nobreak
    
    echo [OK] Proxy started on port !PORT!
)

goto :eof

:test_proxy_instances
echo [INFO] Testing proxy instances...
setlocal enabledelayedexpansion
set ALL_OK=true

for %%P in (8080 8081 8082) do (
    set PORT=%%P
    curl -s http://localhost:!PORT!/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Port !PORT!: OK
    ) else (
        echo [ERROR] Port !PORT!: FAILED
        set ALL_OK=false
    )
)

if "!ALL_OK!"=="false" (
    exit /b 1
)
endlocal
goto :eof

:configure_nginx
echo [INFO] Configuring Nginx...

if not exist "%NGINX_CONF_SRC%" (
    echo [ERROR] Configuration file not found: %NGINX_CONF_SRC%
    exit /b 1
)

REM Create servers directory if not exists
if not exist "%NGINX_PATH%\conf\servers" (
    mkdir "%NGINX_PATH%\conf\servers"
)

REM Copy configuration
copy "%NGINX_CONF_SRC%" "%NGINX_CONF_DST%" >nul
echo [OK] Nginx configuration deployed

goto :eof

:test_nginx_config
echo [INFO] Testing Nginx configuration...

"%NGINX_EXE%" -t >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Nginx configuration test failed
    "%NGINX_EXE%" -t
    exit /b 1
)

echo [OK] Nginx configuration valid
goto :eof

:start_nginx
echo [INFO] Starting Nginx...

REM Kill existing nginx processes
taskkill /IM nginx.exe /F >nul 2>&1

REM Give time for cleanup
timeout /t 1 /nobreak

REM Start Nginx
cd /d "%NGINX_PATH%"
start nginx.exe

REM Give it time to start
timeout /t 2 /nobreak

REM Check if running
tasklist /FI "IMAGENAME eq nginx.exe" 2>NUL | find /I /N "nginx.exe">NUL
if errorlevel 1 (
    echo [ERROR] Nginx failed to start
    exit /b 1
)

echo [OK] Nginx started
cd /d "%SCRIPT_DIR%"
goto :eof

:test_load_balancer
echo [INFO] Testing load balancer...

curl -s http://localhost/health 2>nul | find /i "status" >nul
if errorlevel 0 (
    echo [OK] Load balancer: OK
) else (
    echo [ERROR] Load balancer: FAILED
    exit /b 1
)
goto :eof

:display_status
echo.
echo ================================================================================
echo                          Ollama Guard Proxy - Status
echo ================================================================================
echo.
echo === Guard Proxy Instances ===
for %%P in (8080 8081 8082) do (
    set PORT=%%P
    curl -s http://localhost:!PORT!/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Port !PORT!: [OK] Running
    ) else (
        echo   Port !PORT!: [FAILED] Stopped
    )
)
echo.

echo === Nginx Load Balancer ===
tasklist /FI "IMAGENAME eq nginx.exe" 2>NUL | find /I /N "nginx.exe">NUL
if errorlevel 1 (
    echo   Status: [FAILED] Stopped
) else (
    echo   Status: [OK] Running
)
echo.

echo === Endpoints ===
echo   HTTP:  http://localhost
echo   Health: http://localhost/health
echo   Proxy1: http://localhost:8080
echo   Proxy2: http://localhost:8081
echo   Proxy3: http://localhost:8082
echo.

echo === Logs ===
echo   Proxy logs: %LOG_DIR%\proxy-*.log
echo   Access log: %NGINX_PATH%\logs\access.log
echo   Error log:  %NGINX_PATH%\logs\error.log
echo.

echo ================================================================================
goto :eof

:stop_services
echo [INFO] Stopping services...
echo.

REM Stop Nginx
echo [INFO] Stopping Nginx...
taskkill /IM nginx.exe /F >nul 2>&1
echo [OK] Nginx stopped

REM Stop Proxy instances
echo [INFO] Stopping Guard Proxy instances...
taskkill /FI "WINDOWTITLE eq Ollama Guard Proxy*" /T /F >nul 2>&1
echo [OK] Proxy instances stopped

echo.
goto :eof

:main
setlocal enabledelayedexpansion
set ACTION=%1
if "!ACTION!"=="" set ACTION=start

if /i "!ACTION!"=="start" goto start_cmd
if /i "!ACTION!"=="stop" goto stop_cmd
if /i "!ACTION!"=="restart" goto restart_cmd
if /i "!ACTION!"=="status" goto status_cmd
if /i "!ACTION!"=="test" goto test_cmd

echo Usage: deploy-nginx.bat [start^|stop^|restart^|status^|test]
echo.
echo Commands:
echo   start       - Start all services (proxies + nginx)
echo   stop        - Stop all services
echo   restart     - Restart all services
echo   status      - Show current status
echo   test        - Run tests
exit /b 1

:start_cmd
echo.
echo ================================================================================
echo        Starting Ollama Guard Proxy + Nginx Load Balancer
echo ================================================================================
echo.

call :check_prerequisites
if errorlevel 1 exit /b 1

call :setup_directories
if errorlevel 1 exit /b 1

call :start_proxy_instances
if errorlevel 1 exit /b 1
echo.

call :test_proxy_instances
if errorlevel 1 exit /b 1
echo.

call :configure_nginx
if errorlevel 1 exit /b 1

call :test_nginx_config
if errorlevel 1 exit /b 1
echo.

call :start_nginx
if errorlevel 1 exit /b 1
echo.

timeout /t 3 /nobreak

call :test_load_balancer
if errorlevel 1 exit /b 1
echo.

echo [OK] Deployment complete
call :display_status
goto :eof

:stop_cmd
call :stop_services
goto :eof

:restart_cmd
call :stop_services
timeout /t 2 /nobreak
call :main start
goto :eof

:status_cmd
call :display_status
goto :eof

:test_cmd
echo [INFO] Running tests...
call :check_prerequisites
call :test_proxy_instances
call :test_load_balancer
echo [OK] All tests passed
goto :eof

:eof
endlocal
