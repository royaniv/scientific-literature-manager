@echo off
cd /d "%~dp0"
python main.py --web
echo.
echo Server running at http://localhost:5050
pause
