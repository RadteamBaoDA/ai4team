@echo off
REM Initialize tiktoken and Hugging Face offline modes with local cache (Windows)
REM Usage: init_all_offline.bat [cache_dir] [options]
REM Example: init_all_offline.bat models --models bert-base-uncased

setlocal enabledelayedexpansion

REM Default cache directory
set "CACHE_BASE=%1"
if "!CACHE_BASE!"=="" set "CACHE_BASE=models"

REM Get absolute path
for /f "tokens=*" %%i in ('cd /d "!CACHE_BASE!" 2^>nul ^&^& cd') do set "CACHE_BASE=%%i"
if not exist "!CACHE_BASE!" (
    for /f "tokens=*" %%i in ('cd') do set "CACHE_BASE=%%i\!CACHE_BASE!"
)

REM Parse additional arguments
set "SKIP_TIKTOKEN=0"
set "SKIP_HF=0"
set "HF_MODELS="

:parse_args
if "!%2!"=="" goto end_parse
if "!%2!"=="--skip-tiktoken" set "SKIP_TIKTOKEN=1"
if "!%2!"=="--skip-hf" set "SKIP_HF=1"
if "!%2!"=="--models" (
    set "HF_MODELS=!%3!"
    shift
)
shift
goto parse_args

:end_parse

echo ========================================
echo Offline Mode Setup - Tiktoken + HF
echo ========================================
echo.

echo Configuration:
echo   Base Directory: !CACHE_BASE!
if !SKIP_TIKTOKEN! EQU 0 (
    echo   Tiktoken Encodings: cl100k_base p50k_base p50k_edit r50k_base
)
if !SKIP_HF! EQU 0 (
    if "!HF_MODELS!"=="" (
        echo   HF Models: (none specified, cache will be initialized^)
    ) else (
        echo   HF Models: !HF_MODELS!
    )
)
echo.

REM Create directories
echo Creating directories...
if not exist "!CACHE_BASE!" mkdir "!CACHE_BASE!"
if !SKIP_TIKTOKEN! EQU 0 if not exist "!CACHE_BASE!\tiktoken" mkdir "!CACHE_BASE!\tiktoken"
if !SKIP_HF! EQU 0 if not exist "!CACHE_BASE!\huggingface" mkdir "!CACHE_BASE!\huggingface"
echo OK
echo.

REM Setup Tiktoken
if !SKIP_TIKTOKEN! EQU 0 (
    set "TIKTOKEN_CACHE=!CACHE_BASE!\tiktoken"
    
    echo Setting up Tiktoken Offline Mode
    echo   Cache: !TIKTOKEN_CACHE!
    echo.
    
    REM Set environment variables
    set "TIKTOKEN_CACHE_DIR=!TIKTOKEN_CACHE!"
    set "TIKTOKEN_OFFLINE_MODE=true"
    set "TIKTOKEN_FALLBACK_LOCAL=true"
    
    echo Downloading tiktoken encodings...
    
    python -m ollama_guardrails tiktoken-download -d "!TIKTOKEN_CACHE!" -e cl100k_base p50k_base p50k_edit r50k_base
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ERROR: Failed to download tiktoken encodings
        exit /b 1
    )
    echo OK
    echo.
)

REM Setup Hugging Face
if !SKIP_HF! EQU 0 (
    set "HF_CACHE=!CACHE_BASE!\huggingface"
    
    echo Setting up Hugging Face Offline Mode
    echo   Cache: !HF_CACHE!
    echo.
    
    REM Set environment variables
    set "HF_HOME=!HF_CACHE!"
    set "HF_OFFLINE=true"
    set "TRANSFORMERS_OFFLINE=1"
    set "HF_DATASETS_OFFLINE=1"
    set "HF_HUB_OFFLINE=1"
    
    python -m ollama_guardrails hf-info
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ERROR: Failed to initialize Hugging Face offline mode
        exit /b 1
    )
    
    if not "!HF_MODELS!"=="" (
        echo.
        echo Downloading Hugging Face models: !HF_MODELS!
        
        python -m ollama_guardrails hf-download -d "!HF_CACHE!" -m !HF_MODELS!
        
        if %ERRORLEVEL% NEQ 0 (
            echo.
            echo ERROR: Failed to download Hugging Face models
            exit /b 1
        )
        echo OK
    )
    echo.
)

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Environment Variables (optional^):
if !SKIP_TIKTOKEN! EQU 0 (
    echo   set TIKTOKEN_CACHE_DIR=!CACHE_BASE!\tiktoken
)
if !SKIP_HF! EQU 0 (
    echo   set HF_HOME=!CACHE_BASE!\huggingface
    echo   set HF_OFFLINE=true
    echo   set TRANSFORMERS_OFFLINE=1
)
echo.
echo Start the server:
echo   python -m ollama_guardrails server
echo.

endlocal
