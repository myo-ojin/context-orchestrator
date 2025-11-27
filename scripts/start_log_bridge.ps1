# Context Orchestrator Log Bridge Auto-Start
# This script starts the log bridge in the background if it's not already running

# Detect project root (where this script is located)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

# Auto-detect paths
$logBridgePath = Join-Path $projectRoot "scripts\log_bridge.py"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

# Fallback to .venv311 if .venv doesn't exist
if (-not (Test-Path $pythonPath)) {
    $pythonPath = Join-Path $projectRoot ".venv311\Scripts\python.exe"
}

# Allow override via environment variable
if ($env:CONTEXT_ORCHESTRATOR_ROOT) {
    $projectRoot = $env:CONTEXT_ORCHESTRATOR_ROOT
    $logBridgePath = Join-Path $projectRoot "scripts\log_bridge.py"
}

# Log file location
$logFile = "$env:LOCALAPPDATA\context-orchestrator\log_bridge.log"

# Validate paths
if (-not (Test-Path $logBridgePath)) {
    Write-Host "[Context Orchestrator] Error: log_bridge.py not found at $logBridgePath" -ForegroundColor Red
    Write-Host "Set CONTEXT_ORCHESTRATOR_ROOT environment variable or ensure script is in project root" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $pythonPath)) {
    Write-Host "[Context Orchestrator] Error: Python not found at $pythonPath" -ForegroundColor Red
    Write-Host "Ensure virtual environment is set up (.venv or .venv311)" -ForegroundColor Yellow
    exit 1
}

# Check if log bridge is already running
$existingProcess = Get-Process -Name python -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*log_bridge.py*" }

if ($existingProcess) {
    Write-Host "[Context Orchestrator] Log bridge already running (PID: $($existingProcess.Id))" -ForegroundColor Green
} else {
    # Ensure log directory exists
    $logDir = Split-Path -Parent $logFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    # Start log bridge in background
    Start-Process -FilePath $pythonPath `
                  -ArgumentList $logBridgePath `
                  -WindowStyle Hidden `
                  -RedirectStandardOutput $logFile `
                  -RedirectStandardError "$logFile.err"

    Write-Host "[Context Orchestrator] Log bridge started successfully" -ForegroundColor Green
    Write-Host "  Log file: $logFile" -ForegroundColor Gray
}
