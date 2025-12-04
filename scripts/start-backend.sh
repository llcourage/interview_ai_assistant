#!/bin/bash

echo "======================================"
echo "🚀 启动 AI 面试助手后端服务"
echo "======================================"
echo ""

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 当前工作目录: $(pwd)"
echo ""

# 检查是否在正确的目录（应该能看到 backend 文件夹）
if [ ! -f "backend/main.py" ]; then
    echo "❌ 错误：找不到 backend/main.py"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

# 检查虚拟环境（先检查项目根目录，再检查 backend 目录）
if [ -f "venv/bin/activate" ]; then
    echo "✓ 找到虚拟环境（项目根目录），正在激活..."
    source venv/bin/activate
elif [ -f "backend/venv/bin/activate" ]; then
    echo "✓ 找到虚拟环境（backend 目录），正在激活..."
    source backend/venv/bin/activate
else
    echo "ℹ️ 未找到虚拟环境"
    echo "建议创建虚拟环境：python -m venv venv"
    echo ""
fi

# 检查是否存在 .env 文件
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/env.example" ]; then
        echo "⚠️  未找到 .env 文件，正在从 env.example 创建..."
        cp backend/env.example backend/.env
        echo "✓ .env 文件已创建"
        echo "⚠️  请编辑 backend/.env 文件，填入你的配置信息"
        echo ""
    fi
fi

# 设置 PYTHONPATH，添加 backend 目录以便模块导入
BACKEND_DIR="$(pwd)/backend"
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

# 启动服务
echo "🔥 正在启动后端服务..."
echo "📍 使用模块路径: backend.main:app"
echo "📂 PYTHONPATH 已包含: $BACKEND_DIR"
echo ""
uvicorn backend.main:app --port 8000














