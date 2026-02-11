@echo off
SETLOCAL EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   SimplyNarrated - One-Click Installer
echo ============================================================
echo.

REM -------------------------------------------------------
REM  Step 1: GPU / CUDA Selection
REM -------------------------------------------------------
echo Select your GPU to install the correct PyTorch version:
echo.
echo   1) NVIDIA RTX 50 series  (Blackwell)       - CUDA 12.8
echo   2) NVIDIA RTX 30/40 series (Ampere / Ada)   - CUDA 12.6
echo   3) CPU only (no GPU acceleration)
echo.
set /p GPU_CHOICE="Enter choice (1/2/3): "

if "%GPU_CHOICE%"=="1" (
    set "CUDA_URL=https://download.pytorch.org/whl/cu128"
    set "GPU_LABEL=CUDA 12.8 (RTX 50 series)"
) else if "%GPU_CHOICE%"=="2" (
    set "CUDA_URL=https://download.pytorch.org/whl/cu126"
    set "GPU_LABEL=CUDA 12.6 (RTX 30/40 series)"
) else if "%GPU_CHOICE%"=="3" (
    set "CUDA_URL=https://download.pytorch.org/whl/cpu"
    set "GPU_LABEL=CPU only"
) else (
    echo Invalid choice. Please run the installer again.
    pause
    exit /b 1
)

echo.
echo Selected: %GPU_LABEL%
echo.

REM -------------------------------------------------------
REM  Step 2: Download & Extract Python 3.12 Embedded
REM -------------------------------------------------------
set "PY_DIR=python_embedded"
set "PY_EXE=%PY_DIR%\python.exe"
set "PY_ZIP=python-3.12.9-embed-amd64.zip"
set "PY_URL=https://www.python.org/ftp/python/3.12.9/%PY_ZIP%"

if exist "%PY_EXE%" (
    echo [OK] Python embedded already found at %PY_DIR%\
) else (
    echo Downloading Python 3.12 embedded package...
    curl -L -o "%PY_ZIP%" "%PY_URL%"
    if errorlevel 1 (
        echo ERROR: Failed to download Python. Check your internet connection.
        pause
        exit /b 1
    )

    echo Extracting Python...
    mkdir "%PY_DIR%" 2>nul
    tar -xf "%PY_ZIP%" -C "%PY_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to extract Python archive.
        pause
        exit /b 1
    )

    del "%PY_ZIP%"
    echo [OK] Python 3.12 embedded extracted to %PY_DIR%\
)

REM -------------------------------------------------------
REM  Step 3: Patch ._pth file to enable site-packages
REM -------------------------------------------------------
set "PTH_FILE=%PY_DIR%\python312._pth"

if exist "%PTH_FILE%" (
    findstr /C:"import site" "%PTH_FILE%" >nul 2>&1
    if errorlevel 1 (
        echo import site>> "%PTH_FILE%"
        echo [OK] Patched %PTH_FILE% to enable site-packages
    ) else (
        REM Check if it's commented out
        findstr /C:"#import site" "%PTH_FILE%" >nul 2>&1
        if not errorlevel 1 (
            powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site','import site' | Set-Content '%PTH_FILE%'"
            echo [OK] Uncommented import site in %PTH_FILE%
        ) else (
            echo [OK] site-packages already enabled
        )
    )
) else (
    echo WARNING: %PTH_FILE% not found. Packages may not be discoverable.
)

REM -------------------------------------------------------
REM  Step 4: Bootstrap pip
REM -------------------------------------------------------
"%PY_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Installing pip...
    curl -L -o "%PY_DIR%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py"
    if errorlevel 1 (
        echo ERROR: Failed to download get-pip.py.
        pause
        exit /b 1
    )
    "%PY_EXE%" "%PY_DIR%\get-pip.py" --no-warn-script-location
    if errorlevel 1 (
        echo ERROR: Failed to install pip.
        pause
        exit /b 1
    )
    del "%PY_DIR%\get-pip.py"
    echo [OK] pip installed
) else (
    echo [OK] pip already available
)

REM -------------------------------------------------------
REM  Step 5: Install PyTorch
REM -------------------------------------------------------
echo.
echo Installing PyTorch (%GPU_LABEL%)...
echo This may take several minutes depending on your connection.
echo.
"%PY_EXE%" -m pip install torch torchvision torchaudio --index-url %CUDA_URL% --no-warn-script-location
if errorlevel 1 (
    echo ERROR: PyTorch installation failed.
    pause
    exit /b 1
)
echo [OK] PyTorch installed

REM -------------------------------------------------------
REM  Step 6: Install project dependencies
REM -------------------------------------------------------
echo.
echo Installing project dependencies...
"%PY_EXE%" -m pip install -r requirements.txt --no-warn-script-location
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)
echo [OK] All dependencies installed

REM -------------------------------------------------------
REM  Done!
REM -------------------------------------------------------
echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo   To start SimplyNarrated, double-click:  run.bat
echo   Or run:  .\python_embedded\python.exe -m uvicorn src.main:app --reload --port 8010
echo   Then open:  http://localhost:8010
echo.
pause
ENDLOCAL
