@echo off
setlocal
set PYTHONPATH=src
.venv\Scripts\python.exe scripts\doctor.py --port 8001
