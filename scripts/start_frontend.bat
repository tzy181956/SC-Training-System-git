@echo off
setlocal
chcp 65001 >nul

set "ROOT_DIR=%~dp0.."
set "FRONTEND_DIR=%ROOT_DIR%\frontend"

if not exist "%FRONTEND_DIR%\node_modules" (
  echo [ERROR] Frontend dependencies were not found.
  echo Please run scripts\init_system.bat first.
  pause
  exit /b 1
)

pushd "%FRONTEND_DIR%"
echo [FRONTEND] Starting Vue dev server at http://127.0.0.1:5173
call npm run dev -- --host 0.0.0.0 --port 5173
popd
