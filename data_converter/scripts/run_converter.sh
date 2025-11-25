#!/bin/bash
# Quick start script for Linux/macOS
# Usage: ./run_converter.sh [input_folder] [output_folder]
#
# Environment Variables:
#   CONVERT_EXCEL_FILES - Set to "true" to convert Excel files to PDF (default: "false" = copy)
#   CONVERT_CSV_FILES   - Set to "true" to convert CSV files to PDF (default: "false" = copy)
#
# Examples:
#   ./run_converter.sh                    (uses default ./input and ./output, copies Excel/CSV)
#   ./run_converter.sh ~/Documents        (custom input, default output)
#   ./run_converter.sh ~/Documents ~/PDFs (custom input and output)
#   
#   export CONVERT_EXCEL_FILES=true
#   export CONVERT_CSV_FILES=true
#   ./run_converter.sh                    (convert Excel and CSV files to PDF)

echo "========================================"
echo "Document to PDF Converter v2.3"
echo "========================================"
echo

# Display environment settings
if [ "$CONVERT_EXCEL_FILES" = "true" ]; then
    echo "[CONFIG] Excel files: CONVERT to PDF"
else
    echo "[CONFIG] Excel files: COPY as-is (default)"
fi

if [ "$CONVERT_CSV_FILES" = "true" ]; then
    echo "[CONFIG] CSV files: CONVERT to PDF"
else
    echo "[CONFIG] CSV files: COPY as-is (default)"
fi
echo

# Check if virtual environment Python exists
if [ ! -f "../.venv/bin/python" ] && [ ! -f "../.venv/Scripts/python.exe" ]; then
    echo "[ERROR] Virtual environment not found"
    echo "Please run install.sh first"
    exit 1
fi

# Determine Python path
if [ -f "../.venv/bin/python" ]; then
    PYTHON_PATH="../.venv/bin/python"
else
    PYTHON_PATH="../.venv/Scripts/python.exe"
fi

# Run the converter with appropriate arguments
if [ -z "$1" ]; then
    # No arguments - use defaults
    $PYTHON_PATH main.py
elif [ -z "$2" ]; then
    # Only input folder specified
    $PYTHON_PATH main.py "$1"
else
    # Both folders specified
    $PYTHON_PATH main.py "$1" "$2"
fi

echo
echo "========================================"
echo "Conversion complete!"
echo "========================================"
