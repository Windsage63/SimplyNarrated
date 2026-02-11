@echo off
SETLOCAL
cd /d "%~dp0"

echo Starting SimplyNarrated...

if not exist "python_embedded\python.exe" (
    echo ERROR: Python embedded not found. Please run install.bat first.
    pause
    exit /b 1
)

echo URL: http://localhost:8010
start http://localhost:8010
.\python_embedded\python.exe -m uvicorn src.main:app --reload --port 8010

pause
ENDLOCAL
