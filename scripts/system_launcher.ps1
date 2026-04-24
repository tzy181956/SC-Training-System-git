param(
    [ValidateSet('start', 'init')]
    [string]$Mode = 'start',
    [switch]$NoPause,
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))
$BackendDir = Join-Path $RootDir 'backend'
$FrontendDir = Join-Path $RootDir 'frontend'
$BackendVenvDir = Join-Path $BackendDir '.venv'
$BackendPython = Join-Path $BackendVenvDir 'Scripts\python.exe'
$BackendPyvenvCfg = Join-Path $BackendVenvDir 'pyvenv.cfg'
$BackendHealthUrl = 'http://127.0.0.1:8000/health'
$FrontendLocalUrl = 'http://127.0.0.1:5173/'
$FrontendRuntimeUrl = 'http://127.0.0.1:5173/runtime-access.json'
$FrontendRuntimeFile = Join-Path $FrontendDir 'public\runtime-access.json'
$SummaryDir = Join-Path $RootDir 'logs\startup'
$SummaryFile = Join-Path $SummaryDir 'last-launcher-summary.txt'
$TotalSteps = if ($Mode -eq 'start') { 6 } else { 5 }
$CurrentStep = 0
$StepResults = New-Object System.Collections.Generic.List[object]
$PythonSpec = $null
$NodeCommand = $null
$NodeVersion = $null
$NpmCommand = $null
$BackendState = 'not_checked'
$FrontendState = 'not_checked'
$AccessUrl = $FrontendLocalUrl
$StartedProcessIds = New-Object System.Collections.Generic.List[int]

function Ensure-SummaryDirectory {
    if (-not (Test-Path $SummaryDir)) {
        New-Item -ItemType Directory -Path $SummaryDir -Force | Out-Null
    }
}

function Pause-Launcher {
    if ($NoPause) {
        return
    }

    try {
        [void](Read-Host 'Press Enter to close')
    } catch {
    }
}

function Add-StepResult {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Detail
    )

    $StepResults.Add([pscustomobject]@{
            Name   = $Name
            Status = $Status
            Detail = $Detail
        }) | Out-Null
}

function Write-Step {
    param([string]$Title)

    $script:CurrentStep += 1
    Write-Host ''
    Write-Host ('[{0}/{1}] {2}' -f $script:CurrentStep, $script:TotalSteps, $Title) -ForegroundColor Cyan
}

function Resolve-CommandName {
    param([string[]]$Candidates)

    foreach ($candidate in $Candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $command) {
            return $command.Name
        }
    }

    return $null
}

function Invoke-CapturedCommand {
    param(
        [string]$Command,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    $tempLog = Join-Path $SummaryDir ('launcher-temp-{0}.log' -f ([guid]::NewGuid().ToString('N')))
    Ensure-SummaryDirectory

    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments 2>&1 | Tee-Object -FilePath $tempLog | Out-Host
        $exitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    } finally {
        Pop-Location
    }

    $logLines = @()
    if (Test-Path $tempLog) {
        $logLines = Get-Content -LiteralPath $tempLog
        Remove-Item -LiteralPath $tempLog -Force -ErrorAction SilentlyContinue
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = $logLines
    }
}

function Get-SummaryText {
    param(
        [string]$OverallStatus,
        [string]$ModeLabel,
        [string]$Headline,
        [string]$Detail,
        [string]$Category,
        [string[]]$PossibleCauses,
        [string[]]$Suggestions,
        [string]$CommandLine,
        [string]$LogExcerpt
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('Training Platform launcher summary') | Out-Null
    $lines.Add(('Timestamp: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))) | Out-Null
    $lines.Add(('Mode: {0}' -f $ModeLabel)) | Out-Null
    $lines.Add(('Status: {0}' -f $OverallStatus)) | Out-Null
    $lines.Add(('Headline: {0}' -f $Headline)) | Out-Null
    if ($Category) {
        $lines.Add(('Category: {0}' -f $Category)) | Out-Null
    }
    if ($Detail) {
        $lines.Add(('Detail: {0}' -f $Detail)) | Out-Null
    }

    $lines.Add(('Project root: {0}' -f $RootDir)) | Out-Null
    if ($null -ne $PythonSpec) {
        $lines.Add(('Python: {0}' -f $PythonSpec.Display)) | Out-Null
    } else {
        $lines.Add('Python: not resolved') | Out-Null
    }
    if ($NodeVersion) {
        $lines.Add(('Node: {0}' -f $NodeVersion)) | Out-Null
    } else {
        $lines.Add('Node: not resolved') | Out-Null
    }
    $lines.Add(('Backend state: {0}' -f $BackendState)) | Out-Null
    $lines.Add(('Frontend state: {0}' -f $FrontendState)) | Out-Null
    $lines.Add(('Frontend access URL: {0}' -f $AccessUrl)) | Out-Null

    $lines.Add('') | Out-Null
    $lines.Add('Step results:') | Out-Null
    foreach ($result in $StepResults) {
        $lines.Add((' - {0}: {1} - {2}' -f $result.Name, $result.Status, $result.Detail)) | Out-Null
    }

    if ($PossibleCauses -and $PossibleCauses.Count -gt 0) {
        $lines.Add('') | Out-Null
        $lines.Add('Possible causes:') | Out-Null
        foreach ($cause in $PossibleCauses) {
            $lines.Add((' - {0}' -f $cause)) | Out-Null
        }
    }

    if ($Suggestions -and $Suggestions.Count -gt 0) {
        $lines.Add('') | Out-Null
        $lines.Add('Suggested fixes:') | Out-Null
        foreach ($suggestion in $Suggestions) {
            $lines.Add((' - {0}' -f $suggestion)) | Out-Null
        }
    }

    if ($CommandLine) {
        $lines.Add('') | Out-Null
        $lines.Add(('Command: {0}' -f $CommandLine)) | Out-Null
    }

    if ($LogExcerpt) {
        $lines.Add('') | Out-Null
        $lines.Add('Log excerpt:') | Out-Null
        foreach ($line in ($LogExcerpt -split "`r?`n")) {
            $lines.Add((' | {0}' -f $line)) | Out-Null
        }
    }

    return ($lines -join [Environment]::NewLine)
}

function Write-SummaryFile {
    param([string]$Content)

    Ensure-SummaryDirectory
    Set-Content -LiteralPath $SummaryFile -Value $Content -Encoding UTF8
}

function Fail-Launcher {
    param(
        [string]$StepName,
        [string]$Category,
        [string]$Detail,
        [string[]]$PossibleCauses,
        [string[]]$Suggestions,
        [string]$CommandLine,
        [string]$LogExcerpt
    )

    Add-StepResult -Name $StepName -Status 'FAILED' -Detail $Detail
    $summary = Get-SummaryText `
        -OverallStatus 'FAILED' `
        -ModeLabel $Mode `
        -Headline $StepName `
        -Detail $Detail `
        -Category $Category `
        -PossibleCauses $PossibleCauses `
        -Suggestions $Suggestions `
        -CommandLine $CommandLine `
        -LogExcerpt $LogExcerpt

    Write-SummaryFile -Content $summary

    Write-Host ''
    Write-Host ('[FAIL] {0}' -f $StepName) -ForegroundColor Red
    Write-Host $Detail -ForegroundColor Yellow
    if ($Suggestions -and $Suggestions.Count -gt 0) {
        Write-Host ''
        Write-Host 'Suggested fixes:' -ForegroundColor Yellow
        foreach ($suggestion in $Suggestions) {
            Write-Host (' - {0}' -f $suggestion)
        }
    }

    Write-Host ''
    Write-Host ('Copyable summary saved to: {0}' -f $SummaryFile) -ForegroundColor Yellow
    Write-Host '----- COPY THIS SUMMARY -----' -ForegroundColor Yellow
    Write-Host $summary
    Write-Host '----- END SUMMARY -----' -ForegroundColor Yellow

    Pause-Launcher
    exit 1
}

function Invoke-StepCommand {
    param(
        [string]$StepName,
        [string]$Command,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$Category,
        [string]$FailureDetail,
        [string[]]$PossibleCauses,
        [string[]]$Suggestions
    )

    $commandLine = ($Command + ' ' + ($Arguments -join ' ')).Trim()
    $result = Invoke-CapturedCommand -Command $Command -Arguments $Arguments -WorkingDirectory $WorkingDirectory
    if ($result.ExitCode -ne 0) {
        $logExcerpt = ($result.Output | Select-Object -Last 25) -join [Environment]::NewLine
        Fail-Launcher `
            -StepName $StepName `
            -Category $Category `
            -Detail $FailureDetail `
            -PossibleCauses $PossibleCauses `
            -Suggestions $Suggestions `
            -CommandLine $commandLine `
            -LogExcerpt $logExcerpt
    }

    return $result.Output
}

function Resolve-Python312 {
    $pyLauncher = Resolve-CommandName -Candidates @('py.exe', 'py')
    if ($pyLauncher) {
        try {
            $versionOutput = & $pyLauncher -3.12 -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and (($versionOutput | Select-Object -Last 1).ToString().Trim() -eq '3.12')) {
                return [pscustomobject]@{
                    Command = $pyLauncher
                    Prefix  = @('-3.12')
                    Display = "$pyLauncher -3.12"
                }
            }
        } catch {
        }
    }

    $pythonCommand = Resolve-CommandName -Candidates @('python.exe', 'python')
    if (-not $pythonCommand) {
        Fail-Launcher `
            -StepName 'Environment check' `
            -Category 'python_missing' `
            -Detail 'Python 3.12 was not found on this computer.' `
            -PossibleCauses @(
                'Python is not installed yet.',
                'Python is installed but not added to PATH.'
            ) `
            -Suggestions @(
                'Install Python 3.12.x from the official installer.',
                'Enable the PATH option during installation, then run start_system.bat again.'
            )
    }

    $detectedVersion = ''
    try {
        $versionOutput = & $pythonCommand -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $detectedVersion = ($versionOutput | Select-Object -Last 1).ToString().Trim()
        }
    } catch {
    }

    if ($detectedVersion -ne '3.12') {
        Fail-Launcher `
            -StepName 'Environment check' `
            -Category 'python_version_unsupported' `
            -Detail ('Unsupported Python version detected: {0}' -f ($(if ($detectedVersion) { $detectedVersion } else { 'unknown' }))) `
            -PossibleCauses @(
                'This project currently supports Python 3.12 only.',
                'The default python command points to another installed version.'
            ) `
            -Suggestions @(
                'Install Python 3.12.x.',
                'Make sure either py -3.12 or python resolves to Python 3.12, then run the launcher again.'
            )
    }

    return [pscustomobject]@{
        Command = $pythonCommand
        Prefix  = @()
        Display = $pythonCommand
    }
}

function Get-NodeVersion {
    $nodeCommand = Resolve-CommandName -Candidates @('node.exe', 'node')
    if (-not $nodeCommand) {
        Fail-Launcher `
            -StepName 'Environment check' `
            -Category 'node_missing' `
            -Detail 'Node.js was not found on this computer.' `
            -PossibleCauses @(
                'Node.js is not installed yet.',
                'Node.js is installed but not added to PATH.'
            ) `
            -Suggestions @(
                'Install Node.js 18 or newer.',
                'Re-open the launcher after installation so PATH is refreshed.'
            )
    }

    $script:NodeCommand = $nodeCommand
    $versionOutput = & $nodeCommand -p 'process.version' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Fail-Launcher `
            -StepName 'Environment check' `
            -Category 'node_broken' `
            -Detail 'Node.js exists in PATH but could not run.' `
            -PossibleCauses @(
                'Node.js installation is incomplete.',
                'The current PATH entry points to a broken Node.js binary.'
            ) `
            -Suggestions @(
                'Reinstall Node.js 18 or newer.',
                'Open a new terminal and try again.'
            )
    }

    $version = ($versionOutput | Select-Object -Last 1).ToString().Trim()
    $major = 0
    if ($version -match '^v(\d+)') {
        $major = [int]$Matches[1]
    }
    if ($major -lt 18) {
        Fail-Launcher `
            -StepName 'Environment check' `
            -Category 'node_version_unsupported' `
            -Detail ('Unsupported Node.js version detected: {0}' -f $version) `
            -PossibleCauses @(
                'The installed Node.js version is older than the frontend requires.'
            ) `
            -Suggestions @(
                'Upgrade Node.js to version 18 or newer.',
                'Run the launcher again after the upgrade.'
            )
    }

    $script:NpmCommand = Resolve-CommandName -Candidates @('npm.cmd', 'npm')
    if (-not $script:NpmCommand) {
        Fail-Launcher `
            -StepName 'Environment check' `
            -Category 'npm_missing' `
            -Detail 'npm was not found on this computer.' `
            -PossibleCauses @(
                'The Node.js installation does not include npm.',
                'npm is not available in PATH.'
            ) `
            -Suggestions @(
                'Reinstall Node.js and keep npm enabled.',
                'Open a new terminal and run the launcher again.'
            )
    }

    return $version
}

function Test-BackendVenv {
    if (-not (Test-Path $BackendVenvDir)) {
        return [pscustomobject]@{ Status = 'missing'; Reason = 'backend\.venv does not exist.' }
    }
    if (-not (Test-Path $BackendPython)) {
        return [pscustomobject]@{ Status = 'broken'; Reason = 'backend\.venv is missing Scripts\python.exe.' }
    }
    if (-not (Test-Path $BackendPyvenvCfg)) {
        return [pscustomobject]@{ Status = 'broken'; Reason = 'backend\.venv is missing pyvenv.cfg.' }
    }

    $cfgText = Get-Content -LiteralPath $BackendPyvenvCfg -Raw
    if ($cfgText -notmatch 'version\s*=\s*3\.12') {
        return [pscustomobject]@{ Status = 'broken'; Reason = 'backend\.venv was not created with Python 3.12.' }
    }

    try {
        & $BackendPython -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" *> $null
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{ Status = 'broken'; Reason = 'backend\.venv could not execute Python 3.12 on this computer.' }
        }
    } catch {
        return [pscustomobject]@{ Status = 'broken'; Reason = 'backend\.venv could not execute Python 3.12 on this computer.' }
    }

    return [pscustomobject]@{ Status = 'healthy'; Reason = 'backend\.venv is healthy.' }
}

function Ensure-BackendEnvironment {
    $venvCheck = Test-BackendVenv
    $venvAction = 'reused'

    if ($venvCheck.Status -ne 'healthy') {
        $venvAction = 'rebuilt'
        if (Test-Path $BackendVenvDir) {
            Write-Host ('[INFO] Removing unusable backend\.venv: {0}' -f $venvCheck.Reason)
            Remove-Item -LiteralPath $BackendVenvDir -Recurse -Force
        } else {
            Write-Host '[INFO] backend\.venv was not found. A new virtual environment will be created.'
        }

        Invoke-StepCommand `
            -StepName 'Backend environment' `
            -Command $PythonSpec.Command `
            -Arguments ($PythonSpec.Prefix + @('-m', 'venv', '.venv')) `
            -WorkingDirectory $BackendDir `
            -Category 'backend_venv_create_failed' `
            -FailureDetail 'Failed to create backend\.venv.' `
            -PossibleCauses @(
                'Python 3.12 is present but the venv module failed.',
                'The project folder does not allow creating files.',
                'An antivirus tool is blocking virtual environment creation.'
            ) `
            -Suggestions @(
                'Close other programs that may lock the project folder and try again.',
                'Make sure this project folder is writable.',
                'If antivirus is blocking Python, allow python.exe and rerun the launcher.'
            ) | Out-Null

        $venvCheck = Test-BackendVenv
        if ($venvCheck.Status -ne 'healthy') {
            Fail-Launcher `
                -StepName 'Backend environment' `
                -Category 'backend_venv_validation_failed' `
                -Detail ('backend\.venv was recreated but is still not healthy: {0}' -f $venvCheck.Reason) `
                -PossibleCauses @(
                    'The new virtual environment still points to an invalid Python install.',
                    'File creation completed partially.'
                ) `
                -Suggestions @(
                    'Reinstall Python 3.12 and run the launcher again.',
                    'Delete backend\.venv manually if it still exists, then rerun start_system.bat.'
                )
        }
    }

    $importCheck = Invoke-CapturedCommand `
        -Command $BackendPython `
        -Arguments @('-c', 'import fastapi, uvicorn, sqlalchemy, alembic, openpyxl') `
        -WorkingDirectory $BackendDir

    $dependencyAction = 'already_ready'
    if ($importCheck.ExitCode -ne 0) {
        $dependencyAction = 'installed'
        Invoke-StepCommand `
            -StepName 'Backend environment' `
            -Command $BackendPython `
            -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip') `
            -WorkingDirectory $BackendDir `
            -Category 'backend_pip_upgrade_failed' `
            -FailureDetail 'Failed to upgrade pip inside backend\.venv.' `
            -PossibleCauses @(
                'The internet connection is unavailable.',
                'The Python package index could not be reached.',
                'The current Python environment is damaged.'
            ) `
            -Suggestions @(
                'Check internet access, then run the launcher again.',
                'If you are on a restricted network, switch to a network that can access PyPI.',
                'If the problem repeats, delete backend\.venv and rerun start_system.bat.'
            ) | Out-Null

        Invoke-StepCommand `
            -StepName 'Backend environment' `
            -Command $BackendPython `
            -Arguments @('-m', 'pip', 'install', '-r', 'requirements.txt') `
            -WorkingDirectory $BackendDir `
            -Category 'backend_dependency_install_failed' `
            -FailureDetail 'Failed to install backend dependencies from requirements.txt.' `
            -PossibleCauses @(
                'One or more Python packages could not be downloaded.',
                'The current Python version does not match the project requirement.',
                'A proxy or firewall blocked pip.'
            ) `
            -Suggestions @(
                'Check internet access and rerun the launcher.',
                'Confirm that Python 3.12 is the version being used.',
                'If your network uses a proxy, configure pip first and rerun.'
            ) | Out-Null
    }

    Add-StepResult -Name 'Backend environment' -Status 'OK' -Detail ("venv {0}; dependencies {1}" -f $venvAction, $dependencyAction)
}

function Ensure-FrontendDependencies {
    $packageCheck = Invoke-CapturedCommand `
        -Command $NodeCommand `
        -Arguments @('-e', "require.resolve('vite/package.json'); require.resolve('vue/package.json'); require.resolve('axios/package.json');") `
        -WorkingDirectory $FrontendDir

    $dependencyAction = 'already_ready'
    if (-not (Test-Path (Join-Path $FrontendDir 'node_modules')) -or $packageCheck.ExitCode -ne 0) {
        $dependencyAction = 'installed'
        Invoke-StepCommand `
            -StepName 'Frontend dependencies' `
            -Command $NpmCommand `
            -Arguments @('install') `
            -WorkingDirectory $FrontendDir `
            -Category 'frontend_dependency_install_failed' `
            -FailureDetail 'Failed to install frontend dependencies with npm install.' `
            -PossibleCauses @(
                'The internet connection is unavailable.',
                'The npm registry is blocked by the current network.',
                'node_modules or package-lock.json is in a damaged state.'
            ) `
            -Suggestions @(
                'Check internet access and rerun the launcher.',
                'Delete frontend\node_modules and run the launcher again.',
                'If you use a private registry, verify npm registry settings first.'
            ) | Out-Null
    }

    Add-StepResult -Name 'Frontend dependencies' -Status 'OK' -Detail ("dependencies {0}" -f $dependencyAction)
}

function Ensure-DatabaseReady {
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = $BackendDir
    try {
        $migrationOutput = Invoke-StepCommand `
            -StepName 'Database migration check' `
            -Command $BackendPython `
            -Arguments @('scripts\migrate_db.py', 'ensure') `
            -WorkingDirectory $BackendDir `
            -Category 'database_migration_failed' `
            -FailureDetail 'Database migration check did not complete successfully.' `
            -PossibleCauses @(
                'The database file is locked by another program.',
                'A migration script failed while applying schema changes.',
                'The current backend dependencies are incomplete.'
            ) `
            -Suggestions @(
                'Close other backend windows or tools that may lock backend\training.db, then rerun the launcher.',
                'Check the summary log excerpt for the failing migration.',
                'If the issue persists, send the summary file to the maintainer for diagnosis.'
            )
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }

    $detail = 'database already ready'
    if ($migrationOutput -match 'Upgrading database') {
        $detail = 'database upgraded to head'
    } elseif ($migrationOutput -match 'not versioned yet') {
        $detail = 'database bootstrap flow completed'
    }

    Add-StepResult -Name 'Database migration check' -Status 'OK' -Detail $detail
}

function Test-BackendHealthy {
    try {
        $response = Invoke-WebRequest -Uri $BackendHealthUrl -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -eq 200 -and $response.Content -match '"status"\s*:\s*"ok"')
    } catch {
        return $false
    }
}

function Test-TcpPort {
    param([int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(500)
        if (-not $connected) {
            return $false
        }

        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-FrontendRuntimeInfo {
    try {
        $response = Invoke-WebRequest -Uri $FrontendRuntimeUrl -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            if ($data.accessUrl) {
                return [pscustomobject]@{
                    AccessUrl = [string]$data.accessUrl
                    Host      = [string]$data.host
                    Port      = [int]$data.port
                    Source    = [string]$data.source
                }
            }
        }
    } catch {
    }

    try {
        $response = Invoke-WebRequest -Uri $FrontendLocalUrl -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            return [pscustomobject]@{
                AccessUrl = $FrontendLocalUrl
                Host      = '127.0.0.1'
                Port      = 5173
                Source    = 'local-fallback'
            }
        }
    } catch {
    }

    return $null
}

function Wait-Until {
    param(
        [int]$TimeoutSeconds,
        [scriptblock]$Check
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $result = & $Check
        if ($result) {
            return $result
        }
        Start-Sleep -Milliseconds 750
    }

    return $null
}

function Start-ServiceWindow {
    param(
        [string]$WindowTitle,
        [string]$ScriptPath
    )

    $process = Start-Process `
        -FilePath 'cmd.exe' `
        -ArgumentList @('/k', ('title {0} && call "{1}"' -f $WindowTitle, $ScriptPath)) `
        -WorkingDirectory $RootDir `
        -PassThru

    $StartedProcessIds.Add($process.Id) | Out-Null
    return $process
}

function Ensure-ServicesRunning {
    $backendAlreadyRunning = Test-BackendHealthy
    if ($backendAlreadyRunning) {
        $script:BackendState = 'reused_existing_service'
        Write-Host '[INFO] Backend is already healthy on port 8000. Reusing the existing service.'
    } elseif (Test-TcpPort -Port 8000) {
        Fail-Launcher `
            -StepName 'Start services' `
            -Category 'backend_port_conflict' `
            -Detail 'Port 8000 is already in use, but the expected backend health endpoint is not responding.' `
            -PossibleCauses @(
                'Another program is using port 8000.',
                'An old backend process is stuck in a broken state.'
            ) `
            -Suggestions @(
                'Close the program using port 8000, then run start_system.bat again.',
                'If another backend window is open, close it first and retry.'
            )
    } else {
        if (Test-Path $FrontendRuntimeFile) {
            Remove-Item -LiteralPath $FrontendRuntimeFile -Force -ErrorAction SilentlyContinue
        }

        Write-Host '[INFO] Starting backend window...'
        Start-ServiceWindow -WindowTitle 'Training Platform Backend' -ScriptPath (Join-Path $ScriptDir 'start_backend.bat') | Out-Null
        $backendReady = Wait-Until -TimeoutSeconds 30 -Check { Test-BackendHealthy }
        if (-not $backendReady) {
            $category = if (Test-TcpPort -Port 8000) { 'backend_start_unhealthy' } else { 'backend_start_failed' }
            $detail = if ($category -eq 'backend_start_unhealthy') {
                'Backend window started, but http://127.0.0.1:8000/health never became healthy.'
            } else {
                'Backend window did not open a healthy service on port 8000.'
            }

            Fail-Launcher `
                -StepName 'Start services' `
                -Category $category `
                -Detail $detail `
                -PossibleCauses @(
                    'The backend process crashed during startup.',
                    'A required backend package is still missing.',
                    'Port 8000 became unavailable during startup.'
                ) `
                -Suggestions @(
                    'Check the backend window for the first traceback line.',
                    'Run start_system.bat again after fixing the backend error.',
                    'If needed, send the summary file and the backend window error to the maintainer.'
                )
        }

        $script:BackendState = 'started_new_window'
    }

    $frontendInfo = Get-FrontendRuntimeInfo
    if ($frontendInfo) {
        $script:FrontendState = 'reused_existing_service'
        $script:AccessUrl = $frontendInfo.AccessUrl
        Write-Host '[INFO] Frontend is already reachable on port 5173. Reusing the existing service.'
        return
    }

    if (Test-TcpPort -Port 5173) {
        Fail-Launcher `
            -StepName 'Start services' `
            -Category 'frontend_port_conflict' `
            -Detail 'Port 5173 is already in use, but the expected frontend runtime endpoint is not responding.' `
            -PossibleCauses @(
                'Another frontend dev server is using port 5173.',
                'An old frontend process is stuck in a broken state.'
            ) `
            -Suggestions @(
                'Close the program using port 5173, then run start_system.bat again.',
                'If another frontend window is open, close it first and retry.'
            )
    }

    if (Test-Path $FrontendRuntimeFile) {
        Remove-Item -LiteralPath $FrontendRuntimeFile -Force -ErrorAction SilentlyContinue
    }

    Write-Host '[INFO] Starting frontend window...'
    Start-ServiceWindow -WindowTitle 'Training Platform Frontend' -ScriptPath (Join-Path $ScriptDir 'start_frontend.bat') | Out-Null
    $frontendInfo = Wait-Until -TimeoutSeconds 40 -Check { Get-FrontendRuntimeInfo }
    if (-not $frontendInfo) {
        $category = if (Test-TcpPort -Port 5173) { 'frontend_start_unhealthy' } else { 'frontend_start_failed' }
        $detail = if ($category -eq 'frontend_start_unhealthy') {
            'Frontend window started, but runtime-access.json never became available.'
        } else {
            'Frontend window did not open a reachable service on port 5173.'
        }

        Fail-Launcher `
            -StepName 'Start services' `
            -Category $category `
            -Detail $detail `
            -PossibleCauses @(
                'The frontend dev server crashed during startup.',
                'A frontend dependency is still missing.',
                'Port 5173 became unavailable during startup.'
            ) `
            -Suggestions @(
                'Check the frontend window for the first error line.',
                'Run start_system.bat again after fixing the frontend error.',
                'If needed, send the summary file and the frontend window error to the maintainer.'
            )
    }

    $script:FrontendState = 'started_new_window'
    $script:AccessUrl = $frontendInfo.AccessUrl
}

function Finish-Launcher {
    param([string]$Headline, [string]$Detail)

    Add-StepResult -Name $Headline -Status 'OK' -Detail $Detail

    $summary = Get-SummaryText `
        -OverallStatus 'SUCCESS' `
        -ModeLabel $Mode `
        -Headline $Headline `
        -Detail $Detail `
        -Category '' `
        -PossibleCauses @() `
        -Suggestions @() `
        -CommandLine '' `
        -LogExcerpt ''

    Write-SummaryFile -Content $summary

    Write-Host ''
    Write-Host '[OK] Launcher finished successfully.' -ForegroundColor Green
    Write-Host ('Summary saved to: {0}' -f $SummaryFile) -ForegroundColor Green
    if ($Mode -eq 'start') {
        Write-Host ('Frontend: {0}' -f $AccessUrl)
        Write-Host ('Backend : {0}' -f $BackendHealthUrl.Replace('/health', ''))
    }
    Write-Host ''
    Write-Host '----- COPY THIS SUMMARY -----' -ForegroundColor Yellow
    Write-Host $summary
    Write-Host '----- END SUMMARY -----' -ForegroundColor Yellow

    Pause-Launcher
    exit 0
}

Write-Host ''
Write-Host '========================================='
Write-Host ' Training Platform Launcher'
Write-Host (' Mode: {0}' -f $Mode.ToUpperInvariant())
Write-Host '========================================='

Write-Step -Title 'Check required tools'
$PythonSpec = Resolve-Python312
$NodeVersion = Get-NodeVersion
Add-StepResult -Name 'Environment check' -Status 'OK' -Detail ("Python {0}; Node {1}; npm available" -f $PythonSpec.Display, $NodeVersion)

Write-Step -Title 'Prepare backend environment'
Ensure-BackendEnvironment

Write-Step -Title 'Prepare frontend dependencies'
Ensure-FrontendDependencies

Write-Step -Title 'Check database and migrations'
Ensure-DatabaseReady

if ($Mode -eq 'init') {
    Write-Step -Title 'Finish initialization'
    Finish-Launcher -Headline 'Initialization finish' -Detail 'Environment, dependencies, and database checks are ready. You can now run start_system.bat.'
}

Write-Step -Title 'Start or reuse services'
Ensure-ServicesRunning
Add-StepResult -Name 'Start services' -Status 'OK' -Detail ("backend {0}; frontend {1}" -f $BackendState, $FrontendState)

Write-Step -Title 'Open browser and print access info'
if (-not $NoBrowser) {
    Start-Process $AccessUrl | Out-Null
}
$startupDetail = if ($NoBrowser) { 'Access entry prepared at {0}' -f $AccessUrl } else { 'Browser entry prepared at {0}' -f $AccessUrl }
Finish-Launcher -Headline 'Startup finish' -Detail $startupDetail
