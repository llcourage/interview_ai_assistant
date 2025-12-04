@echo off
chcp 65001 > nul
echo ======================================
echo 🔧 修复后端依赖问题
echo ======================================
echo.

REM Ensure we're in the project root directory
REM %~dp0 is the script directory (scripts/), so go up one level to project root
cd /d "%~dp0\.."

cd backend

if exist venv\Scripts\activate.bat (
    echo ✓ 找到虚拟环境，正在激活...
    call venv\Scripts\activate.bat
    echo.
    echo 🔄 正在重新安装依赖...
    echo.
    pip install --upgrade pip
    pip uninstall -y openai httpx
    pip install -r requirements.txt
    echo.
    echo ✅ 依赖修复完成！
) else (
    echo ❌ 未找到虚拟环境
    echo 请先运行 install.bat
)

cd ..

echo.
echo ======================================
echo 现在可以运行 start-all.bat 启动应用
echo ======================================
pause






