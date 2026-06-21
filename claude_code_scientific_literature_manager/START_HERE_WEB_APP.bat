@echo off
setlocal

cd /d "%~dp0"

echo Starting the Scientific Literature Manager web app...
echo.
echo Open this address in your browser:
echo http://127.0.0.1:5000
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m web_app.app
) else (
    py -m web_app.app
    if errorlevel 1 python -m web_app.app
)

if errorlevel 1 (
    echo.
    echo The web app could not start.
    echo Install the requirements first, then try again:
    echo .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
)
