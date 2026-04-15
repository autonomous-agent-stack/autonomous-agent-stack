Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& .\doctor.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$proc = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @(
    "-m",
    "uvicorn",
    "autoresearch.api.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8001"
) -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds 5
    $resp = Invoke-RestMethod "http://127.0.0.1:8001/health"
    if ($resp.status -ne "ok") {
        throw "health check failed"
    }
    Write-Host "Windows smoke passed"
} finally {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}
