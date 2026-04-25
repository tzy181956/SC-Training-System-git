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
$RunTimestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$SummaryFile = Join-Path $SummaryDir 'last-launcher-summary.txt'
$TimestampedSummaryFile = Join-Path $SummaryDir ("launcher-summary-{0}.txt" -f $RunTimestamp)
$DetailLogFile = Join-Path $SummaryDir ("launcher-detail-{0}.log" -f $RunTimestamp)
$LastDetailLogFile = Join-Path $SummaryDir 'last-launcher-detail.log'
$TroubleshootingDoc = Join-Path $RootDir 'docs\phase1-launcher-failure-summary.md'
$TotalSteps = if ($Mode -eq 'start') { 6 } else { 5 }
$RetryLauncherFile = if ($Mode -eq 'init') { 'init_system.bat' } else { 'start_system.bat' }
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

function Get-Utf8BomEncoding {
    return (New-Object System.Text.UTF8Encoding($true))
}

function Write-LauncherLog {
    param(
        [string]$Message,
        [string]$Level = 'INFO'
    )

    Ensure-SummaryDirectory
    $line = '[{0}] [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level.ToUpperInvariant(), $Message
    $encoding = Get-Utf8BomEncoding
    [System.IO.File]::AppendAllText($DetailLogFile, ($line + [Environment]::NewLine), $encoding)
    [System.IO.File]::AppendAllText($LastDetailLogFile, ($line + [Environment]::NewLine), $encoding)
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

    Write-LauncherLog -Message ("STEP RESULT | {0} | {1} | {2}" -f $Name, $Status, $Detail)
}

function Write-Step {
    param([string]$Title)

    $script:CurrentStep += 1
    Write-Host ''
    Write-Host ('[{0}/{1}] {2}' -f $script:CurrentStep, $script:TotalSteps, $Title) -ForegroundColor Cyan
    Write-LauncherLog -Message ("STEP START | {0}/{1} | {2}" -f $script:CurrentStep, $script:TotalSteps, $Title)
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

function Convert-ToProcessArgumentLine {
    param([string[]]$Arguments)

    $encodedArgs = foreach ($argument in $Arguments) {
        if ($null -eq $argument) {
            '""'
            continue
        }

        if ($argument -match '[\s"]') {
            '"' + ($argument -replace '"', '\"') + '"'
        } else {
            $argument
        }
    }

    return ($encodedArgs -join ' ')
}

function Invoke-CapturedCommand {
    param(
        [string]$Command,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    $tempBase = Join-Path $SummaryDir ('launcher-temp-{0}' -f ([guid]::NewGuid().ToString('N')))
    $tempStdOut = '{0}.stdout.log' -f $tempBase
    $tempStdErr = '{0}.stderr.log' -f $tempBase
    Ensure-SummaryDirectory

    Push-Location $WorkingDirectory
    try {
        Write-LauncherLog -Message ("COMMAND START | {0} | cwd={1}" -f (($Command + ' ' + ($Arguments -join ' ')).Trim()), $WorkingDirectory)
        $argumentLine = Convert-ToProcessArgumentLine -Arguments $Arguments
        $process = Start-Process `
            -FilePath $Command `
            -ArgumentList $argumentLine `
            -WorkingDirectory $WorkingDirectory `
            -NoNewWindow `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $tempStdOut `
            -RedirectStandardError $tempStdErr
        $exitCode = [int]$process.ExitCode
    } finally {
        Pop-Location
    }

    $logLines = @()
    if (Test-Path $tempStdOut) {
        $logLines += Get-Content -LiteralPath $tempStdOut
        Remove-Item -LiteralPath $tempStdOut -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $tempStdErr) {
        $logLines += Get-Content -LiteralPath $tempStdErr
        Remove-Item -LiteralPath $tempStdErr -Force -ErrorAction SilentlyContinue
    }
    foreach ($line in $logLines) {
        Write-Host $line
    }

    if (@($logLines).Count -gt 0) {
        Write-LauncherLog -Message 'COMMAND OUTPUT BEGIN'
        foreach ($line in $logLines) {
            Write-LauncherLog -Message $line -Level 'CMD'
        }
        Write-LauncherLog -Message 'COMMAND OUTPUT END'
    }
    Write-LauncherLog -Message ("COMMAND END | exit={0}" -f $exitCode)

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = $logLines
    }
}

function Get-ErrorTypeInfo {
    param([string]$Category)

    $catalog = @{
        powershell_missing                 = @{ Label = 'PowerShell unavailable'; Section = 'powershell_missing'; DefaultCause = 'Windows PowerShell is not available on this computer, or powershell.exe is not in PATH.'; DefaultFix = 'Restore Windows PowerShell access, then run the launcher again.' }
        python_missing                     = @{ Label = 'Python 3.12 missing'; Section = 'python_missing'; DefaultCause = 'Python 3.12 is not installed, or PATH does not point to it.'; DefaultFix = 'Install Python 3.12.x and add it to PATH.' }
        python_version_unsupported         = @{ Label = 'Unsupported Python version'; Section = 'python_version_unsupported'; DefaultCause = 'The default python command does not point to Python 3.12.'; DefaultFix = 'Switch the launcher to Python 3.12, then retry.' }
        node_missing                       = @{ Label = 'Node.js missing'; Section = 'node_missing'; DefaultCause = 'Node.js is not installed, or PATH does not point to node.'; DefaultFix = 'Install Node.js 18 or newer.' }
        node_broken                        = @{ Label = 'Node.js command broken'; Section = 'node_broken'; DefaultCause = 'The node executable in PATH is damaged or incomplete.'; DefaultFix = 'Reinstall Node.js 18 or newer.' }
        node_version_unsupported           = @{ Label = 'Unsupported Node.js version'; Section = 'node_version_unsupported'; DefaultCause = 'The detected Node.js version is lower than the frontend requirement.'; DefaultFix = 'Upgrade Node.js to version 18 or newer.' }
        npm_missing                        = @{ Label = 'npm missing'; Section = 'npm_missing'; DefaultCause = 'The current Node.js installation does not expose npm.'; DefaultFix = 'Reinstall Node.js and confirm npm works from a new terminal.' }
        backend_venv_create_failed         = @{ Label = 'Backend virtual environment creation failed'; Section = 'backend_venv_create_failed'; DefaultCause = 'Python can run, but backend\\.venv could not be created.'; DefaultFix = 'Make sure the project folder is writable and not blocked by antivirus, then retry.' }
        backend_venv_validation_failed     = @{ Label = 'Backend virtual environment validation failed'; Section = 'backend_venv_validation_failed'; DefaultCause = 'The recreated backend\\.venv still points to an invalid or damaged Python.'; DefaultFix = 'Reinstall Python 3.12, delete backend\\.venv, and run the launcher again.' }
        backend_pip_upgrade_failed         = @{ Label = 'Backend pip upgrade failed'; Section = 'backend_pip_upgrade_failed'; DefaultCause = 'pip could not reach the package index, or the Python environment is damaged.'; DefaultFix = 'Check network access to PyPI, then retry.' }
        backend_dependency_install_failed  = @{ Label = 'Backend dependency install failed'; Section = 'backend_dependency_install_failed'; DefaultCause = 'One or more backend dependencies were not installed successfully.'; DefaultFix = 'Confirm network access and Python 3.12, then retry dependency installation.' }
        frontend_dependency_install_failed = @{ Label = 'Frontend dependency install failed'; Section = 'frontend_dependency_install_failed'; DefaultCause = 'npm install did not finish successfully.'; DefaultFix = 'Check npm registry access; if needed, delete frontend\\node_modules and retry.' }
        database_migration_failed          = @{ Label = 'Database migration failed'; Section = 'database_migration_failed'; DefaultCause = 'The database is locked, or a migration script failed.'; DefaultFix = 'Close programs using training.db, then rerun the launcher.' }
        backend_port_conflict              = @{ Label = 'Backend port conflict'; Section = 'backend_port_conflict'; DefaultCause = 'Port 8000 is already in use by another program.'; DefaultFix = 'Close the process using port 8000, then retry.' }
        backend_start_unhealthy            = @{ Label = 'Backend started but never became healthy'; Section = 'backend_start_unhealthy'; DefaultCause = 'The backend window opened, but the app failed during initialization.'; DefaultFix = 'Check the first traceback line in the backend window, then retry.' }
        backend_start_failed               = @{ Label = 'Backend failed to start'; Section = 'backend_start_failed'; DefaultCause = 'The backend process never reached a healthy state.'; DefaultFix = 'Check dependencies, port usage, and the backend window error.' }
        frontend_port_conflict             = @{ Label = 'Frontend port conflict'; Section = 'frontend_port_conflict'; DefaultCause = 'Port 5173 is already in use by another program.'; DefaultFix = 'Close the process using port 5173, then retry.' }
        frontend_start_unhealthy           = @{ Label = 'Frontend started but never became ready'; Section = 'frontend_start_unhealthy'; DefaultCause = 'The frontend dev server opened, but runtime-access.json never became available.'; DefaultFix = 'Check the first error line in the frontend window, then retry.' }
        frontend_start_failed              = @{ Label = 'Frontend failed to start'; Section = 'frontend_start_failed'; DefaultCause = 'The frontend process never reached a usable state.'; DefaultFix = 'Check dependencies, port usage, and the frontend window error.' }
    }

    if ($catalog.ContainsKey($Category)) {
        return $catalog[$Category]
    }

    return @{
        Label        = 'Unknown launcher error'
        Section      = 'general'
        DefaultCause = 'The launcher hit an uncategorized error.'
        DefaultFix   = 'Send the failure summary and detailed log to AI or the maintainer.'
    }
}

function Get-ShortText {
    param([string[]]$Values, [string]$Fallback)

    if ($Values -and $Values.Count -gt 0) {
        return (($Values | Where-Object { $_ -and $_.Trim() } | Select-Object -First 1) -as [string])
    }

    return $Fallback
}

function Get-FailureSummaryText {
    param(
        [string]$ModeLabel,
        [string]$StepName,
        [string]$Detail,
        [string]$Category,
        [string[]]$PossibleCauses,
        [string[]]$Suggestions,
        [string]$CommandLine,
        [string]$LogExcerpt
    )

    $errorInfo = Get-ErrorTypeInfo -Category $Category
    $mostLikelyCause = Get-ShortText -Values $PossibleCauses -Fallback $errorInfo.DefaultCause
    $suggestedFix = Get-ShortText -Values $Suggestions -Fallback $errorInfo.DefaultFix
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('Training Platform launcher failure summary') | Out-Null
    $lines.Add(('Time: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))) | Out-Null
    $lines.Add(('Mode: {0}' -f $ModeLabel)) | Out-Null
    $lines.Add(('Failed step: {0}' -f $StepName)) | Out-Null
    $lines.Add(('Error type: {0}' -f $errorInfo.Label)) | Out-Null
    $lines.Add(('Error code: {0}' -f $Category)) | Out-Null
    $lines.Add(('Most likely cause: {0}' -f $mostLikelyCause)) | Out-Null
    $lines.Add(('Suggested fix: {0}' -f $suggestedFix)) | Out-Null
    if ($Detail) {
        $lines.Add(('Failure detail: {0}' -f $Detail)) | Out-Null
    }
    if ($CommandLine) {
        $lines.Add(('Failed command: {0}' -f $CommandLine)) | Out-Null
    }
    $lines.Add(('Detailed log: {0}' -f $LastDetailLogFile)) | Out-Null
    $lines.Add(('Troubleshooting doc: {0} (see section/code: {1})' -f $TroubleshootingDoc, $errorInfo.Section)) | Out-Null
    if ($LogExcerpt) {
        $lines.Add('Recent log lines:') | Out-Null
        foreach ($line in (($LogExcerpt -split "`r?`n") | Select-Object -Last 8)) {
            $lines.Add((' - {0}' -f $line)) | Out-Null
        }
    }
    return ($lines -join [Environment]::NewLine)
}

function Get-SuccessSummaryText {
    param(
        [string]$ModeLabel,
        [string]$Headline,
        [string]$Detail
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('Training Platform launcher success summary') | Out-Null
    $lines.Add(('Time: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))) | Out-Null
    $lines.Add(('Mode: {0}' -f $ModeLabel)) | Out-Null
    $lines.Add(('Result: {0}' -f $Headline)) | Out-Null
    $lines.Add(('Detail: {0}' -f $Detail)) | Out-Null
    $lines.Add(('Access URL: {0}' -f $AccessUrl)) | Out-Null
    $lines.Add(('Detailed log: {0}' -f $LastDetailLogFile)) | Out-Null
    return ($lines -join [Environment]::NewLine)
}

function Write-SummaryFile {
    param([string]$Content)

    Ensure-SummaryDirectory
    $encoding = Get-Utf8BomEncoding
    [System.IO.File]::WriteAllText($SummaryFile, $Content, $encoding)
    [System.IO.File]::WriteAllText($TimestampedSummaryFile, $Content, $encoding)
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
    Write-LauncherLog -Message ("FAIL | {0} | {1} | {2}" -f $StepName, $Category, $Detail) -Level 'ERROR'
    $summary = Get-FailureSummaryText `
        -ModeLabel $Mode `
        -StepName $StepName `
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
    Write-Host ('Error type: {0}' -f (Get-ErrorTypeInfo -Category $Category).Label) -ForegroundColor Yellow
    if ($Suggestions -and $Suggestions.Count -gt 0) {
        Write-Host ''
        Write-Host 'Suggested fixes:' -ForegroundColor Yellow
        foreach ($suggestion in $Suggestions) {
            Write-Host (' - {0}' -f $suggestion)
        }
    }

    Write-Host ''
    Write-Host ('Copyable summary saved to: {0}' -f $SummaryFile) -ForegroundColor Yellow
    Write-Host ('Detailed log saved to   : {0}' -f $LastDetailLogFile) -ForegroundColor Yellow
    Write-Host ('Troubleshooting guide    : {0}' -f $TroubleshootingDoc) -ForegroundColor Yellow
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
                ('Enable the PATH option during installation, then run {0} again.' -f $RetryLauncherFile)
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
                    ('Delete backend\.venv manually if it still exists, then rerun {0}.' -f $RetryLauncherFile)
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
                ('If the problem repeats, delete backend\.venv and rerun {0}.' -f $RetryLauncherFile)
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
                ('Close the program using port 8000, then run {0} again.' -f $RetryLauncherFile),
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
                    ('Run {0} again after fixing the backend error.' -f $RetryLauncherFile),
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
                ('Close the program using port 5173, then run {0} again.' -f $RetryLauncherFile),
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
                ('Run {0} again after fixing the frontend error.' -f $RetryLauncherFile),
                'If needed, send the summary file and the frontend window error to the maintainer.'
            )
    }

    $script:FrontendState = 'started_new_window'
    $script:AccessUrl = $frontendInfo.AccessUrl
}

function Finish-Launcher {
    param([string]$Headline, [string]$Detail)

    Add-StepResult -Name $Headline -Status 'OK' -Detail $Detail

    Write-LauncherLog -Message ("SUCCESS | {0} | {1}" -f $Headline, $Detail)
    $summary = Get-SuccessSummaryText `
        -ModeLabel $Mode `
        -Headline $Headline `
        -Detail $Detail

    Write-SummaryFile -Content $summary

    Write-Host ''
    Write-Host '[OK] Launcher finished successfully.' -ForegroundColor Green
    Write-Host ('Summary saved to: {0}' -f $SummaryFile) -ForegroundColor Green
    Write-Host ('Detailed log saved to: {0}' -f $LastDetailLogFile) -ForegroundColor Green
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
Ensure-SummaryDirectory
$encoding = Get-Utf8BomEncoding
[System.IO.File]::WriteAllText($DetailLogFile, '', $encoding)
[System.IO.File]::WriteAllText($LastDetailLogFile, '', $encoding)
Write-LauncherLog -Message ("LAUNCHER START | mode={0} | root={1}" -f $Mode, $RootDir)

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
