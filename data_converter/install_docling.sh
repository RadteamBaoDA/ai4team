#!/bin/bash
# install_docling.sh - Install Docling for advanced layout recognition

echo "============================================================"
echo "  Docling Installation Script"
echo "============================================================"
echo ""
echo "This script will install Docling and its dependencies for"
echo "enhanced Excel table layout recognition."
echo ""

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python not found"
    echo ""
    echo "Please install Python 3.10 or higher first."
    exit 1
fi

# Use python or python3
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo "Using: $PYTHON_CMD"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"
echo ""

# Install Docling
echo "Installing Docling..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON_CMD -m pip install docling

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Installation failed"
    echo ""
    echo "Try manual installation:"
    echo "  pip install docling"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Docling installed successfully!"
echo ""

# Verify installation
echo "Verifying installation..."
$PYTHON_CMD -c "import docling; print(f'Docling version: {docling.__version__}')" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Installation verified!"
else
    echo ""
    echo "⚠️  Installation completed but verification failed"
    echo "Try restarting your terminal or IDE"
fi

echo ""
echo "============================================================"
echo "  Next Steps"
echo "============================================================"
echo ""
echo "1. Enable Docling converter:"
echo "   export USE_DOCLING_CONVERTER=true"
echo "   export DOCLING_PRIORITY=2"
echo ""
echo "2. Test installation:"
echo "   python test_docling.py"
echo ""
echo "3. Generate test Excel files:"
echo "   python generate_test_excel.py"
echo ""
echo "4. Convert documents:"
echo "   python main.py ./input ./output"
echo ""
echo "For more information, see:"
echo "  docs/DOCLING_INTEGRATION.md"
echo "  docs/DOCLING_IMPLEMENTATION_SUMMARY.md"
echo ""
echo "============================================================"
