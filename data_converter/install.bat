@echo off
REM Installation script for Document Converter
REM Windows batch file

echo ========================================
echo Document Converter - Installation
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed
    echo Please install pip
    pause
    exit /b 1
)

echo [OK] pip found
echo.

REM Install requirements
echo Installing Python dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To convert documents, run:
echo   python main.py ^<input_folder^> ^<output_folder^>
echo.
echo For best results, install LibreOffice:
echo   https://www.libreoffice.org/download/download/
echo.

pause
