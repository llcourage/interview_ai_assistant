@echo off
echo ========================================
echo 🧹 清理临时文件
echo ========================================
echo.

echo [1/5] 清理 Python 缓存...
if exist backend\__pycache__ (
    rmdir /s /q backend\__pycache__
    echo ✅ 已删除 backend\__pycache__
)

if exist __pycache__ (
    rmdir /s /q __pycache__
    echo ✅ 已删除 __pycache__
)

echo.
echo [2/5] 清理 Python 编译文件...
del /s /q backend\*.pyc 2>nul
del /s /q *.pyc 2>nul
echo ✅ 已清理 .pyc 文件

echo.
echo [3/5] 清理 Node.js 缓存...
if exist node_modules\.cache (
    rmdir /s /q node_modules\.cache
    echo ✅ 已删除 node_modules\.cache
)

if exist .vite (
    rmdir /s /q .vite
    echo ✅ 已删除 .vite
)

echo.
echo [4/5] 清理构建文件...
if exist dist (
    rmdir /s /q dist
    echo ✅ 已删除 dist
)

if exist dist-electron (
    rmdir /s /q dist-electron
    echo ✅ 已删除 dist-electron
)

if exist build (
    rmdir /s /q build
    echo ✅ 已删除 build
)

echo.
echo [5/5] 清理日志文件...
del /s /q *.log 2>nul
del /s /q *.log.* 2>nul
echo ✅ 已清理日志文件

echo.
echo ========================================
echo ✅ 清理完成！
echo ========================================
echo.
echo 提示: 检查 .gitignore 确保敏感文件不会被提交
echo.

pause






