@echo off
SETLOCAL
cd /d "%~dp0"

echo Activating virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found at .venv\Scripts\activate.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Starting SimplyNarrated application...
echo URL: http://localhost:8010
start http://localhost:8010
python -m uvicorn src.main:app --reload --port 8010

pause
ENDLOCAL
