@echo off
chcp 65001 > nul
echo ======================================
echo 📦 AI 面试助手 - 依赖安装
echo ======================================
echo.

echo [1/2] 安装前端依赖...
echo.
call npm install
if errorlevel 1 (
    echo ❌ 前端依赖安装失败
    pause
    exit /b 1
)
echo ✓ 前端依赖安装完成
echo.

echo [2/2] 安装后端依赖...
echo.
cd backend

REM 创建虚拟环境
if not exist venv (
    echo 📝 创建 Python 虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        echo 请确保已安装 Python 3.8+
        cd ..
        pause
        exit /b 1
    )
    echo ✓ 虚拟环境创建成功
)

REM 激活虚拟环境并安装依赖
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 后端依赖安装失败
    cd ..
    pause
    exit /b 1
)

REM 创建 .env 文件
if not exist .env (
    if exist env.example (
        copy env.example .env > nul
        echo ✓ .env 配置文件已创建
    )
)

cd ..

echo.
echo ======================================
echo ✅ 安装完成！
echo ======================================
echo.
echo 下一步：
echo 1. 编辑 backend\.env 文件，填入你的 OPENAI_API_KEY
echo 2. 运行 start-all.bat 启动应用
echo.
pause









