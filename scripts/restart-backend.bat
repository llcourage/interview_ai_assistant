@echo off
chcp 65001 > nul
echo ======================================
echo 🔄 重启后端服务（应用新的提示词）
echo ======================================
echo.

REM Ensure we're in the project root directory
REM %~dp0 is the script directory (scripts/), so go up one level to project root
cd /d "%~dp0\.."

echo 正在关闭后端服务...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak > nul

echo.
echo 🚀 启动后端服务...
echo.

cd backend

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python start.py

pause






