@echo off
setlocal

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%~dp0scripts\local_dev.py" --venv .venv start %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%~dp0scripts\local_dev.py" --venv .venv start %*
  exit /b %ERRORLEVEL%
)

echo [FAIL] Neither "py" nor "python" is available in PATH.
echo        Install Python 3.11+ and rerun start.cmd
exit /b 1
