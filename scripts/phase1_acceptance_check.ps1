param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir ".."))
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$Results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Id,
        [string]$Name,
        [string]$Status,
        [string]$Detail
    )

    $Results.Add([pscustomobject]@{
            Id     = $Id
            Name   = $Name
            Status = $Status
            Detail = $Detail
        }) | Out-Null
}

function Invoke-Check {
    param(
        [string]$Id,
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host ("[{0}] {1}" -f $Id, $Name) -ForegroundColor Cyan
    try {
        & $Action
        Add-Result -Id $Id -Name $Name -Status "PASS" -Detail "ok"
        Write-Host ("[PASS] {0}" -f $Name) -ForegroundColor Green
        return $true
    } catch {
        $message = $_.Exception.Message
        Add-Result -Id $Id -Name $Name -Status "FAIL" -Detail $message
        Write-Host ("[FAIL] {0}" -f $Name) -ForegroundColor Red
        Write-Host $message -ForegroundColor Yellow
        return $false
    }
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0) {
            throw ("Command failed with exit code {0}: {1} {2}" -f $LASTEXITCODE, $FilePath, ($ArgumentList -join " "))
        }
    } finally {
        Pop-Location
    }
}

$launcherOk = Invoke-Check -Id "C01" -Name "Launcher init smoke" -Action {
    Invoke-Native -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        (Join-Path $ScriptDir "system_launcher.ps1"),
        "-Mode",
        "init",
        "-NoPause"
    ) -WorkingDirectory $RootDir
}

if (-not $launcherOk) {
    Add-Result -Id "C02" -Name "Text encoding check" -Status "SKIPPED" -Detail "launcher init failed"
    Add-Result -Id "C03" -Name "Backend compileall" -Status "SKIPPED" -Detail "launcher init failed"
    Add-Result -Id "C04" -Name "Database migration ensure" -Status "SKIPPED" -Detail "launcher init failed"
    Add-Result -Id "C05" -Name "Backend phase1 smoke" -Status "SKIPPED" -Detail "launcher init failed"
    Add-Result -Id "C06" -Name "Frontend production build" -Status "SKIPPED" -Detail "launcher init failed"
} else {
    Invoke-Check -Id "C02" -Name "Text encoding check" -Action {
        Invoke-Native -FilePath $BackendPython -ArgumentList @((Join-Path $ScriptDir "check_text_encoding.py")) -WorkingDirectory $RootDir
    } | Out-Null

    Invoke-Check -Id "C03" -Name "Backend compileall" -Action {
        Invoke-Native -FilePath $BackendPython -ArgumentList @("-m", "compileall", "app") -WorkingDirectory $BackendDir
    } | Out-Null

    Invoke-Check -Id "C04" -Name "Database migration ensure" -Action {
        Invoke-Native -FilePath $BackendPython -ArgumentList @("-m", "scripts.migrate_db", "ensure") -WorkingDirectory $BackendDir
    } | Out-Null

    Invoke-Check -Id "C05" -Name "Backend phase1 smoke" -Action {
        Invoke-Native -FilePath $BackendPython -ArgumentList @("scripts\phase1_backend_smoke_check.py") -WorkingDirectory $BackendDir
    } | Out-Null

    Invoke-Check -Id "C06" -Name "Frontend production build" -Action {
        Invoke-Native -FilePath "npm.cmd" -ArgumentList @("run", "build") -WorkingDirectory $FrontendDir
    } | Out-Null
}

$failed = @($Results | Where-Object { $_.Status -eq "FAIL" })

Write-Host ""
Write-Host "===== Phase 1 Acceptance Self-Check Summary =====" -ForegroundColor Yellow
foreach ($result in $Results) {
    Write-Host ("[{0}] {1} - {2}" -f $result.Status, $result.Id, $result.Name)
    if ($result.Detail -and $result.Detail -ne "ok") {
        Write-Host ("  {0}" -f $result.Detail)
    }
}

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host ("[FAIL] {0} blocking checks failed." -f $failed.Count) -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[OK] Phase 1 acceptance self-check passed." -ForegroundColor Green
exit 0
