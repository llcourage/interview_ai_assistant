@echo off
chcp 65001 > nul
echo ======================================
echo 🚀 启动 AI 面试助手后端服务
echo ======================================
echo.

REM 确保在项目根目录运行（包含 backend 文件夹的目录）
REM 获取脚本所在目录（项目根目录）
cd /d "%~dp0"

echo 📂 当前工作目录: %CD%
echo.

REM 检查是否在正确的目录（应该能看到 backend 文件夹）
if not exist backend\main.py (
    echo ❌ 错误：找不到 backend\main.py
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 检查虚拟环境（先检查项目根目录，再检查 backend 目录）
if exist venv\Scripts\activate.bat (
    echo ✓ 找到虚拟环境（项目根目录），正在激活...
    call venv\Scripts\activate.bat
) else if exist backend\venv\Scripts\activate.bat (
    echo ✓ 找到虚拟环境（backend 目录），正在激活...
    call backend\venv\Scripts\activate.bat
) else (
    echo ℹ️ 未找到虚拟环境
    echo 建议创建虚拟环境：python -m venv venv
    echo.
)

REM 检查是否存在 .env 文件
if not exist backend\.env (
    if exist backend\env.example (
        echo ⚠️  未找到 .env 文件，正在从 env.example 创建...
        copy backend\env.example backend\.env > nul
        echo ✓ .env 文件已创建
        echo ⚠️  请编辑 backend\.env 文件，填入你的配置信息
        echo.
    )
)

REM 设置 PYTHONPATH，添加 backend 目录以便模块导入
REM 注意：使用绝对路径，避免路径问题
set "BACKEND_DIR=%CD%\backend"
set "PYTHONPATH=%BACKEND_DIR%;%PYTHONPATH%"

REM 启动服务
echo 🔥 正在启动后端服务...
echo 📍 使用模块路径: backend.main:app
echo 📂 PYTHONPATH 已包含: %BACKEND_DIR%
echo 🚫 已禁用 --reload（避免 Windows 路径扫描问题）
echo.
uvicorn backend.main:app --port 8000

pause











