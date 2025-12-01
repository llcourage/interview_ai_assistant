#!/bin/bash

echo "========================================"
echo "🧹 清理临时文件"
echo "========================================"
echo ""

echo "[1/5] 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name "*.pyc" -exec rm -rf {} + 2>/dev/null
echo "✅ 已清理 Python 缓存"

echo ""
echo "[2/5] 清理 Python 编译文件..."
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
find . -type f -name "*.pyd" -delete 2>/dev/null
echo "✅ 已清理 Python 编译文件"

echo ""
echo "[3/5] 清理 Node.js 缓存..."
rm -rf node_modules/.cache 2>/dev/null
rm -rf .vite 2>/dev/null
echo "✅ 已清理 Node.js 缓存"

echo ""
echo "[4/5] 清理构建文件..."
rm -rf dist 2>/dev/null
rm -rf dist-electron 2>/dev/null
rm -rf build 2>/dev/null
rm -rf out 2>/dev/null
echo "✅ 已清理构建文件"

echo ""
echo "[5/5] 清理日志文件..."
find . -type f -name "*.log" -delete 2>/dev/null
find . -type f -name "*.log.*" -delete 2>/dev/null
echo "✅ 已清理日志文件"

echo ""
echo "========================================"
echo "✅ 清理完成！"
echo "========================================"
echo ""
echo "提示: 检查 .gitignore 确保敏感文件不会被提交"
echo ""

