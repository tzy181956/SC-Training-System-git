@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"
set "DB_FILE=%BACKEND_DIR%\training.db"
set "NEED_INIT=0"
set "INIT_REASON="

echo.
echo ======================================
echo   Training Platform V1 - Start System
echo ======================================
echo.

call :check_venv
if /i not "!VENV_STATUS!"=="healthy" (
  set "NEED_INIT=1"
  set "INIT_REASON=!VENV_REASON!"
)
if not exist "%FRONTEND_DIR%\node_modules" (
  set "NEED_INIT=1"
  if not defined INIT_REASON set "INIT_REASON=Frontend dependencies are missing."
)
if not exist "%DB_FILE%" (
  set "NEED_INIT=1"
  if not defined INIT_REASON set "INIT_REASON=Database file is missing."
)

if "%NEED_INIT%"=="1" (
  echo [INFO] Initialization is required before startup.
  if defined INIT_REASON echo [INFO] !INIT_REASON!
  echo [INFO] The system will run init_system.bat automatically.
  echo.
  call "%ROOT_DIR%\scripts\init_system.bat"
  if errorlevel 1 (
    echo.
    echo [ERROR] Initialization did not complete successfully.
    pause
    exit /b 1
  )
  echo.
  echo [INFO] Initialization finished. Continue startup...
  echo.
)

echo [1/4] Start backend window...
start "Training Platform Backend" cmd /k call "%ROOT_DIR%\scripts\start_backend.bat"

echo [2/4] Start frontend window...
start "Training Platform Frontend" cmd /k call "%ROOT_DIR%\scripts\start_frontend.bat"

echo [3/4] Wait for services...
timeout /t 8 /nobreak >nul

echo [4/4] Open browser...
start "" "http://127.0.0.1:5173"

echo.
echo Local URLs:
echo Frontend: http://127.0.0.1:5173
echo Backend : http://127.0.0.1:8000
echo.
echo iPad access:
echo Use http://YOUR-PC-IP:5173 on the same Wi-Fi network.
echo.
echo Current IPv4 addresses:
ipconfig | findstr /R /C:"IPv4"
echo.
pause
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
