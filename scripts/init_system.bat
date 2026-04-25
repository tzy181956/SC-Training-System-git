@echo off
setlocal
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%SystemRoot%\System32\chcp.com" 65001 >nul 2>nul
for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI"
set "SUMMARY_DIR=%ROOT_DIR%\logs\startup"
set "SUMMARY_FILE=%SUMMARY_DIR%\last-launcher-summary.txt"
set "DETAIL_LOG=%SUMMARY_DIR%\last-launcher-detail.log"
set "TROUBLESHOOTING_DOC=%ROOT_DIR%\docs\phase1-launcher-failure-summary.md"
if not exist "%SUMMARY_DIR%" mkdir "%SUMMARY_DIR%"

if not exist "%POWERSHELL_EXE%" (
  >"%DETAIL_LOG%" (
    echo [ERROR] PowerShell was not found on this computer.
    echo [ERROR] Launcher entry: %~f0
    echo [ERROR] Time: %date% %time%
    echo [ERROR] Expected PowerShell path: %POWERSHELL_EXE%
  )
  >"%SUMMARY_FILE%" (
    echo Training Platform launcher failure summary
    echo Time: %date% %time%
    echo Mode: init
    echo Failed step: Environment check
    echo Error type: PowerShell unavailable
    echo Error code: powershell_missing
    echo Most likely cause: Windows PowerShell is not available on this computer, or powershell.exe is not in PATH.
    echo Suggested fix: Restore Windows PowerShell access, then rerun init_system.bat.
    echo Detailed log: %DETAIL_LOG%
    echo Troubleshooting doc: %TROUBLESHOOTING_DOC%
  )
  echo [ERROR] PowerShell was not found on this computer.
  echo [ERROR] This launcher requires Windows PowerShell to run the step-by-step checks.
  echo [ERROR] Copyable summary saved to: %SUMMARY_FILE%
  pause
  exit /b 1
)

"%POWERSHELL_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0system_launcher.ps1" -Mode init
exit /b %errorlevel%
