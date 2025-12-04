@echo off
chcp 65001 > nul
title Backend Server - Port 8000 (Check logs here!)
echo ========================================
echo Backend Server Starting...
echo ========================================
echo.
echo This window will show all backend logs.
echo Keep this window open and visible!
echo.
echo When you refresh the Profile page in your browser,
echo you'll see the logs appear here immediately.
echo.
echo ========================================
echo.

REM Ensure we're in the project root directory
REM %~dp0 is the script directory (scripts/), so go up one level to project root
cd /d "%~dp0\.."

REM Set PYTHONPATH
set "BACKEND_DIR=%CD%\backend"
set "PYTHONPATH=%BACKEND_DIR%;%PYTHONPATH%"

echo Starting server with detailed logging...
echo Working directory: %CD%
echo PYTHONPATH: %BACKEND_DIR%
echo.
echo ========================================
echo SERVER LOGS WILL APPEAR BELOW
echo ========================================
echo.

REM Start server with reload enabled
python -m uvicorn backend.main:app --port 8000 --host 127.0.0.1 --reload --reload-dir backend

pause

