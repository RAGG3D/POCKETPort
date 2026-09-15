@echo off
cd /d "%~dp0"
py -3.12 scripts\install.py
if errorlevel 1 (
  echo Install failed. Install Python 3.12 from python.org, or run Python 3.13 scripts\install.py manually.
  pause
  exit /b 1
)
pause
