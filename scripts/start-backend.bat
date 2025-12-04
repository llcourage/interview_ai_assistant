@echo off
chcp 65001 > nul
echo ======================================
echo Starting AI Assistant Backend Server
echo ======================================
echo.

REM Ensure we're in the project root directory
REM %~dp0 is the script directory (scripts/), so go up one level to project root
cd /d "%~dp0\.."

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

REM Check for .env file
if not exist backend\.env (
    if exist backend\env.example (
        echo WARNING: .env file not found, creating from env.example...
        copy backend\env.example backend\.env > nul
        echo .env file created
        echo Please edit backend\.env file and add your configuration
        echo.
    )
)

REM Set PYTHONPATH to project root so backend can be imported as a package
set "PROJECT_ROOT=%CD%"
set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"

REM Start server
echo Starting backend service...
echo Using module path: backend.main:app
echo PYTHONPATH includes: %PROJECT_ROOT%
echo.
uvicorn backend.main:app --port 8000 --host 127.0.0.1

pause




