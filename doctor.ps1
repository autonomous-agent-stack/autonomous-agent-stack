Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\doctor.py --port 8001
