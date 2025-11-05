#!/bin/bash
# Initialize tiktoken offline mode with local cache
# Usage: ./init_tiktoken.sh [cache_dir] [encodings...]
# Example: ./init_tiktoken.sh ./models/tiktoken cl100k_base p50k_base

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
CACHE_DIR="${1:-./models/tiktoken}"
ENCODINGS=("${@:2}")

# If no encodings specified, use defaults
if [ ${#ENCODINGS[@]} -eq 0 ]; then
    ENCODINGS=("cl100k_base" "p50k_base" "p50k_edit" "r50k_base")
fi

echo "========================================"
echo -e "${BLUE}Tiktoken Offline Mode Setup${NC}"
echo "========================================"
echo ""

# Make cache directory absolute
CACHE_DIR="$(cd "$(dirname "$CACHE_DIR")" 2>/dev/null && pwd)/$(basename "$CACHE_DIR")" || CACHE_DIR="$(pwd)/$CACHE_DIR"

echo -e "${BLUE}Configuration:${NC}"
echo "  Cache Directory: $CACHE_DIR"
echo "  Encodings: ${ENCODINGS[*]}"
echo ""

# Create cache directory
echo -e "${BLUE}Creating cache directory...${NC}"
mkdir -p "$CACHE_DIR"
echo -e "${GREEN}✓${NC} Directory created"
echo ""

# Set environment variable
export TIKTOKEN_CACHE_DIR="$CACHE_DIR"
export TIKTOKEN_OFFLINE_MODE=true
export TIKTOKEN_FALLBACK_LOCAL=true

# Download encodings using Python CLI
echo -e "${BLUE}Downloading encodings...${NC}"
ENCODING_ARGS=""
for encoding in "${ENCODINGS[@]}"; do
    ENCODING_ARGS="$ENCODING_ARGS $encoding"
done

if python -m ollama_guardrails tiktoken-download -d "$CACHE_DIR" -e $ENCODING_ARGS; then
    echo ""
    echo -e "${BLUE}Verifying cache...${NC}"
    python -m ollama_guardrails tiktoken-info
    
    echo ""
    echo "========================================"
    echo -e "${GREEN}Setup Complete!${NC}"
    echo "========================================"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Set environment variable (optional):"
    echo "   ${YELLOW}export TIKTOKEN_CACHE_DIR=$CACHE_DIR${NC}"
    echo ""
    echo "2. Start the server:"
    echo "   ${YELLOW}python -m ollama_guardrails server${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Setup failed${NC}"
    exit 1
fi
