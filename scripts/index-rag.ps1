$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "clear-broken-proxy.ps1")
$modelCache = Join-Path $root ".hf-cache"
New-Item -ItemType Directory -Force -Path $modelCache | Out-Null
$env:HF_HOME = $modelCache
$env:TRANSFORMERS_CACHE = $modelCache
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
Set-Location (Join-Path $root "backend")

Write-Host "Building SupportLens RAG index..."
Write-Host "Qdrant must already be running."
& (Join-Path $root ".venv\Scripts\python.exe") -m app.ingestion.index_cli --reset
