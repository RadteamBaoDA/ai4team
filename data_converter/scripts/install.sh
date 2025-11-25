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

# Check uv CLI
if ! command -v uv &> /dev/null; then
    echo "[ERROR] The uv package manager is not installed"
    echo "Install it from https://github.com/astral-sh/uv"
    echo "  macOS:  brew install uv"
    echo "  Linux:  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "[OK] uv found"
echo

VENV_PATH="../.venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment with uv..."
    if ! uv venv "$VENV_PATH"; then
        echo
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
else
    echo "[OK] Virtual environment found at $VENV_PATH"
fi

if [ -x "$VENV_PATH/bin/python" ]; then
    PYTHON_PATH="$VENV_PATH/bin/python"
elif [ -x "$VENV_PATH/Scripts/python.exe" ]; then
    PYTHON_PATH="$VENV_PATH/Scripts/python.exe"
else
    echo
    echo "[ERROR] Could not locate Python inside $VENV_PATH"
    echo "Try deleting the folder and run install.sh again"
    exit 1
fi

echo "Installing Python dependencies with uv..."
if ! uv pip install --python "$PYTHON_PATH" -r requirements.txt; then
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
