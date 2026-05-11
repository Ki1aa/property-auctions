@echo off
setlocal EnableExtensions
REM Run Vite dev server from frontend\ (avoids PowerShell execution policy on npm.ps1).
REM Optional: set NPM_CMD=C:\full\path\to\npm.cmd before running, or edit the fallbacks below.

cd /d "%~dp0frontend" 2>nul
if errorlevel 1 (
  echo ERROR: folder "frontend" not found next to this script.
  pause
  exit /b 1
)

if defined NPM_CMD (
  call "%NPM_CMD%" run dev
  exit /b %errorlevel%
)

where npm.cmd >nul 2>&1
if %errorlevel%==0 (
  call npm.cmd run dev
  exit /b %errorlevel%
)

if exist "F:\nodeJS\npm.cmd" (
  call "F:\nodeJS\npm.cmd" run dev
  exit /b %errorlevel%
)

if exist "%ProgramFiles%\nodejs\npm.cmd" (
  call "%ProgramFiles%\nodejs\npm.cmd" run dev
  exit /b %errorlevel%
)

if exist "%ProgramFiles(x86)%\nodejs\npm.cmd" (
  call "%ProgramFiles(x86)%\nodejs\npm.cmd" run dev
  exit /b %errorlevel%
)

echo ERROR: npm.cmd not found. Install Node.js and add to PATH, or:
echo   set NPM_CMD=C:\path\to\npm.cmd
echo then run this .bat again.
pause
exit /b 1
