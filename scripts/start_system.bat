@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "FRONTEND_PUBLIC_DIR=%FRONTEND_DIR%\public"
set "RUNTIME_ACCESS_FILE=%FRONTEND_PUBLIC_DIR%\runtime-access.json"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"
set "DB_FILE=%BACKEND_DIR%\training.db"
set "NEED_INIT=0"
set "INIT_REASON="
set "LAN_IP="
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

call :write_runtime_access
if errorlevel 1 (
  echo [ERROR] Failed to generate runtime access config.
  pause
  exit /b 1
)

echo [1/4] Start backend window...
start "Training Platform Backend" cmd /k call "%ROOT_DIR%\scripts\start_backend.bat"

echo [2/4] Start frontend window...
start "Training Platform Frontend" cmd /k call "%ROOT_DIR%\scripts\start_frontend.bat"

echo [3/4] Wait for services...
timeout /t 8 /nobreak >nul

echo [4/4] Open browser...
start "" "http://127.0.0.1:%FRONTEND_PORT%"

echo.
echo Local URLs:
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo Backend : http://127.0.0.1:%BACKEND_PORT%
echo.
echo iPad access:
if defined LAN_IP (
  echo Use http://%LAN_IP%:%FRONTEND_PORT% on the same Wi-Fi network.
) else (
  echo No recommended LAN IPv4 was detected. The page will fall back to the current local address.
)
echo.
echo Current IPv4 addresses:
ipconfig | findstr /R /C:"IPv4"
echo.
pause
exit /b 0

:write_runtime_access
if not exist "%FRONTEND_PUBLIC_DIR%" mkdir "%FRONTEND_PUBLIC_DIR%"

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | Where-Object { $_.NextHop -ne '0.0.0.0' } | Sort-Object RouteMetric, InterfaceMetric | Select-Object -First 1; if ($route) { $ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Sort-Object SkipAsSource | Select-Object -First 1 -ExpandProperty IPAddress; if ($ip) { $ip } }"`) do (
  set "LAN_IP=%%I"
)

set "ACCESS_HOST=%LAN_IP%"
set "ACCESS_SOURCE=startup-script"
if not defined ACCESS_HOST (
  set "ACCESS_HOST=127.0.0.1"
  set "ACCESS_SOURCE=fallback"
)

powershell -NoProfile -Command ^
  "$payload = [ordered]@{ accessUrl = 'http://%ACCESS_HOST%:%FRONTEND_PORT%'; host = '%ACCESS_HOST%'; port = %FRONTEND_PORT%; generatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'); source = '%ACCESS_SOURCE%' }; $json = $payload | ConvertTo-Json; Set-Content -Path '%RUNTIME_ACCESS_FILE%' -Value $json -Encoding UTF8"
if errorlevel 1 exit /b 1
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
