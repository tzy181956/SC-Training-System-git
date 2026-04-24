@echo off
setlocal
chcp 65001 >nul

where powershell >nul 2>nul
if errorlevel 1 (
  echo [ERROR] PowerShell was not found on this computer.
  echo [ERROR] This launcher requires Windows PowerShell to run the step-by-step checks.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0system_launcher.ps1" -Mode init
exit /b %errorlevel%
