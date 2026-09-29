$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")

Write-Host "Starting backend on http://127.0.0.1:8000"
Write-Host "Keep this window open."
& (Join-Path $root ".venv\Scripts\python.exe") -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
