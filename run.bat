@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Setup has not been run. Double-click install.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo App exited with an error. See logs\oneclick-cover.log if available.
  pause
)
