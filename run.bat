@echo off
title HS Economics Flask Browser & Portal
echo ==========================================================
echo    HS Economics Session Gateway & Browser Launcher
echo ==========================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in your PATH.
    echo Please install Python 3.10+ and check "Add Python to PATH".
    pause
    exit /b 1
)

:: 2. Create virtual environment if it doesn't exist
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment in .venv...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Install or update dependencies
echo [INFO] Verifying dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>nul
.venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: 4. Start the Flask application
echo.
echo ==========================================================
echo [SUCCESS] Starting server at http://127.0.0.1:5000
echo Opening dashboard in your default browser...
echo ==========================================================
echo.

:: Automatically open dashboard after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"

.venv\Scripts\python.exe app.py
pause
