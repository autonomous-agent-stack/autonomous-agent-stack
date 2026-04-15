Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"
$env:AUTORESEARCH_MODE = "minimal"

.\.venv\Scripts\python.exe -m uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8001
