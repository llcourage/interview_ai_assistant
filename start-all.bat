@echo off
chcp 65001 > nul
echo ======================================
echo 🔥 AI 面试助手 - 完整启动（Electron 客户端）
echo ======================================
echo.
echo 正在启动后端和前端服务...
echo.

REM 在新窗口启动后端
start "AI 面试助手 - 后端" cmd /k start-backend.bat

REM 等待 3 秒
timeout /t 3 /nobreak > nul

REM 检查是否已安装依赖
if not exist node_modules (
    echo ⚠️  未找到 node_modules，正在安装依赖...
    call npm install
    echo.
)

echo.
echo ✓ 后端服务已在新窗口启动
echo 🚀 正在启动前端开发服务器和 Electron 客户端...
echo.
echo 💡 注意：这将启动 Electron 桌面客户端（包含主窗口和悬浮窗）
echo    而不是网页版。如果需要网页版，请使用浏览器访问 http://localhost:5173
echo.

REM 启动前端开发服务器和 Electron（使用 npm run dev）
call npm run dev











