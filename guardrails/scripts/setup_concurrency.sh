#!/bin/bash
# Setup script for Ollama Guard Proxy with Concurrent Request Handling

set -e

echo "========================================="
echo "Ollama Guard Proxy - Concurrency Setup"
echo "========================================="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "✓ Dependencies installed"
echo

# Check configuration
if [ ! -f "config.yaml" ]; then
    echo "⚠ Warning: config.yaml not found"
    echo "  Please create config.yaml with concurrency settings"
    echo
    echo "  Example:"
    echo "    ollama_num_parallel: \"auto\""
    echo "    ollama_max_queue: 512"
    echo "    request_timeout: 300"
    echo
else
    echo "✓ Configuration file found"
    
    # Check if concurrency settings exist
    if grep -q "ollama_num_parallel" config.yaml; then
        echo "✓ Concurrency settings found in config.yaml"
    else
        echo "⚠ Adding concurrency settings to config.yaml..."
        cat >> config.yaml << EOF

# Concurrency Configuration (Added by setup)
ollama_num_parallel: "auto"
ollama_max_queue: 512
request_timeout: 300
enable_queue_stats: true
EOF
        echo "✓ Concurrency settings added"
    fi
fi

echo
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo
echo "Next steps:"
echo "  1. Review config.yaml for concurrency settings"
echo "  2. Start the proxy: ./run_proxy.sh start"
echo "  3. Check health: curl http://localhost:8080/health"
echo "  4. Monitor queues: curl http://localhost:8080/queue/stats"
echo
echo "Documentation:"
echo "  - Concurrency Guide: docs/CONCURRENCY_GUIDE.md"
echo "  - Quick Reference: docs/CONCURRENCY_QUICKREF.md"
echo "  - Update Summary: CONCURRENCY_UPDATE.md"
echo
