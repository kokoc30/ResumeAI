Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$VenvPython = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$BackendEnv = Join-Path $BackendRoot ".env"
$BackendEnvExample = Join-Path $BackendRoot ".env.example"

$BackendPort = 8000
$FrontendPort = 5500
$FrontendUrl = "http://127.0.0.1:$FrontendPort"
$BackendUrl = "http://127.0.0.1:$BackendPort"
$DocsUrl = "$BackendUrl/docs"
$ChatStatusUrl = "$BackendUrl/api/chat/status"
$OllamaTagsUrl = "http://127.0.0.1:11434/api/tags"

$script:StartedProcesses = @()

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "OK  $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "WARN  $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "ERROR  $Message" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-Truthy {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) {
        return $false
    }
    return "$Value".Trim().ToLowerInvariant() -in @("1", "true", "yes", "y", "on")
}

function Get-NormalizedOllamaMode {
    param([AllowNull()][string]$Mode)

    $normalized = "$Mode".Trim().ToLowerInvariant()
    if ($normalized -in @("local", "cloud")) {
        return $normalized
    }

    return "local"
}

function Test-MissingApiKey {
    param([AllowNull()][string]$Value)

    $cleanValue = "$Value".Trim().ToLowerInvariant()
    if (-not $cleanValue) {
        return $true
    }

    return $cleanValue -in @(
        "your_key_here",
        "your_ollama_api_key_here",
        "<real key>",
        "<real_key>",
        "<your key>",
        "<your_ollama_api_key_here>"
    )
}

function Test-Port {
    param([int]$Port)
    return @(Get-PortProcesses -Port $Port).Count -gt 0
}

function Get-PortProcesses {
    param([int]$Port)

    $connections = @()
    try {
        $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    }
    catch {
        $connections = @()
    }

    $processIds = @(
        $connections |
            Where-Object { $null -ne $_.OwningProcess } |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    $items = @()
    foreach ($processId in $processIds) {
        $processName = "Unknown"
        try {
            $process = Get-Process -Id $processId -ErrorAction Stop
            $processName = $process.ProcessName
        }
        catch {
            $processName = "Unknown"
        }

        $items += [pscustomobject]@{
            Port = $Port
            Id = [int]$processId
            ProcessName = $processName
        }
    }

    return $items
}

function Stop-PortProcessesWithPrompt {
    param(
        [Parameter(Mandatory = $true)][object[]]$PortProcesses
    )

    if ($PortProcesses.Count -eq 0) {
        return
    }

    Write-Warn "One or more required ports are already in use:"
    foreach ($item in $PortProcesses) {
        Write-Host ("  Port {0}: PID {1} ({2})" -f $item.Port, $item.Id, $item.ProcessName) -ForegroundColor Yellow
    }

    $answer = Read-Host "Stop these existing ResumeMatch/dev server processes and continue? [Y/N]"
    if ($answer -notmatch "^(y|yes)$") {
        throw "Startup cancelled. Stop the existing processes or rerun .\start.ps1 and choose Y."
    }

    $uniqueProcessIds = @($PortProcesses | Select-Object -ExpandProperty Id -Unique)
    foreach ($processId in $uniqueProcessIds) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Ok "Stopped PID $processId."
        }
        catch {
            throw "Could not stop PID $processId. Close it manually or run PowerShell with permission to stop that process."
        }
    }

    Start-Sleep -Seconds 1
}

function Stop-ProcessTree {
    param([int]$ProcessId)

    if ($ProcessId -le 0) {
        return
    }

    try {
        $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)
        foreach ($child in $children) {
            Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
        }
    }
    catch {
        # Best-effort cleanup. Stop the parent below even if child lookup fails.
    }

    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        if (-not $process.HasExited) {
            Stop-Process -Id $ProcessId -Force -ErrorAction Stop
        }
    }
    catch {
        # Already stopped.
    }
}

function Stop-StartedProcesses {
    if ($script:StartedProcesses.Count -eq 0) {
        return
    }

    Write-Host ""
    Write-Host "Stopping ResumeMatch AI..." -ForegroundColor Cyan

    foreach ($process in @($script:StartedProcesses)) {
        if ($null -eq $process) {
            continue
        }

        try {
            $process.Refresh()
            if (-not $process.HasExited) {
                Write-Warn ("Stopping PID {0} ({1})" -f $process.Id, $process.ProcessName)
                Stop-ProcessTree -ProcessId $process.Id
            }
        }
        catch {
            # Process may already be gone.
        }
    }

    $script:StartedProcesses = @()
}

function Assert-ProjectReady {
    Write-Section "Checking project"
    if (-not (Test-Path -LiteralPath $BackendRoot -PathType Container)) {
        throw "backend folder was not found. Run this script from the project root."
    }
    if (-not (Test-Path -LiteralPath $FrontendRoot -PathType Container)) {
        throw "frontend folder was not found. Run this script from the project root."
    }
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        throw "backend\.venv\Scripts\python.exe was not found. Run .\setup.ps1 first."
    }
    if (-not (Test-Path -LiteralPath $BackendEnv -PathType Leaf)) {
        if (Test-Path -LiteralPath $BackendEnvExample -PathType Leaf) {
            throw "backend\.env is missing. Run .\setup.ps1 or copy backend\.env.example to backend\.env."
        }
        throw "backend\.env is missing. Run .\setup.ps1 first."
    }

    Write-Ok "Project folders, backend virtual environment, and backend\.env are ready."
}

function Import-BackendEnvForChildProcesses {
    Write-Section "Loading backend environment"

    if (-not (Test-Path -LiteralPath $BackendEnv -PathType Leaf)) {
        Write-Warn "backend\.env was not found. Backend will use code defaults and inherited process environment."
        return
    }

    $lines = Get-Content -LiteralPath $BackendEnv
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or $trimmed -notmatch "=") {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if ($key -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            continue
        }

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$key" -Value $value
    }

    Write-Ok "Loaded backend\.env for child processes."
    if ($env:OLLAMA_MODE) {
        Write-Ok "Configured Ollama mode: $(Get-NormalizedOllamaMode -Mode $env:OLLAMA_MODE)"
    }
    if ($env:OLLAMA_MODEL) {
        Write-Ok "Configured Ollama model: $env:OLLAMA_MODEL"
    }
}

function Ensure-PortsAvailable {
    Write-Section "Checking ports"

    $busyProcesses = @()
    $busyProcesses += @(Get-PortProcesses -Port $BackendPort)
    $busyProcesses += @(Get-PortProcesses -Port $FrontendPort)

    if ($busyProcesses.Count -gt 0) {
        Stop-PortProcessesWithPrompt -PortProcesses $busyProcesses
    }

    $stillBusy = @()
    $stillBusy += @(Get-PortProcesses -Port $BackendPort)
    $stillBusy += @(Get-PortProcesses -Port $FrontendPort)
    if ($stillBusy.Count -gt 0) {
        foreach ($item in $stillBusy) {
            Write-Warn ("Port {0} is still in use by PID {1} ({2})." -f $item.Port, $item.Id, $item.ProcessName)
        }
        throw "Required ports are still busy. Stop those processes and rerun .\start.ps1."
    }

    Write-Ok "Ports $BackendPort and $FrontendPort are available."
}

function Test-OllamaStatus {
    Write-Section "Checking AI chat mode"

    if (-not (Test-Truthy $env:LLM_ENABLED)) {
        Write-Warn "Local AI chat disabled; fallback guidance will be used."
        return
    }

    $mode = Get-NormalizedOllamaMode -Mode $env:OLLAMA_MODE
    if ($env:OLLAMA_MODE -and $mode -ne $env:OLLAMA_MODE.Trim().ToLowerInvariant()) {
        Write-Warn "Invalid OLLAMA_MODE '$env:OLLAMA_MODE'. Treating it as local. Recommended value is local or cloud."
    }

    if ($mode -eq "cloud") {
        if (Test-MissingApiKey $env:OLLAMA_API_KEY) {
            Write-Warn "Ollama Cloud mode selected, but OLLAMA_API_KEY is missing."
        }
        else {
            Write-Ok "Ollama Cloud mode configured."
        }
        return
    }

    try {
        Invoke-RestMethod -Uri $OllamaTagsUrl -TimeoutSec 2 | Out-Null
        Write-Ok "Local Ollama is reachable."
    }
    catch {
        Write-Warn "Local Ollama is not reachable. The app still works, but chat may use fallback/error guidance."
    }
}

function Start-DevProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    Write-Ok ("Starting {0}..." -f $Name)
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow `
        -PassThru

    $script:StartedProcesses += $process
    Write-Ok ("{0} PID: {1}" -f $Name, $process.Id)
    return $process
}

function Wait-ForHttpStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false
}

function Show-ChatStatus {
    try {
        $status = Invoke-RestMethod -Uri $ChatStatusUrl -TimeoutSec 3
        $mode = "local"
        if ($status.PSObject.Properties.Name -contains "mode") {
            $mode = $status.mode
        }
        Write-Ok ("Chat status: llm_enabled={0}, provider={1}, mode={2}, model={3}" -f $status.llm_enabled, $status.provider, $mode, $status.model)
    }
    catch {
        Write-Warn "Chat status endpoint is not reachable yet. The app may still be starting."
    }
}

function Open-FrontendBrowser {
    try {
        Start-Process $FrontendUrl
        Write-Ok "Opened $FrontendUrl in the browser."
    }
    catch {
        Write-Warn "Could not open the browser automatically. Open $FrontendUrl manually."
    }
}

function Show-Urls {
    Write-Section "Local URLs"
    Write-Host "Frontend:    $FrontendUrl" -ForegroundColor White
    Write-Host "Backend:     $BackendUrl" -ForegroundColor White
    Write-Host "API Docs:    $DocsUrl" -ForegroundColor White
    Write-Host "Chat Status: $ChatStatusUrl" -ForegroundColor White
}

function Watch-DevProcesses {
    Write-Host ""
    Write-Host "ResumeMatch AI is running. Press Ctrl+C to stop." -ForegroundColor Green

    while ($true) {
        Start-Sleep -Seconds 2

        foreach ($process in @($script:StartedProcesses)) {
            $process.Refresh()
            if ($process.HasExited) {
                Write-Warn ("Process PID {0} ({1}) exited unexpectedly with code {2}." -f $process.Id, $process.ProcessName, $process.ExitCode)
                throw "A development server stopped. Shutting down the remaining process."
            }
        }
    }
}

try {
    Write-Host "Starting ResumeMatch AI" -ForegroundColor Cyan
    Write-Host "Project root: $ProjectRoot"

    Assert-ProjectReady
    Import-BackendEnvForChildProcesses
    Ensure-PortsAvailable
    Test-OllamaStatus

    Write-Section "Starting servers"
    $backendProcess = Start-DevProcess `
        -Name "backend" `
        -FilePath $VenvPython `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $BackendRoot

    $frontendProcess = Start-DevProcess `
        -Name "frontend" `
        -FilePath $VenvPython `
        -ArgumentList @("-m", "http.server", "$FrontendPort") `
        -WorkingDirectory $FrontendRoot

    if (Wait-ForHttpStatus -Url $FrontendUrl -TimeoutSeconds 25) {
        Write-Ok "Frontend is reachable."
    }
    else {
        Write-Warn "Frontend did not respond yet. It may still be starting."
    }

    if (Wait-ForHttpStatus -Url $DocsUrl -TimeoutSeconds 25) {
        Write-Ok "Backend API docs are reachable."
    }
    else {
        Write-Warn "Backend API docs did not respond yet. It may still be starting."
    }

    Show-ChatStatus
    Show-Urls

    Start-Sleep -Seconds 2
    Open-FrontendBrowser
    Watch-DevProcesses
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}
finally {
    Stop-StartedProcesses
}
