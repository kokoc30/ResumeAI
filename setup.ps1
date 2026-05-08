Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$VenvPath = Join-Path $BackendRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$EnvPath = Join-Path $BackendRoot ".env"
$EnvExamplePath = Join-Path $BackendRoot ".env.example"
$DefaultOllamaModel = "llama3.2:1b"
$LocalOllamaBaseUrl = "http://127.0.0.1:11434"
$CloudOllamaBaseUrl = "https://ollama.com/api"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "OK  $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "WARN  $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "ERROR  $Message" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-NvidiaGpuAvailable {
    try {
        if (-not (Test-CommandExists "nvidia-smi")) {
            return $false
        }
        $null = & nvidia-smi 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Show-EmbeddingDeviceHint {
    Write-Step "Embedding device hint"
    try {
        if (Test-NvidiaGpuAvailable) {
            Write-Success "NVIDIA GPU detected. Recommendation: EMBEDDING_DEVICE=auto (uses CUDA when available)."
        }
        else {
            Write-Warn "No NVIDIA GPU detected. Recommendation: EMBEDDING_DEVICE=cpu for predictable startup."
        }
        Write-Host "For Render / cloud CPU deploy, always use EMBEDDING_DEVICE=cpu." -ForegroundColor Cyan
        Write-Host "This is a hint only; backend\.env is not modified automatically." -ForegroundColor DarkGray
    }
    catch {
        Write-Warn "Hardware hint check failed; continuing without changing backend\.env."
    }
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$WorkingDirectory = ""
    )

    $previousLocation = Get-Location
    try {
        if ($WorkingDirectory) {
            Set-Location -LiteralPath $WorkingDirectory
        }

        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE`: $FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        Set-Location -LiteralPath $previousLocation
    }
}

function Get-PreferredPython {
    if (Test-CommandExists "py") {
        $versionOutput = & py -3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return @{
                File = "py"
                PrefixArgs = @("-3")
                Version = ($versionOutput | Select-Object -First 1)
            }
        }
    }

    if (Test-CommandExists "python") {
        $versionOutput = & python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return @{
                File = "python"
                PrefixArgs = @()
                Version = ($versionOutput | Select-Object -First 1)
            }
        }
    }

    return $null
}

function Get-RequirementsPath {
    $candidates = @(
        (Join-Path $BackendRoot "requirements.txt"),
        (Join-Path $ProjectRoot "requirements.txt")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Ensure-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $content = Get-Content -LiteralPath $Path -Raw
    $escapedKey = [regex]::Escape($Key)
    if ($content -notmatch "(?m)^\s*$escapedKey\s*=") {
        Add-Content -LiteralPath $Path -Value "$Key=$Value"
        Write-Success "Added $Key to backend\.env"
    }
}

function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value
    )

    $lines = @(Get-Content -LiteralPath $Path)
    $escapedKey = [regex]::Escape($Key)
    $updated = $false

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$escapedKey\s*=") {
            $lines[$i] = "$Key=$Value"
            $updated = $true
        }
    }

    if ($updated) {
        Set-Content -LiteralPath $Path -Value $lines
    }
    else {
        Add-Content -LiteralPath $Path -Value "$Key=$Value"
    }
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [string]$Default = ""
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $Default
    }

    $escapedKey = [regex]::Escape($Key)
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or $trimmed -notmatch "=") {
            continue
        }
        if ($trimmed -notmatch "^\s*$escapedKey\s*=") {
            continue
        }

        $value = $trimmed.Split("=", 2)[1].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        return $value
    }

    return $Default
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

function Convert-SecureStringToPlainText {
    param([Parameter(Mandatory = $true)][System.Security.SecureString]$SecureString)

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Ensure-BackendEnv {
    if (-not (Test-Path -LiteralPath $EnvPath)) {
        if (Test-Path -LiteralPath $EnvExamplePath) {
            Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
            Write-Success "Created backend\.env from backend\.env.example"
        }
        else {
            throw "backend\.env is missing and backend\.env.example was not found."
        }
    }
    else {
        Write-Success "backend\.env already exists; preserving it."
    }

    Ensure-EnvValue -Path $EnvPath -Key "LLM_ENABLED" -Value "true"
    Ensure-EnvValue -Path $EnvPath -Key "LLM_PROVIDER" -Value "ollama"
    Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_MODE" -Value "local"
    Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_BASE_URL" -Value $LocalOllamaBaseUrl
    Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_MODEL" -Value $DefaultOllamaModel
    Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Value ""
    Ensure-EnvValue -Path $EnvPath -Key "LLM_TIMEOUT_SECONDS" -Value "60"
}

function Test-OllamaModelInstalled {
    param([string]$ModelName)

    $modelList = & ollama list 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Could not read Ollama model list."
        return $false
    }

    $modelListText = ($modelList -join "`n")
    return $modelListText -match "(^|\s)$([regex]::Escape($ModelName))(\s|$)"
}

function Invoke-AiModeSelection {
    Write-Step "AI chat mode"

    $currentEnabled = Get-EnvValue -Path $EnvPath -Key "LLM_ENABLED" -Default "true"
    $currentMode = Get-NormalizedOllamaMode -Mode (Get-EnvValue -Path $EnvPath -Key "OLLAMA_MODE" -Default "local")
    $currentModel = Get-EnvValue -Path $EnvPath -Key "OLLAMA_MODEL" -Default $DefaultOllamaModel
    if (-not $currentModel.Trim()) {
        $currentModel = $DefaultOllamaModel
    }

    if (-not (Test-Truthy $currentEnabled)) {
        Write-Host "Current AI mode: disabled" -ForegroundColor White
    }
    else {
        Write-Host ("Current AI mode: {0}, model={1}" -f $currentMode, $currentModel) -ForegroundColor White
    }

    Write-Host "Choose AI mode: [1] local Ollama  [2] Ollama Cloud API  [3] disabled  [Enter] keep current" -ForegroundColor White
    $choice = Read-Host "Selection"

    switch ($choice.Trim()) {
        "" {
            Write-Success "Keeping current AI mode."
        }
        "1" {
            Set-EnvValue -Path $EnvPath -Key "LLM_ENABLED" -Value "true"
            Set-EnvValue -Path $EnvPath -Key "LLM_PROVIDER" -Value "ollama"
            Set-EnvValue -Path $EnvPath -Key "OLLAMA_MODE" -Value "local"
            Set-EnvValue -Path $EnvPath -Key "OLLAMA_BASE_URL" -Value $LocalOllamaBaseUrl
            Set-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Value ""
            Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_MODEL" -Value $DefaultOllamaModel
            Ensure-EnvValue -Path $EnvPath -Key "LLM_TIMEOUT_SECONDS" -Value "60"
            Write-Success "Configured local Ollama mode."
        }
        "2" {
            Set-EnvValue -Path $EnvPath -Key "LLM_ENABLED" -Value "true"
            Set-EnvValue -Path $EnvPath -Key "LLM_PROVIDER" -Value "ollama"
            Set-EnvValue -Path $EnvPath -Key "OLLAMA_MODE" -Value "cloud"
            Set-EnvValue -Path $EnvPath -Key "OLLAMA_BASE_URL" -Value $CloudOllamaBaseUrl
            Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_MODEL" -Value $DefaultOllamaModel
            Ensure-EnvValue -Path $EnvPath -Key "LLM_TIMEOUT_SECONDS" -Value "60"

            $existingKey = Get-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Default ""
            if (Test-MissingApiKey $existingKey) {
                $secureKey = Read-Host "Enter Ollama API key for backend\.env (leave blank to add later)" -AsSecureString
            }
            else {
                $secureKey = Read-Host "Enter new Ollama API key, or leave blank to keep existing backend\.env key" -AsSecureString
            }

            $plainKey = Convert-SecureStringToPlainText -SecureString $secureKey
            if ($null -eq $plainKey) {
                $plainKey = ""
            }
            if ($plainKey.Trim()) {
                Set-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Value $plainKey.Trim()
                Write-Success "Saved Ollama Cloud API key to backend\.env without displaying it."
            }
            elseif (Test-MissingApiKey $existingKey) {
                Set-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Value ""
                Write-Warn "Cloud mode is selected, but OLLAMA_API_KEY is missing. Add it to backend\.env."
            }
            else {
                Write-Success "Kept existing Ollama Cloud API key in backend\.env."
            }
        }
        "3" {
            Set-EnvValue -Path $EnvPath -Key "LLM_ENABLED" -Value "false"
            Ensure-EnvValue -Path $EnvPath -Key "LLM_PROVIDER" -Value "ollama"
            Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_MODE" -Value "local"
            Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_BASE_URL" -Value $LocalOllamaBaseUrl
            Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_MODEL" -Value $DefaultOllamaModel
            Ensure-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Value ""
            Write-Success "Configured disabled AI chat mode. Resume analysis still works."
        }
        default {
            Write-Warn "Unrecognized selection. Keeping current AI mode."
        }
    }
}

function Test-AiModeSetup {
    Write-Step "Checking configured AI mode"

    $enabled = Get-EnvValue -Path $EnvPath -Key "LLM_ENABLED" -Default "true"
    if (-not (Test-Truthy $enabled)) {
        Write-Warn "Local AI chat disabled; fallback guidance will be used."
        return
    }

    $rawMode = Get-EnvValue -Path $EnvPath -Key "OLLAMA_MODE" -Default "local"
    $mode = Get-NormalizedOllamaMode -Mode $rawMode
    if ($rawMode.Trim() -and $mode -ne $rawMode.Trim().ToLowerInvariant()) {
        Write-Warn "Invalid OLLAMA_MODE '$rawMode'. Treating it as local. Recommended value is local or cloud."
    }

    $modelName = Get-EnvValue -Path $EnvPath -Key "OLLAMA_MODEL" -Default $DefaultOllamaModel
    if (-not $modelName.Trim()) {
        $modelName = $DefaultOllamaModel
    }

    if ($mode -eq "cloud") {
        $apiKey = Get-EnvValue -Path $EnvPath -Key "OLLAMA_API_KEY" -Default ""
        if (Test-MissingApiKey $apiKey) {
            Write-Warn "Cloud mode is selected, but OLLAMA_API_KEY is missing. Add it to backend\.env."
        }
        else {
            Write-Success "Ollama Cloud mode configured."
        }
        return
    }

    if (-not (Test-CommandExists "ollama")) {
        Write-Warn "Ollama is optional. Install it later if you want local AI chatbot responses."
        return
    }

    $versionOutput = & ollama --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Detected Ollama: $($versionOutput | Select-Object -First 1)"
    }
    else {
        Write-Warn "Ollama command was found, but version check failed."
    }

    if (Test-OllamaModelInstalled -ModelName $modelName) {
        Write-Success "Ollama model $modelName is already available."
        return
    }

    Write-Warn "Ollama is installed, but $modelName is missing."
    $answer = Read-Host "Pull it now? [Y/N]"
    if ($answer -match "^(y|yes)$") {
        Invoke-CheckedCommand -FilePath "ollama" -Arguments @("pull", $modelName)
        Write-Success "Pulled Ollama model $modelName."
    }
    else {
        Write-Warn "Skipping model pull. The app still works; chat can use fallback/error guidance if local Ollama is unavailable."
        Write-Warn "Optional higher-quality model for stronger machines: qwen3:4b."
    }
}

function Run-OptionalTests {
    Write-Step "Optional backend tests"
    $answer = Read-Host "Run backend tests now? [Y/N]"
    if ($answer -match "^(y|yes)$") {
        Invoke-CheckedCommand -FilePath $VenvPython -Arguments @("-m", "pytest", "tests", "-v") -WorkingDirectory $BackendRoot
        Write-Success "Backend tests passed."
    }
    else {
        Write-Warn "Skipped backend tests."
    }
}

try {
    Write-Host "ResumeMatch AI setup" -ForegroundColor Cyan
    Write-Host "Project root: $ProjectRoot"

    Write-Step "Checking project folders"
    if (-not (Test-Path -LiteralPath $BackendRoot -PathType Container)) {
        throw "backend folder was not found. Run this script from the project root."
    }
    if (-not (Test-Path -LiteralPath $FrontendRoot -PathType Container)) {
        throw "frontend folder was not found. Run this script from the project root."
    }
    Write-Success "Found backend and frontend folders."

    Write-Step "Checking Python"
    $python = Get-PreferredPython
    if ($null -eq $python) {
        throw "Python was not found. Install Python 3.10+ or 3.11+ and rerun .\setup.ps1."
    }
    Write-Success "Detected Python: $($python.Version)"

    Write-Step "Preparing backend virtual environment"
    if (Test-Path -LiteralPath $VenvPython) {
        Write-Success "backend\.venv already exists."
    }
    else {
        $venvArgs = @($python.PrefixArgs) + @("-m", "venv", $VenvPath)
        Invoke-CheckedCommand -FilePath $python.File -Arguments $venvArgs
        Write-Success "Created backend\.venv."
    }

    Write-Step "Installing backend requirements"
    $requirementsPath = Get-RequirementsPath
    if ($null -eq $requirementsPath) {
        throw "No requirements.txt file was found. Expected backend\requirements.txt."
    }
    Invoke-CheckedCommand -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-CheckedCommand -FilePath $VenvPython -Arguments @("-m", "pip", "install", "-r", $requirementsPath)
    Write-Success "Installed backend requirements from $requirementsPath."

    Write-Step "Preparing backend environment file"
    Ensure-BackendEnv

    Show-EmbeddingDeviceHint

    Invoke-AiModeSelection
    Test-AiModeSetup
    Run-OptionalTests

    Write-Step "Setup complete"
    Write-Success "Next command:"
    Write-Host ".\start.ps1" -ForegroundColor White
}
catch {
    Write-Fail $_.Exception.Message
    exit 1
}
