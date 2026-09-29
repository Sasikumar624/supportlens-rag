$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root ".env"
$examplePath = Join-Path $root ".env.example"

if (!(Test-Path $envPath)) {
    Copy-Item $examplePath $envPath
}

$content = Get-Content $envPath -Raw
if ($content -match "ENABLE_QUERY_PIPELINE=") {
    $content = $content -replace "ENABLE_QUERY_PIPELINE=.*", "ENABLE_QUERY_PIPELINE=true"
} else {
    $content = $content.TrimEnd() + "`r`nENABLE_QUERY_PIPELINE=true`r`n"
}
Set-Content -Path $envPath -Value $content -Encoding UTF8

Write-Host "Ready: .env exists and ENABLE_QUERY_PIPELINE=true"
