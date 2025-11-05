#!/bin/bash
# Initialize tiktoken and Hugging Face offline modes with local cache
# Usage: ./init_tiktoken.sh [cache_dir] [options]
# Example: ./init_tiktoken.sh ./models --models bert-base-uncased

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
CACHE_DIR="${1:-./models}"
SKIP_TIKTOKEN=0
SKIP_HF=0
TT_ENCODINGS=("cl100k_base" "p50k_base" "p50k_edit" "r50k_base")
HF_MODELS=()

# Parse additional arguments
for arg in "${@:2}"; do
    case "$arg" in
        --skip-tiktoken) SKIP_TIKTOKEN=1 ;;
        --skip-hf) SKIP_HF=1 ;;
        --models) 
            shift
            while [[ $# -gt 0 ]] && [[ "$1" != --* ]]; do
                HF_MODELS+=("$1")
                shift
            done
            ;;
    esac
done

echo "========================================"
echo -e "${BLUE}Offline Mode Setup - Tiktoken + HF${NC}"
echo "========================================"
echo ""

# Make cache directory absolute
CACHE_DIR="$(cd "$(dirname "$CACHE_DIR")" 2>/dev/null && pwd)/$(basename "$CACHE_DIR")" || CACHE_DIR="$(pwd)/$CACHE_DIR"

echo -e "${BLUE}Configuration:${NC}"
echo "  Base Directory: $CACHE_DIR"
if [ $SKIP_TIKTOKEN -eq 0 ]; then
    echo "  Tiktoken Encodings: ${TT_ENCODINGS[*]}"
fi
if [ $SKIP_HF -eq 0 ]; then
    if [ ${#HF_MODELS[@]} -gt 0 ]; then
        echo "  HF Models: ${HF_MODELS[*]}"
    else
        echo "  HF Models: (none specified, cache will be initialized)"
    fi
fi
echo ""

# Create cache directory
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$CACHE_DIR"
if [ $SKIP_TIKTOKEN -eq 0 ]; then
    mkdir -p "$CACHE_DIR/tiktoken"
fi
if [ $SKIP_HF -eq 0 ]; then
    mkdir -p "$CACHE_DIR/huggingface"
fi
echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Setup Tiktoken
if [ $SKIP_TIKTOKEN -eq 0 ]; then
    TIKTOKEN_CACHE="$CACHE_DIR/tiktoken"
    
    echo -e "${BLUE}Setting up Tiktoken Offline Mode${NC}"
    echo "  Cache: $TIKTOKEN_CACHE"
    echo ""
    
    # Set environment variables
    export TIKTOKEN_CACHE_DIR="$TIKTOKEN_CACHE"
    export TIKTOKEN_OFFLINE_MODE=true
    export TIKTOKEN_FALLBACK_LOCAL=true
    
    echo -e "${BLUE}Downloading encodings...${NC}"
    ENCODING_ARGS=""
    for encoding in "${TT_ENCODINGS[@]}"; do
        ENCODING_ARGS="$ENCODING_ARGS $encoding"
    done
    
    if python -m ollama_guardrails tiktoken-download -d "$TIKTOKEN_CACHE" -e $ENCODING_ARGS; then
        echo -e "${GREEN}✓${NC} Tiktoken encodings downloaded"
    else
        echo -e "${RED}✗${NC} Failed to download tiktoken encodings"
        exit 1
    fi
    echo ""
fi

# Setup Hugging Face
if [ $SKIP_HF -eq 0 ]; then
    HF_CACHE="$CACHE_DIR/huggingface"
    
    echo -e "${BLUE}Setting up Hugging Face Offline Mode${NC}"
    echo "  Cache: $HF_CACHE"
    echo ""
    
    # Set environment variables
    export HF_HOME="$HF_CACHE"
    export HF_OFFLINE=true
    export TRANSFORMERS_OFFLINE=1
    export HF_DATASETS_OFFLINE=1
    export HF_HUB_OFFLINE=1
    
    if python -m ollama_guardrails hf-info; then
        echo -e "${GREEN}✓${NC} Hugging Face offline mode initialized"
    else
        echo -e "${RED}✗${NC} Failed to initialize Hugging Face offline mode"
        exit 1
    fi
    echo ""
    
    # Download models if specified
    if [ ${#HF_MODELS[@]} -gt 0 ]; then
        echo -e "${BLUE}Downloading Hugging Face models...${NC}"
        
        HF_MODEL_ARGS=""
        for model_id in "${HF_MODELS[@]}"; do
            HF_MODEL_ARGS="$HF_MODEL_ARGS $model_id"
        done
        
        if python -m ollama_guardrails hf-download -d "$HF_CACHE" -m $HF_MODEL_ARGS; then
            echo -e "${GREEN}✓${NC} Hugging Face models downloaded"
        else
            echo -e "${RED}✗${NC} Failed to download Hugging Face models"
            exit 1
        fi
    fi
    echo ""
fi

echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo -e "${BLUE}Environment Variables (optional):${NC}"
if [ $SKIP_TIKTOKEN -eq 0 ]; then
    echo "  ${YELLOW}export TIKTOKEN_CACHE_DIR=$CACHE_DIR/tiktoken${NC}"
fi
if [ $SKIP_HF -eq 0 ]; then
    echo "  ${YELLOW}export HF_HOME=$CACHE_DIR/huggingface${NC}"
    echo "  ${YELLOW}export HF_OFFLINE=true${NC}"
    echo "  ${YELLOW}export TRANSFORMERS_OFFLINE=1${NC}"
fi
echo ""
echo -e "${BLUE}Start the server:${NC}"
echo "  ${YELLOW}python -m ollama_guardrails server${NC}"
echo ""
