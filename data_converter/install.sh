#!/bin/bash
# Installation script for Document Converter
# Linux/macOS

echo "========================================"
echo "Document Converter - Installation"
echo "========================================"
echo

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3"
    exit 1
fi

echo "[OK] Python found"
python3 --version
echo

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip3 is not installed"
    echo "Please install pip3"
    exit 1
fi

echo "[OK] pip found"
echo

# Install requirements
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo
echo "To convert documents, run:"
echo "  python3 main.py <input_folder> <output_folder>"
echo
echo "For best results, install LibreOffice:"
echo "  Linux:  sudo apt-get install libreoffice"
echo "  macOS:  brew install libreoffice"
echo

# Make script executable
chmod +x main.py 2>/dev/null
