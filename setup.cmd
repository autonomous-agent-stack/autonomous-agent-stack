@echo off
setlocal
set PYTHONPATH=src
set AUTORESEARCH_MODE=minimal

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.lock
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.lock
  exit /b %ERRORLEVEL%
)

echo [FAIL] Neither "py" nor "python" is available in PATH.
echo        Install Python 3.11+ and rerun setup.cmd
exit /b 1
