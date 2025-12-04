@echo off
chcp 65001 > nul
echo ======================================
echo 🔑 创建 .env 配置文件
echo ======================================
echo.

REM Ensure we're in the project root directory
REM %~dp0 is the script directory (scripts/), so go up one level to project root
cd /d "%~dp0\.."

cd backend

echo # OpenAI API 配置 > .env
echo OPENAI_API_KEY=your_openai_api_key_here >> .env
echo OPENAI_BASE_URL=https://api.openai.com/v1 >> .env
echo OPENAI_MODEL=gpt-4o >> .env
echo. >> .env
echo # 服务器配置 >> .env
echo HOST=127.0.0.1 >> .env
echo PORT=8000 >> .env

cd ..

echo ✅ .env 文件已创建！
echo 📁 位置: backend\.env
echo.
echo 现在可以运行 start-all.bat 启动应用了！
echo.
pause






