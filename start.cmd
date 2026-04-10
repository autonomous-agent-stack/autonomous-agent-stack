@echo off
setlocal
set PYTHONPATH=src
set AUTORESEARCH_MODE=minimal
.venv\Scripts\python.exe -m uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8001
