@echo off
chcp 65001 > nul
echo ======================================
echo 🔄 更新依赖并重启应用
echo ======================================
echo.

echo [1/3] 安装新的前端依赖（Markdown 支持）...
echo.
call npm install
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✅ 前端依赖安装完成
echo.

echo [2/3] 关闭现有进程...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM electron.exe 2>nul
timeout /t 2 /nobreak > nul
echo.

echo [3/3] 重新启动应用...
echo.
start "AI 面试助手" cmd /k start-all.bat

echo.
echo ======================================
echo ✅ 更新完成！
echo ======================================
echo.
echo 应用已在新窗口启动
echo 现在代码会以格式化的方式显示！
echo.
pause






