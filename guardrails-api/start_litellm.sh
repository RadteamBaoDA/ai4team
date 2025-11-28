#!/bin/bash
# LiteLLM Proxy with LLM Guard Integration - Start Script
# 
# This script starts the LiteLLM proxy with LLM Guard API integration.
# Reference: https://protectai.github.io/llm-guard/tutorials/litellm/

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/litellm_llmguard_config.yaml}"
LITELLM_PORT="${LITELLM_PORT:-4000}"

# LLM Guard API settings
export LLM_GUARD_API_BASE="${LLM_GUARD_API_BASE:-http://localhost:8000}"

# Ollama settings
export OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://192.168.1.2:11434}"
export OLLAMA_API_BASE_2="${OLLAMA_API_BASE_2:-http://192.168.1.11:11434}"
export OLLAMA_API_BASE_3="${OLLAMA_API_BASE_3:-http://192.168.1.20:11434}"

# Master key for LiteLLM admin
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-litellm-master-key}"

echo "============================================"
echo "LiteLLM Proxy with LLM Guard Integration"
echo "============================================"
echo ""
echo "Configuration:"
echo "  Config File:       $CONFIG_FILE"
echo "  LiteLLM Port:      $LITELLM_PORT"
echo "  LLM Guard API:     $LLM_GUARD_API_BASE"
echo "  Ollama (Primary):  $OLLAMA_API_BASE"
echo "  Ollama (Secondary): $OLLAMA_API_BASE_2"
echo "  Master Key:        ${LITELLM_MASTER_KEY:0:10}..."
echo ""

# Check if LLM Guard API is running
echo "Checking LLM Guard API..."
if curl -sf "$LLM_GUARD_API_BASE/healthz" > /dev/null 2>&1; then
    echo "✓ LLM Guard API is healthy"
else
    echo "⚠ Warning: LLM Guard API is not responding at $LLM_GUARD_API_BASE"
    echo "  Make sure to start it: docker-compose up -d"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if litellm is installed
if ! command -v litellm &> /dev/null; then
    echo "Error: litellm not found. Install it with:"
    echo "  pip install 'litellm[proxy]'"
    exit 1
fi

# Start LiteLLM Proxy
echo ""
echo "Starting LiteLLM Proxy..."
echo "  API: http://localhost:$LITELLM_PORT"
echo "  Docs: http://localhost:$LITELLM_PORT/docs"
echo ""

litellm --config "$CONFIG_FILE" --port "$LITELLM_PORT" --detailed_debug
