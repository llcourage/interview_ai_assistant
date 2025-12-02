@echo off
chcp 65001 > nul
echo ======================================
echo Starting AI Assistant Backend Server
echo ======================================
echo.

REM Ensure we're in the project root directory
cd /d "%~dp0"

echo Current directory: %CD%
echo.

REM Check if we're in the right directory
if not exist backend\main.py (
    echo ERROR: backend\main.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Check for virtual environment
if exist venv\Scripts\activate.bat (
    echo Found virtual environment, activating...
    call venv\Scripts\activate.bat
) else if exist backend\venv\Scripts\activate.bat (
    echo Found virtual environment in backend, activating...
    call backend\venv\Scripts\activate.bat
) else (
    echo INFO: No virtual environment found
    echo Consider creating one: python -m venv venv
    echo.
)

REM Set PYTHONPATH to include backend directory
set "BACKEND_DIR=%CD%\backend"
set "PYTHONPATH=%BACKEND_DIR%;%PYTHONPATH%"

echo Starting server...
echo Module path: backend.main:app
echo PYTHONPATH includes: %BACKEND_DIR%
echo Port: 8000
echo.
echo ======================================
echo SERVER LOGS WILL APPEAR BELOW
echo ======================================
echo.

REM Start server in FOREGROUND so logs are visible
uvicorn backend.main:app --port 8000 --reload --reload-dir backend

pause
