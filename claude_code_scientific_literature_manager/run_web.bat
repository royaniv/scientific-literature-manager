@echo off
cd /d "%~dp0"
"%~dp0..\.venv\Scripts\pip.exe" install flask --quiet 2>nul
"%~dp0..\.venv\Scripts\python.exe" main.py --web
pause
