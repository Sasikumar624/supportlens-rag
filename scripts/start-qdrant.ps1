$ErrorActionPreference = "Stop"

Write-Host "Starting Qdrant on http://localhost:6333"
Write-Host "Keep this window open."
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
