@echo off
REM ========================================
REM Desktop Version Build Script (Windows)
REM Using onedir mode + C# Launcher + Inno Setup
REM ========================================

setlocal enabledelayedexpansion

echo ========================================
echo DesktopAI - Desktop Version Build
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.8+
    pause
    exit /b 1
)

REM Check PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller installation failed
        pause
        exit /b 1
    )
)

REM Check .NET SDK
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] .NET SDK not found, please install .NET 6.0 or later
    pause
    exit /b 1
)

REM Set paths
set PROJECT_ROOT=%~dp0..
set BACKEND_DIR=%PROJECT_ROOT%\backend
set LAUNCHER_DIR=%PROJECT_ROOT%\launcher
set INSTALLER_DIR=%PROJECT_ROOT%\installer
set RELEASE_ROOT=%PROJECT_ROOT%\release_root
set DIST_DIR=%PROJECT_ROOT%\dist-desktop
set BUILD_DIR=%PROJECT_ROOT%\build-desktop

echo [1/7] Cleaning old build files...
if exist "%RELEASE_ROOT%" rmdir /s /q "%RELEASE_ROOT%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%RELEASE_ROOT%"
mkdir "%DIST_DIR%"
mkdir "%BUILD_DIR%"

echo [2/7] Building frontend...
cd /d "%PROJECT_ROOT%"
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)

echo [3/7] Building backend (onedir mode)...
cd /d "%BACKEND_DIR%"
python -m PyInstaller build_backend.spec --clean --distpath "%DIST_DIR%\backend" --workpath "%BUILD_DIR%\backend"
if errorlevel 1 (
    echo [ERROR] Backend build failed
    pause
    exit /b 1
)

REM Check if backend directory was created
if not exist "%DIST_DIR%\backend\backend" (
    echo [ERROR] Backend directory not found in dist
    pause
    exit /b 1
)

echo [4/7] Building C# Launcher...
cd /d "%LAUNCHER_DIR%"
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
if errorlevel 1 (
    echo [ERROR] Launcher build failed
    pause
    exit /b 1
)

REM Find Launcher.exe in publish directory
set LAUNCHER_EXE=
for /r "%LAUNCHER_DIR%\bin\Release\net8.0\win-x64\publish" %%f in (Launcher.exe) do set LAUNCHER_EXE=%%f

if not exist "%LAUNCHER_EXE%" (
    echo [ERROR] Launcher.exe not found
    pause
    exit /b 1
)

echo [5/7] Organizing release files...
REM Copy Launcher.exe
copy "%LAUNCHER_EXE%" "%RELEASE_ROOT%\Launcher.exe" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy Launcher.exe
    pause
    exit /b 1
)

REM Copy backend directory
xcopy /E /I /Y "%DIST_DIR%\backend\backend\*" "%RELEASE_ROOT%\backend\" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy backend files
    pause
    exit /b 1
)

REM Copy frontend static files
if exist "%PROJECT_ROOT%\dist" (
    xcopy /E /I /Y "%PROJECT_ROOT%\dist\*" "%RELEASE_ROOT%\ui\" >nul
) else (
    echo [WARNING] dist directory not found, skipping frontend files
)

echo [6/7] Creating installer with Inno Setup...
cd /d "%INSTALLER_DIR%"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" DesktopAI.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed
        echo Please check the .iss file and Inno Setup installation
        pause
        exit /b 1
    )
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" DesktopAI.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed
        echo Please check the .iss file and Inno Setup installation
        pause
        exit /b 1
    )
) else (
    echo [WARNING] Inno Setup not found, skipping installer creation
    echo Please install Inno Setup and run manually:
    echo   ISCC.exe installer\DesktopAI.iss
)

echo [7/7] Build complete!
echo.
echo ========================================
echo ✅ Build completed successfully!
echo ========================================
echo.
echo Release directory: %RELEASE_ROOT%
echo.
echo Next steps:
echo   1. Test Launcher.exe in %RELEASE_ROOT%
echo   2. If Inno Setup is installed, installer should be in installer\Output\
echo   3. Upload the installer to your website for download
echo.
pause


