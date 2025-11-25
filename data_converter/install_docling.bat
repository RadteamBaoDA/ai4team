@echo off
REM install_docling.bat - Install Docling for advanced layout recognition

echo ============================================================
echo   Docling Installation Script
echo ============================================================
echo.
echo This script will install Docling and its dependencies for
echo enhanced Excel table layout recognition.
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found
    echo.
    echo Please install Python 3.10 or higher first.
    pause
    exit /b 1
)

echo Checking Python version...
python --version
echo.

REM Install Docling
echo Installing Docling...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python -m pip install docling

if %errorlevel% neq 0 (
    echo.
    echo Installation failed
    echo.
    echo Try manual installation:
    echo   pip install docling
    pause
    exit /b 1
)

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo Docling installed successfully!
echo.

REM Verify installation
echo Verifying installation...
python -c "import docling; print(f'Docling version: {docling.__version__}')" 2>&1

if %errorlevel% equ 0 (
    echo.
    echo Installation verified!
) else (
    echo.
    echo Installation completed but verification failed
    echo Try restarting your terminal or IDE
)

echo.
echo ============================================================
echo   Next Steps
echo ============================================================
echo.
echo 1. Enable Docling converter:
echo    set USE_DOCLING_CONVERTER=true
echo    set DOCLING_PRIORITY=2
echo.
echo 2. Test installation:
echo    python test_docling.py
echo.
echo 3. Generate test Excel files:
echo    python generate_test_excel.py
echo.
echo 4. Convert documents:
echo    python main.py ./input ./output
echo.
echo For more information, see:
echo   docs\DOCLING_INTEGRATION.md
echo   docs\DOCLING_IMPLEMENTATION_SUMMARY.md
echo.
echo ============================================================
pause
