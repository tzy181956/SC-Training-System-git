@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"
set "RESOLVED_PYTHON="
set "PYTHON_VERSION="
set "VENV_STATUS=missing"
set "VENV_REASON="

echo.
echo ======================================
echo   Training Platform V1 - Init System
echo ======================================
echo.

call :resolve_python312
if errorlevel 1 (
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js was not found.
  echo Please install Node.js 18 or newer, then try again.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found.
  echo Please reinstall Node.js and make sure npm is included.
  pause
  exit /b 1
)

echo [1/6] Check Python virtual environment...
call :inspect_venv
if /i "!VENV_STATUS!"=="healthy" (
  echo Virtual environment is reusable on this computer.
) else (
  if exist "%VENV_DIR%" (
    echo [WARN] Existing backend\.venv is not usable on this computer.
    if defined VENV_REASON echo [WARN] !VENV_REASON!
    echo [INFO] Recreating backend\.venv with !RESOLVED_PYTHON! ...
    rmdir /s /q "%VENV_DIR%"
    if exist "%VENV_DIR%" (
      echo [ERROR] Failed to remove backend\.venv.
      pause
      exit /b 1
    )
  ) else (
    echo [INFO] backend\.venv was not found. A new virtual environment will be created.
  )

  pushd "%BACKEND_DIR%"
  call !RESOLVED_PYTHON! -m venv .venv
  if errorlevel 1 (
    popd
    echo [ERROR] Failed to create Python virtual environment.
    pause
    exit /b 1
  )
  popd

  call :inspect_venv
  if /i not "!VENV_STATUS!"=="healthy" (
    echo [ERROR] Virtual environment validation failed after recreation.
    if defined VENV_REASON echo [ERROR] !VENV_REASON!
    pause
    exit /b 1
  )
)

echo [2/6] Install backend dependencies...
pushd "%BACKEND_DIR%"
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
  popd
  echo [ERROR] Failed to upgrade pip.
  pause
  exit /b 1
)

"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
  popd
  echo [ERROR] Failed to install backend dependencies.
  pause
  exit /b 1
)

echo [3/5] Initialize database schema...
set "PYTHONPATH=."
"%VENV_PYTHON%" scripts\init_db.py
if errorlevel 1 (
  popd
  echo [ERROR] Failed to initialize database schema.
  pause
  exit /b 1
)
popd

echo [4/5] Install frontend dependencies...
pushd "%FRONTEND_DIR%"
call npm install
if errorlevel 1 (
  popd
  echo [ERROR] Failed to install frontend dependencies.
  pause
  exit /b 1
)
popd

echo [5/5] Init complete.
echo.
echo Next step:
echo Double-click scripts\start_system.bat
echo.
echo Initialization no longer clears existing data or imports any preset data.
echo Import real athlete and test data separately when needed.
echo.
pause
exit /b 0

:resolve_python312
set "RESOLVED_PYTHON="
set "PYTHON_VERSION="

py -3.12 -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))" >nul 2>nul
if not errorlevel 1 (
  set "RESOLVED_PYTHON=py -3.12"
  set "PYTHON_VERSION=3.12"
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.12.x was not found.
  echo Install Python 3.12.x and make sure either `py -3.12` or `python` works.
  exit /b 1
)

for /f %%i in ('python -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))" 2^>nul') do set "PYTHON_VERSION=%%i"
if not "%PYTHON_VERSION%"=="3.12" (
  echo [ERROR] Unsupported Python version: %PYTHON_VERSION%
  echo This project requires Python 3.12.x.
  echo Install Python 3.12.x and make sure either `py -3.12` or `python` works.
  exit /b 1
)

set "RESOLVED_PYTHON=python"
exit /b 0

:inspect_venv
set "VENV_STATUS=healthy"
set "VENV_REASON="

if not exist "%VENV_DIR%" (
  set "VENV_STATUS=missing"
  set "VENV_REASON=backend\.venv does not exist."
  exit /b 0
)

if not exist "%VENV_PYTHON%" (
  set "VENV_STATUS=broken"
  set "VENV_REASON=backend\.venv is missing Scripts\python.exe."
  exit /b 0
)

if not exist "%VENV_CFG%" (
  set "VENV_STATUS=broken"
  set "VENV_REASON=backend\.venv is missing pyvenv.cfg."
  exit /b 0
)

findstr /C:"version = 3.12" "%VENV_CFG%" >nul 2>nul
if errorlevel 1 (
  set "VENV_STATUS=broken"
  set "VENV_REASON=backend\.venv was created with a Python version other than 3.12."
  exit /b 0
)

call :extract_cfg_value "home = " VENV_HOME
if defined VENV_HOME (
  if not exist "!VENV_HOME!\python.exe" (
    set "VENV_STATUS=broken"
    set "VENV_REASON=The original Python home recorded in pyvenv.cfg no longer exists: !VENV_HOME!\python.exe"
    exit /b 0
  )
)

call :extract_cfg_value "executable = " VENV_EXECUTABLE
if defined VENV_EXECUTABLE (
  if not exist "!VENV_EXECUTABLE!" (
    set "VENV_STATUS=broken"
    set "VENV_REASON=The original Python executable recorded in pyvenv.cfg no longer exists: !VENV_EXECUTABLE!"
    exit /b 0
  )
)

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 (
  set "VENV_STATUS=broken"
  set "VENV_REASON=backend\.venv could not execute Python 3.12 on this computer."
  exit /b 0
)

exit /b 0

:extract_cfg_value
set "%~2="
for /f "tokens=1,* delims==" %%a in ('findstr /B /C:%~1 "%VENV_CFG%" 2^>nul') do (
  set "%~2=%%b"
)
if defined %~2 (
  for /f "tokens=* delims= " %%v in ("!%~2!") do set "%~2=%%v"
)
exit /b 0
