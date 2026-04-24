@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "RUNTIME_ACCESS_FILE=%FRONTEND_DIR%\public\runtime-access.json"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"
set "DB_FILE=%BACKEND_DIR%\training.db"
set "NEED_INIT=0"
set "INIT_REASON="
set "ACCESS_URL="
set "FRONTEND_URL=http://127.0.0.1:5173/"
set "FRONTEND_PORT=5173"
set "BACKEND_PORT=8000"

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

if exist "%RUNTIME_ACCESS_FILE%" del /q "%RUNTIME_ACCESS_FILE%" >nul 2>nul

echo [1/4] Start backend window...
start "Training Platform Backend" cmd /k call "%ROOT_DIR%\scripts\start_backend.bat"

echo [2/4] Start frontend window...
start "Training Platform Frontend" cmd /k call "%ROOT_DIR%\scripts\start_frontend.bat"

echo [3/4] Wait for services...
timeout /t 8 /nobreak >nul
call :read_runtime_access_url
if defined ACCESS_URL set "FRONTEND_URL=%ACCESS_URL%"

echo [4/4] Open browser...
start "" "%FRONTEND_URL%"

echo.
echo Access URLs:
echo Frontend: %FRONTEND_URL%
echo Backend : http://127.0.0.1:%BACKEND_PORT%
echo.
echo iPad access:
if defined ACCESS_URL (
  echo Use %ACCESS_URL% on the same Wi-Fi network.
) else (
  echo Runtime access URL is not ready yet. Use the Network address shown in the frontend window.
)
echo.
echo Current IPv4 addresses:
ipconfig | findstr /R /C:"IPv4"
echo.
pause
exit /b 0

:read_runtime_access_url
set "ACCESS_URL="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "if (Test-Path '%RUNTIME_ACCESS_FILE%') { try { $data = Get-Content '%RUNTIME_ACCESS_FILE%' -Raw | ConvertFrom-Json; if ($data.accessUrl) { $data.accessUrl } } catch {} }"`) do (
  set "ACCESS_URL=%%I"
)
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
