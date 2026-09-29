$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "frontend")

Write-Host "Starting frontend on http://localhost:3000"
Write-Host "Keep this window open."
npm run dev
