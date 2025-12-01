@echo off
chcp 65001 > nul
echo ======================================
echo 🔥 启动本地 Webhook 测试服务器
echo ======================================
echo.

cd api\webhooks

echo 📦 检查 Python 环境...
python --version
echo.

echo 📦 安装依赖（如果需要）...
pip install -q fastapi uvicorn mangum stripe supabase
echo.

echo 🚀 启动服务器...
echo 📡 服务地址: http://localhost:8001
echo 🔗 Webhook 端点: http://localhost:8001/
echo 📚 健康检查: 在浏览器访问 http://localhost:8001/
echo.
echo 按 Ctrl+C 停止服务器
echo.

python test_local.py

pause

