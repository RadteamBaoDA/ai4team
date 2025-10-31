@echo off
REM Setup script for Ollama Guard Proxy with Concurrent Request Handling

echo =========================================
echo Ollama Guard Proxy - Concurrency Setup
echo =========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.11+
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python version: %PYTHON_VERSION%

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo [OK] Dependencies installed
echo.

REM Check configuration
if not exist "config.yaml" (
    echo [WARNING] config.yaml not found
    echo   Please create config.yaml with concurrency settings
    echo.
    echo   Example:
    echo     ollama_num_parallel: "auto"
    echo     ollama_max_queue: 512
    echo     request_timeout: 300
    echo.
) else (
    echo [OK] Configuration file found
    
    REM Check if concurrency settings exist
    findstr /C:"ollama_num_parallel" config.yaml >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Adding concurrency settings to config.yaml...
        echo. >> config.yaml
        echo # Concurrency Configuration (Added by setup^) >> config.yaml
        echo ollama_num_parallel: "auto" >> config.yaml
        echo ollama_max_queue: 512 >> config.yaml
        echo request_timeout: 300 >> config.yaml
        echo enable_queue_stats: true >> config.yaml
        echo [OK] Concurrency settings added
    ) else (
        echo [OK] Concurrency settings found in config.yaml
    )
)

echo.
echo =========================================
echo Setup Complete!
echo =========================================
echo.
echo Next steps:
echo   1. Review config.yaml for concurrency settings
echo   2. Start the proxy: run_proxy.bat
echo   3. Check health: curl http://localhost:8080/health
echo   4. Monitor queues: curl http://localhost:8080/queue/stats
echo.
echo Documentation:
echo   - Concurrency Guide: docs\CONCURRENCY_GUIDE.md
echo   - Quick Reference: docs\CONCURRENCY_QUICKREF.md
echo   - Update Summary: CONCURRENCY_UPDATE.md
echo.
pause
