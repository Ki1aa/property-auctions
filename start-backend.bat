@echo off
setlocal EnableExtensions

cd /d "%~dp0backend" 2>nul
if errorlevel 1 (
  echo ERROR: folder "backend" not found next to this script.
  pause
  exit /b 1
)

set PYTHONPATH=%CD%

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause