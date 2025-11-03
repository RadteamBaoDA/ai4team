@echo off
REM Quick start batch script for Windows
REM Usage: run_converter.bat [input_folder] [output_folder]
REM 
REM Environment Variables:
REM   CONVERT_EXCEL_FILES - Set to "true" to convert Excel files to PDF (default: "false" = copy)
REM   CONVERT_CSV_FILES   - Set to "true" to convert CSV files to PDF (default: "false" = copy)
REM
REM Examples:
REM   run_converter.bat                              (uses default ./input and ./output, copies Excel/CSV)
REM   run_converter.bat "C:\My Documents"            (custom input, default output)
REM   run_converter.bat "C:\My Documents" "C:\PDFs"  (custom input and output)
REM   
REM   set CONVERT_EXCEL_FILES=true
REM   set CONVERT_CSV_FILES=true
REM   run_converter.bat                              (convert Excel and CSV files to PDF)

echo ========================================
echo Document to PDF Converter v2.3
echo ========================================
echo.

REM Display environment settings
if "%CONVERT_EXCEL_FILES%"=="true" (
    echo [CONFIG] Excel files: CONVERT to PDF
) else (
    echo [CONFIG] Excel files: COPY as-is ^(default^)
)

if "%CONVERT_CSV_FILES%"=="true" (
    echo [CONFIG] CSV files: CONVERT to PDF
) else (
    echo [CONFIG] CSV files: COPY as-is ^(default^)
)
echo.

REM Check if virtual environment Python exists
if not exist "..\\.venv\\Scripts\\python.exe" (
    echo [ERROR] Virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Run the converter with appropriate arguments
if "%~1"=="" (
    REM No arguments - use defaults
    ..\.venv\Scripts\python.exe main.py
) else if "%~2"=="" (
    REM Only input folder specified
    ..\.venv\Scripts\python.exe main.py "%~1"
) else (
    REM Both folders specified
    ..\.venv\Scripts\python.exe main.py "%~1" "%~2"
)

echo.
echo ========================================
echo Conversion complete!
echo ========================================
pause
