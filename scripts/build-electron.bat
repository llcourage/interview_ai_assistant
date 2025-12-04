@echo off
REM Build Electron app without code signing

echo Building frontend...
call npm run build
if errorlevel 1 (
    echo Frontend build failed
    exit /b 1
)

echo.
echo Building Electron app (no code signing)...
set CSC_IDENTITY_AUTO_DISCOVERY=false
call electron-builder --win
if errorlevel 1 (
    echo Electron build failed
    exit /b 1
)

echo.
echo Build complete! Check dist-electron folder for the installer.


