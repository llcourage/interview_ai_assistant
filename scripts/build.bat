@echo off
chcp 65001 > nul
echo ======================================
echo 📦 AI 面试助手 - 打包构建
echo ======================================
echo.

echo [1/2] 构建前端...
echo.
call npm run build
if errorlevel 1 (
    echo ❌ 前端构建失败
    pause
    exit /b 1
)
echo ✓ 前端构建完成
echo.

echo [2/2] 打包 Electron 应用...
echo.
call npm run package
if errorlevel 1 (
    echo ❌ Electron 打包失败
    pause
    exit /b 1
)
echo ✓ Electron 打包完成
echo.

echo ======================================
echo ✅ 构建完成！
echo ======================================
echo.
echo 安装包位置: dist-electron\
echo.
pause









