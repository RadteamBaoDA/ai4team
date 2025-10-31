@echo off
REM Ollama Guard Proxy - Uvicorn Runner (Windows)
REM Run the proxy with Uvicorn with support for parallel/concurrent requests
REM
REM Usage:
REM   run_proxy.bat                             # Default: 4 workers, 128 concurrency
REM   run_proxy.bat --workers 8 --concurrency 256
REM   run_proxy.bat --host 0.0.0.0 --port 8080
REM   run_proxy.bat --reload                    # Auto-reload on code changes
REM   run_proxy.bat --debug                     # Show debug logs
REM
REM Nginx-Only Access (restrict to Nginx proxy):
REM   set NGINX_WHITELIST=127.0.0.1              # Single Nginx IP
REM   set NGINX_WHITELIST=192.168.1.10,192.168.1.11  # Multiple IPs
REM   set NGINX_WHITELIST=192.168.1.0/24         # CIDR range
REM   run_proxy.bat                              # Start with whitelist
REM
REM Python Virtual Environment:
REM   python -m venv venv                        # Create venv
REM   pip install -r requirements.txt            # Install dependencies
REM   set VENV_DIR=venv                          # Custom venv location
REM   set USE_VENV=true                          # Enable venv (default)
REM   run_proxy.bat                              # Start with venv
REM
REM Features:
REM   - Uvicorn ASGI server
REM   - Multi-worker support for parallel requests
REM   - Configurable concurrency per worker
REM   - Environment variable support
REM   - Health check endpoint
REM   - Request logging
REM   - Python virtual environment support
REM   - Nginx-only access control

setlocal enabledelayedexpansion

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Default configuration
set "HOST=0.0.0.0"
set "PORT=8080"
set "WORKERS=4"
set "CONCURRENCY=128"
set "LOG_LEVEL=info"
set "RELOAD=false"
set "CONFIG_FILE=%PROJECT_ROOT%\config\config.yaml"
set "PROXY_MODULE=src.ollama_guard_proxy:app"

REM Virtual environment setup
if not defined VENV_DIR set "VENV_DIR=%PROJECT_ROOT%\venv"
if not defined USE_VENV set "USE_VENV=true"
set "VENV_ACTIVATE=%VENV_DIR%\Scripts\activate.bat"

REM Default Python command (may be overridden to venv python)
set "PYTHON_CMD=python"
if "%USE_VENV%"=="true" (
  if exist "%VENV_DIR%\Scripts\python.exe" (
    set "PYTHON_CMD=%VENV_DIR%\Scripts\python.exe"
  )
)

REM Parse arguments
:parse_args
if "%~1"=="" goto done_parsing
if "%~1"=="--host" (
  set "HOST=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--port" (
  set "PORT=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--workers" (
  set "WORKERS=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--concurrency" (
  set "CONCURRENCY=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--log-level" (
  set "LOG_LEVEL=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--reload" (
  set "RELOAD=true"
  shift
  goto parse_args
)
if "%~1"=="--debug" (
  set "LOG_LEVEL=debug"
  shift
  goto parse_args
)
if "%~1"=="--config" (
  set "CONFIG_FILE=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--help" (
  goto show_help
)
if "%~1"=="/?" (
  goto show_help
)
shift
goto parse_args

:done_parsing

REM Check if Python is available (use venv python if present)
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo Error: Python not found. Please install Python 3.9+ or create the virtual environment
  exit /b 1
)

REM (Optional) Activate virtual environment for interactive sessions; we still prefer running the venv python directly
if "%USE_VENV%"=="true" (
  if exist "%VENV_ACTIVATE%" (
    echo Activating Python virtual environment: %VENV_DIR%
    call "%VENV_ACTIVATE%"
  ) else (
    echo Warning: Virtual environment not found at %VENV_DIR%
    echo Tip: Create venv with: python -m venv %VENV_DIR%
    echo Tip: Or set VENV_DIR to another location
    echo Continuing (will attempt to use %PYTHON_CMD%)...
  )
)

REM Check if uvicorn is installed using the selected Python interpreter
%PYTHON_CMD% -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Error: uvicorn not installed in %PYTHON_CMD%. Install with: %PYTHON_CMD% -m pip install uvicorn
  exit /b 1
)

REM Check if config file exists
if not exist "%CONFIG_FILE%" (
  echo Warning: Config file '%CONFIG_FILE%' not found. Using defaults.
)

REM Set environment variables
if not defined OLLAMA_URL set "OLLAMA_URL=http://127.0.0.1:11434"
if not defined NGINX_WHITELIST set "NGINX_WHITELIST="
if not defined ENABLE_INPUT_GUARD set "ENABLE_INPUT_GUARD="
if not defined ENABLE_OUTPUT_GUARD set "ENABLE_OUTPUT_GUARD="
if not defined ENABLE_IP_FILTER set "ENABLE_IP_FILTER="
if not defined IP_WHITELIST set "IP_WHITELIST="
if not defined IP_BLACKLIST set "IP_BLACKLIST="
set "PROXY_PORT=%PORT%"
set "CONFIG_FILE=%CONFIG_FILE%"

REM Build uvicorn command to run via the selected Python interpreter (ensures venv packages are used)
set "UVICORN_CMD=%PYTHON_CMD% -m uvicorn %PROXY_MODULE%"
set "UVICORN_CMD=!UVICORN_CMD! --host %HOST%"
set "UVICORN_CMD=!UVICORN_CMD! --port %PORT%"
set "UVICORN_CMD=!UVICORN_CMD! --workers %WORKERS%"
set "UVICORN_CMD=!UVICORN_CMD! --log-level %LOG_LEVEL%"

REM Add reload flag for development
if "%RELOAD%"=="true" (
  set "UVICORN_CMD=!UVICORN_CMD! --reload"
)

REM Display startup information
cls
echo.
echo ════════════════════════════════════════════════════════════════
echo          Ollama Guard Proxy - Uvicorn Server
echo ════════════════════════════════════════════════════════════════
echo Server Configuration:
echo   Host:       %HOST%
echo   Port:       %PORT%
echo   Workers:    %WORKERS%
echo Python Environment:
if "%USE_VENV%"=="true" (
  if exist "%VENV_ACTIVATE%" (
    echo   Venv:       %VENV_DIR% (ACTIVE)
  ) else (
    echo   Venv:       %VENV_DIR% (NOT FOUND - using system Python)
  )
) else (
  echo   Venv:       DISABLED (using system Python)
)
echo Runtime Settings:
echo   Concurrency:     %CONCURRENCY% per worker
echo   Log Level:       %LOG_LEVEL%
echo   Reload:          %RELOAD%
echo   Config File:     %CONFIG_FILE%
echo ════════════════════════════════════════════════════════════════
echo Environment Variables:
echo   OLLAMA_URL:              %OLLAMA_URL%
if "%NGINX_WHITELIST%"=="" (
  echo   NGINX_WHITELIST:         empty (unrestricted^)
) else (
  echo   NGINX_WHITELIST:         %NGINX_WHITELIST%
)
if "%ENABLE_INPUT_GUARD%"=="" (
  echo   ENABLE_INPUT_GUARD:      not set
) else (
  echo   ENABLE_INPUT_GUARD:      %ENABLE_INPUT_GUARD%
)
if "%ENABLE_OUTPUT_GUARD%"=="" (
  echo   ENABLE_OUTPUT_GUARD:     not set
) else (
  echo   ENABLE_OUTPUT_GUARD:     %ENABLE_OUTPUT_GUARD%
)
if "%ENABLE_IP_FILTER%"=="" (
  echo   ENABLE_IP_FILTER:        not set
) else (
  echo   ENABLE_IP_FILTER:        %ENABLE_IP_FILTER%
)
if "%IP_WHITELIST%"=="" (
  echo   IP_WHITELIST:            not set
) else (
  echo   IP_WHITELIST:            %IP_WHITELIST%
)
if "%IP_BLACKLIST%"=="" (
  echo   IP_BLACKLIST:            not set
) else (
  echo   IP_BLACKLIST:            %IP_BLACKLIST%
)
echo ════════════════════════════════════════════════════════════════
echo Testing proxy:
echo   curl http://%HOST%:%PORT%/health
echo Generating:
echo   curl -X POST http://%HOST%:%PORT%/v1/generate ^
echo     -d "{\"model\":\"mistral\",\"prompt\":\"test\"}"
echo ════════════════════════════════════════════════════════════════
echo.
echo Starting server: %UVICORN_CMD%
echo.

REM Run Uvicorn with configuration
%UVICORN_CMD%

goto end

:show_help
cls
echo Usage: run_proxy.bat [OPTIONS]
echo.
echo Options:
echo   --host HOST              Server bind address (default: 0.0.0.0)
echo   --port PORT              Server port (default: 8080)
echo   --workers N              Number of worker processes (default: 4)
echo   --concurrency N          Concurrent requests per worker (default: 128)
echo   --log-level LEVEL        Logging level: debug, info, warning, error
echo   --reload                 Auto-reload on code changes (development only)
echo   --debug                  Enable debug logging
echo   --config FILE            Config file path (default: config.yaml)
echo   --help                   Show this help message
echo.
echo Examples:
echo   REM Development with auto-reload
echo   run_proxy.bat --reload --debug
echo.
echo   REM Production with 8 workers for parallel processing
echo   run_proxy.bat --workers 8 --concurrency 256
echo.
echo   REM Listen on specific interface
echo   run_proxy.bat --host 127.0.0.1 --port 8080
echo.
echo Setup Python Virtual Environment:
echo   python -m venv venv
echo   call venv\Scripts\activate.bat
echo   pip install -r requirements.txt
echo   run_proxy.bat
echo.
echo Environment Variables:
echo   OLLAMA_URL               Ollama backend URL
echo   NGINX_WHITELIST          Comma-separated IPs/CIDR for Nginx access
echo   ENABLE_INPUT_GUARD       true/false
echo   ENABLE_OUTPUT_GUARD      true/false
echo   ENABLE_IP_FILTER         true/false
echo   IP_WHITELIST             Comma-separated IPs
echo   IP_BLACKLIST             Comma-separated IPs
echo   CONFIG_FILE              Configuration file path
echo   VENV_DIR                 Python virtual environment directory (default: venv)
echo   USE_VENV                 true/false - Enable/disable venv activation (default: true)
echo.
goto end

:end
endlocal
