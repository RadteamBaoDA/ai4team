@echo off
REM Initialize tiktoken offline mode with local cache (Windows)
REM Usage: init_tiktoken.bat [cache_dir] [encodings...]
REM Example: init_tiktoken.bat models\tiktoken cl100k_base p50k_base

setlocal enabledelayedexpansion

REM Default cache directory
set "CACHE_DIR=%1"
if "!CACHE_DIR!"=="" set "CACHE_DIR=models\tiktoken"

REM Get absolute path
for /f "tokens=*" %%i in ('cd /d "!CACHE_DIR!" 2^>nul ^&^& cd') do set "CACHE_DIR=%%i"
if not exist "!CACHE_DIR!" (
    for /f "tokens=*" %%i in ('cd') do set "CACHE_DIR=%%i\!CACHE_DIR!"
)

echo ========================================
echo Tiktoken Offline Mode Setup
echo ========================================
echo.

echo Configuration:
echo   Cache Directory: !CACHE_DIR!
echo.

REM Create cache directory
echo Creating cache directory...
if not exist "!CACHE_DIR!" mkdir "!CACHE_DIR!"
echo OK
echo.

REM Set environment variables
set "TIKTOKEN_CACHE_DIR=!CACHE_DIR!"
set "TIKTOKEN_OFFLINE_MODE=true"
set "TIKTOKEN_FALLBACK_LOCAL=true"

echo Downloading tiktoken encodings...
echo Default encodings: cl100k_base p50k_base p50k_edit r50k_base
echo.

REM Download using Python CLI
python -m ollama_guardrails tiktoken-download -d "!CACHE_DIR!" -e cl100k_base p50k_base p50k_edit r50k_base

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Verifying cache...
    python -m ollama_guardrails tiktoken-info
    
    echo.
    echo ========================================
    echo Setup Complete!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Set environment variable (optional^):
    echo    set TIKTOKEN_CACHE_DIR=!CACHE_DIR!
    echo.
    echo 2. Start the server:
    echo    python -m ollama_guardrails server
    echo.
) else (
    echo.
    echo ERROR: Setup failed
    exit /b 1
)

endlocal
