$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "clear-broken-proxy.ps1")
$modelCache = Join-Path $root ".hf-cache"
New-Item -ItemType Directory -Force -Path $modelCache | Out-Null
$env:HF_HOME = $modelCache
$env:TRANSFORMERS_CACHE = $modelCache
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
Set-Location (Join-Path $root "backend")

Write-Host "Starting backend on http://127.0.0.1:8000"
Write-Host "Keep this window open."
& (Join-Path $root ".venv\Scripts\python.exe") -m uvicorn app.main:app --host 127.0.0.1 --port 8000
