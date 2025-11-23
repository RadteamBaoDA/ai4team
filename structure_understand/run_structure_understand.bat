@echo off
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
if "%~1"=="" (
  set "CONFIG=%SCRIPT_DIR%config.yaml"
) else (
  set "CONFIG=%~1"
)
endlocal & set "CONFIG=%CONFIG%"
if defined PYTHON_EXE (
  set "PY_CMD=%PYTHON_EXE%"
) else (
  set "PY_CMD=python"
)
"%PY_CMD%" "%~dp0app.py" --config "%CONFIG%"
