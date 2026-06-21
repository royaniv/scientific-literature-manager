@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "MAIN_sci_lit_man.py"
) else (
    py "MAIN_sci_lit_man.py"
    if errorlevel 1 python "MAIN_sci_lit_man.py"
)

if errorlevel 1 (
    echo.
    echo The app could not start.
    echo Install the requirements first, then try again:
    echo .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
)
