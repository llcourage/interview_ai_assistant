@echo off
REM ========================================
REM Setup MSIX Certificate (One-Click)
REM ========================================
REM This script generates and installs a self-signed certificate
REM for MSIX package signing
REM
REM Run this script as Administrator

echo ========================================
echo Setup MSIX Certificate
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo [INFO] This will:
echo   1. Generate a self-signed certificate
echo   2. Install it to Trusted Root Certification Authorities
echo.
pause

echo.
echo [1/2] Generating certificate...
powershell -ExecutionPolicy Bypass -File "%~dp0generate-certificate.ps1"
if errorlevel 1 (
    echo [ERROR] Certificate generation failed
    pause
    exit /b 1
)

echo.
echo [2/2] Installing certificate...
powershell -ExecutionPolicy Bypass -File "%~dp0install-certificate.ps1"
if errorlevel 1 (
    echo [ERROR] Certificate installation failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Certificate setup complete!
echo ========================================
echo.
echo You can now install MSIX packages without errors.
echo.
pause







