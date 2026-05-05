# Run yt_summarizer with Ollama (defaults). Double-click or: powershell -ExecutionPolicy Bypass -File .\run.ps1
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "yt_summarizer — project: $ProjectRoot"

if (-not (Test-Path "$ProjectRoot\.env")) {
    if (Test-Path "$ProjectRoot\.env.example") {
        Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
        Write-Host "Created .env from .env.example (DRY_RUN=1 — summaries print to console only)."
    }
}

python -m pip install -q -r "$ProjectRoot\requirements.txt"

$model = if ($env:OPENAI_MODEL) { $env:OPENAI_MODEL } else { "llama3.2" }
Write-Host "Ensuring Ollama model '$model' is available..."
& ollama pull $model
if ($LASTEXITCODE -ne 0) {
    Write-Warning "ollama pull failed. Start the Ollama app, then run: ollama pull $model"
}

Write-Host "Starting run..."
python "$ProjectRoot\main.py"
exit $LASTEXITCODE
