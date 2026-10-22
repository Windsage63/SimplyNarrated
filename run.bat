@echo off
SETLOCAL
cd /d "%~dp0"

echo Starting SimplyNarrated...

if not exist "python_embedded\python.exe" (
    echo ERROR: Python embedded not found. Please run install.bat first.
    pause
    exit /b 1
)

REM Do not leave multiple servers competing for the same local address.
.\python_embedded\python.exe -c "import socket, sys; s = socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1', 8010)) == 0 else 1)"
if not errorlevel 1 (
    echo Port 8010 is already in use. Close the existing SimplyNarrated server before starting again.
    pause
    exit /b 1
)

echo URL: http://localhost:8010
echo Press Ctrl+C in this window to stop SimplyNarrated.
REM Model progress bars must not depend on a live terminal output pipe.
set HF_HUB_DISABLE_PROGRESS_BARS=1
start http://localhost:8010
.\python_embedded\python.exe -m uvicorn src.main:app --port 8010

ENDLOCAL
