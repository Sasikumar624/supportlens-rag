$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")

Write-Host "Building SupportLens RAG index..."
Write-Host "Qdrant must already be running."
& (Join-Path $root ".venv\Scripts\python.exe") -m app.ingestion.index_cli --reset
