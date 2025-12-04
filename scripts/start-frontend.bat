@echo off
chcp 65001 > nul
echo ======================================
echo 🚀 启动 AI 面试助手前端
echo ======================================
echo.

REM Ensure we're in the project root directory
REM %~dp0 is the script directory (scripts/), so go up one level to project root
cd /d "%~dp0\.."

REM 检查是否已安装依赖
if not exist node_modules (
    echo ⚠️  未找到 node_modules，正在安装依赖...
    call npm install
    echo.
)

echo 🔥 正在启动前端开发服务器...
echo.
call npm run dev

pause















