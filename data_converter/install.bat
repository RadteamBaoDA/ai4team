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

REM Check uv CLI
where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The uv package manager is not installed
    echo Download it from https://github.com/astral-sh/uv or install via:
    echo   winget install --id Astral.UV -e
    pause
    exit /b 1
)

echo [OK] uv found
echo.

set "VENV_PATH=..\.venv"
set "PYTHON_PATH=%VENV_PATH%\Scripts\python.exe"

if not exist "%VENV_PATH%" (
    echo Creating virtual environment with uv...
    uv venv "%VENV_PATH%"
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [OK] Virtual environment found at %VENV_PATH%
)

if not exist "%PYTHON_PATH%" (
    echo.
    echo [ERROR] Python executable not found in %VENV_PATH%
    echo Try deleting the folder and re-running install.bat
    pause
    exit /b 1
)

echo Installing Python dependencies with uv...
uv pip install --python "%PYTHON_PATH%" -r requirements.txt

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
