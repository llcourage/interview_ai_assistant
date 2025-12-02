#!/bin/bash

echo "======================================"
echo "🚀 启动 AI 面试助手后端服务"
echo "======================================"
echo ""

cd backend

# 检查是否存在虚拟环境
if [ -f "venv/bin/activate" ]; then
    echo "✓ 找到虚拟环境，正在激活..."
    source venv/bin/activate
else
    echo "ℹ️ 未找到虚拟环境"
    echo "建议创建虚拟环境：python -m venv venv"
    echo ""
fi

# 检查是否存在 .env 文件
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "⚠️  未找到 .env 文件，正在从 env.example 创建..."
        cp env.example .env
        echo "✓ .env 文件已创建"
        echo "⚠️  请编辑 backend/.env 文件，填入你的 OPENAI_API_KEY"
        echo ""
    fi
fi

# 启动服务
echo "🔥 正在启动后端服务..."
echo ""
python start.py











