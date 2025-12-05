@echo off
REM ========================================
REM 桌面版打包脚本 (Windows)
REM ========================================

setlocal enabledelayedexpansion

echo ========================================
echo Desktop AI - 桌面版打包
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查 PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

REM 设置路径
set PROJECT_ROOT=%~dp0..
set BACKEND_DIR=%PROJECT_ROOT%\backend
set LAUNCHER_DIR=%PROJECT_ROOT%\launcher
set DIST_DIR=%PROJECT_ROOT%\dist-desktop
set BUILD_DIR=%PROJECT_ROOT%\build-desktop

echo [1/5] 清理旧的构建文件...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%DIST_DIR%"
mkdir "%BUILD_DIR%"

echo [2/5] 构建前端...
cd /d "%PROJECT_ROOT%"
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)

echo [3/5] 打包后端 (backend.exe)...
cd /d "%BACKEND_DIR%"
python -m PyInstaller build_backend.spec --clean --distpath "%DIST_DIR%\backend" --workpath "%BUILD_DIR%\backend"
if errorlevel 1 (
    echo [错误] 后端打包失败
    pause
    exit /b 1
)

echo [4/5] 打包启动器 (Launcher.exe)...
cd /d "%LAUNCHER_DIR%"
python -m PyInstaller build_launcher.spec --clean --distpath "%DIST_DIR%\launcher" --workpath "%BUILD_DIR%\launcher"
if errorlevel 1 (
    echo [错误] 启动器打包失败
    pause
    exit /b 1
)

echo [5/5] 整理文件...
REM 创建最终分发目录
set FINAL_DIR=%DIST_DIR%\Desktop-AI
if exist "%FINAL_DIR%" rmdir /s /q "%FINAL_DIR%"
mkdir "%FINAL_DIR%"

REM 复制 backend.exe
copy "%DIST_DIR%\backend\backend.exe" "%FINAL_DIR%\backend.exe" >nul
if errorlevel 1 (
    echo [错误] 复制 backend.exe 失败
    pause
    exit /b 1
)

REM 复制 Launcher.exe
copy "%DIST_DIR%\launcher\Launcher.exe" "%FINAL_DIR%\Launcher.exe" >nul
if errorlevel 1 (
    echo [错误] 复制 Launcher.exe 失败
    pause
    exit /b 1
)

REM 复制前端静态文件
if exist "%PROJECT_ROOT%\dist" (
    xcopy /E /I /Y "%PROJECT_ROOT%\dist\*" "%FINAL_DIR%\ui\" >nul
) else (
    echo [警告] 未找到 dist 目录，请先运行 npm run build
)

REM 创建 README
(
echo Desktop AI - 桌面版
echo ========================================
echo.
echo 使用说明:
echo   1. 双击 Launcher.exe 启动应用
echo   2. 启动器会自动启动后端服务并打开浏览器
echo   3. 关闭启动器窗口将停止后端服务
echo.
echo 文件说明:
echo   - Launcher.exe: 启动器程序
echo   - backend.exe: 后端服务程序（已编译）
echo   - ui/: 前端界面文件
echo.
echo 注意事项:
echo   - 首次运行可能需要几秒钟启动后端服务
echo   - 请确保防火墙允许本地连接
echo   - API Key 和计费逻辑在云端，不在本地
echo.
) > "%FINAL_DIR%\README.txt"

echo.
echo ========================================
echo ✅ 打包完成！
echo ========================================
echo.
echo 分发目录: %FINAL_DIR%
echo.
echo 下一步:
echo   1. 测试 Launcher.exe 是否正常工作
echo   2. 将 %FINAL_DIR% 目录压缩为 ZIP
echo   3. 上传到网站提供下载
echo.
pause

