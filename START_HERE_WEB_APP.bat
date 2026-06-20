@echo off
setlocal

cd /d "%~dp0"

echo Starting the Scientific Literature Manager web app...
echo.
echo Open this address in your browser:
echo http://127.0.0.1:5000
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m literature_manager.web_app
) else (
    py -m literature_manager.web_app
    if errorlevel 1 python -m literature_manager.web_app
)

if errorlevel 1 (
    echo.
    echo The web app could not start.
    echo Install the requirements first, then try again:
    echo .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
)
