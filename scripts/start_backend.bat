@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"

call :check_venv
if /i not "!VENV_STATUS!"=="healthy" (
  echo [ERROR] !VENV_REASON!
  echo [ERROR] Please run scripts\init_system.bat to rebuild backend\.venv for this computer.
  pause
  exit /b 1
)

pushd "%BACKEND_DIR%"
set "PYTHONPATH=%BACKEND_DIR%"
echo [BACKEND] Starting FastAPI at http://127.0.0.1:8000
"%VENV_PYTHON%" -m uvicorn app.main:app --app-dir "%BACKEND_DIR%" --reload --host 0.0.0.0 --port 8000
popd
exit /b 0

:check_venv
set "VENV_STATUS=healthy"
set "VENV_REASON="

if not exist "%VENV_DIR%" (
  set "VENV_STATUS=missing"
  set "VENV_REASON=Backend virtual environment was not found."
  exit /b 0
)

if not exist "%VENV_PYTHON%" (
  set "VENV_STATUS=broken"
  set "VENV_REASON=Backend virtual environment is missing Scripts\python.exe."
  exit /b 0
)

if not exist "%VENV_CFG%" (
  set "VENV_STATUS=broken"
  set "VENV_REASON=Backend virtual environment is missing pyvenv.cfg."
  exit /b 0
)

findstr /C:"version = 3.12" "%VENV_CFG%" >nul 2>nul
if errorlevel 1 (
  set "VENV_STATUS=broken"
  set "VENV_REASON=Backend virtual environment is not using Python 3.12."
  exit /b 0
)

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 (
  set "VENV_STATUS=broken"
  set "VENV_REASON=Backend virtual environment is not executable on this computer. It may have been copied from another machine."
  exit /b 0
)

exit /b 0
