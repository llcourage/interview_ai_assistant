@echo off
chcp 65001 > nul
echo ======================================
echo 🔥 AI 面试助手 - 完整启动
echo ======================================
echo.
echo 正在启动后端和前端服务...
echo.

REM 在新窗口启动后端
start "AI 面试助手 - 后端" cmd /k start-backend.bat

REM 等待 3 秒
timeout /t 3 /nobreak > nul

REM 在当前窗口启动前端
echo.
echo ✓ 后端服务已在新窗口启动
echo 🚀 正在启动前端...
echo.

call start-frontend.bat






