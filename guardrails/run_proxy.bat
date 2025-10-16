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
REM Features:
REM   - Uvicorn ASGI server
REM   - Multi-worker support for parallel requests
REM   - Configurable concurrency per worker
REM   - Environment variable support
REM   - Health check endpoint
REM   - Request logging

setlocal enabledelayedexpansion

REM Default configuration
set "HOST=0.0.0.0"
set "PORT=8080"
set "WORKERS=4"
set "CONCURRENCY=128"
set "LOG_LEVEL=info"
set "RELOAD=false"
set "CONFIG_FILE=config.yaml"
set "PROXY_MODULE=ollama_guard_proxy:app"

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

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
  echo Error: Python not found. Please install Python 3.9+
  exit /b 1
)

REM Check if uvicorn is installed
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Error: uvicorn not installed. Install with: pip install uvicorn
  exit /b 1
)

REM Check if config file exists
if not exist "%CONFIG_FILE%" (
  echo Warning: Config file '%CONFIG_FILE%' not found. Using defaults.
)

REM Set environment variables
if not defined OLLAMA_URL set "OLLAMA_URL=http://127.0.0.1:11434"
set "PROXY_PORT=%PORT%"
set "CONFIG_FILE=%CONFIG_FILE%"

REM Build uvicorn command
set "UVICORN_CMD=uvicorn %PROXY_MODULE%"
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
echo Server:        %HOST%:%PORT%
echo Workers:       %WORKERS% (for parallel request handling)
echo Concurrency:   %CONCURRENCY% per worker
echo Log Level:     %LOG_LEVEL%
echo Reload:        %RELOAD%
echo Config:        %CONFIG_FILE%
echo Ollama URL:    %OLLAMA_URL%
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
echo Environment Variables:
echo   OLLAMA_URL               Ollama backend URL
echo   PROXY_PORT               Proxy port
echo   ENABLE_INPUT_GUARD       true/false
echo   ENABLE_OUTPUT_GUARD      true/false
echo   ENABLE_IP_FILTER         true/false
echo   IP_WHITELIST             Comma-separated IPs
echo   IP_BLACKLIST             Comma-separated IPs
echo   CONFIG_FILE              Configuration file path
echo.
goto end

:end
endlocal
