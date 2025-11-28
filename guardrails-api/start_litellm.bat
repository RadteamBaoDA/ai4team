@echo off
REM LiteLLM Proxy with LLM Guard Integration - Start Script (Windows)
REM 
REM This script starts the LiteLLM proxy with LLM Guard API integration.
REM Reference: https://protectai.github.io/llm-guard/tutorials/litellm/

setlocal enabledelayedexpansion

REM Configuration
set SCRIPT_DIR=%~dp0
set CONFIG_FILE=%SCRIPT_DIR%litellm_llmguard_config.yaml
set LITELLM_PORT=4000

REM LLM Guard API settings
if not defined LLM_GUARD_API_BASE set LLM_GUARD_API_BASE=http://localhost:8000

REM Ollama settings
if not defined OLLAMA_API_BASE set OLLAMA_API_BASE=http://192.168.1.2:11434
if not defined OLLAMA_API_BASE_2 set OLLAMA_API_BASE_2=http://192.168.1.11:11434
if not defined OLLAMA_API_BASE_3 set OLLAMA_API_BASE_3=http://192.168.1.20:11434

REM Master key for LiteLLM admin
if not defined LITELLM_MASTER_KEY set LITELLM_MASTER_KEY=sk-litellm-master-key

echo ============================================
echo LiteLLM Proxy with LLM Guard Integration
echo ============================================
echo.
echo Configuration:
echo   Config File:       %CONFIG_FILE%
echo   LiteLLM Port:      %LITELLM_PORT%
echo   LLM Guard API:     %LLM_GUARD_API_BASE%
echo   Ollama (Primary):  %OLLAMA_API_BASE%
echo   Ollama (Secondary): %OLLAMA_API_BASE_2%
echo.

REM Check if LLM Guard API is running
echo Checking LLM Guard API...
curl -sf "%LLM_GUARD_API_BASE%/healthz" >nul 2>&1
if %errorlevel% equ 0 (
    echo √ LLM Guard API is healthy
) else (
    echo ⚠ Warning: LLM Guard API is not responding at %LLM_GUARD_API_BASE%
    echo   Make sure to start it: docker-compose up -d
    echo.
    set /p CONTINUE="Continue anyway? (y/n) "
    if /i not "!CONTINUE!"=="y" exit /b 1
)

REM Check if litellm is installed
where litellm >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: litellm not found. Install it with:
    echo   pip install 'litellm[proxy]'
    exit /b 1
)

REM Start LiteLLM Proxy
echo.
echo Starting LiteLLM Proxy...
echo   API: http://localhost:%LITELLM_PORT%
echo   Docs: http://localhost:%LITELLM_PORT%/docs
echo.

litellm --config "%CONFIG_FILE%" --port %LITELLM_PORT% --detailed_debug
