#!/bin/bash
# ========================================
# 桌面版打包脚本 (Linux/Mac)
# ========================================

set -e

echo "========================================"
echo "AI Interview Assistant - 桌面版打包"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查 PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[安装] 正在安装 PyInstaller..."
    pip3 install pyinstaller
fi

# 设置路径
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
LAUNCHER_DIR="$PROJECT_ROOT/launcher"
DIST_DIR="$PROJECT_ROOT/dist-desktop"
BUILD_DIR="$PROJECT_ROOT/build-desktop"

echo "[1/5] 清理旧的构建文件..."
rm -rf "$DIST_DIR" "$BUILD_DIR"
mkdir -p "$DIST_DIR" "$BUILD_DIR"

echo "[2/5] 构建前端..."
cd "$PROJECT_ROOT"
npm run build
if [ $? -ne 0 ]; then
    echo "[错误] 前端构建失败"
    exit 1
fi

echo "[3/5] 打包后端 (backend)..."
cd "$BACKEND_DIR"
python3 -m PyInstaller build_backend.spec --clean --distpath "$DIST_DIR/backend" --workpath "$BUILD_DIR/backend"
if [ $? -ne 0 ]; then
    echo "[错误] 后端打包失败"
    exit 1
fi

echo "[4/5] 打包启动器 (Launcher)..."
cd "$LAUNCHER_DIR"
python3 -m PyInstaller build_launcher.spec --clean --distpath "$DIST_DIR/launcher" --workpath "$BUILD_DIR/launcher"
if [ $? -ne 0 ]; then
    echo "[错误] 启动器打包失败"
    exit 1
fi

echo "[5/5] 整理文件..."
# 创建最终分发目录
FINAL_DIR="$DIST_DIR/AI-Interview-Assistant-Desktop"
rm -rf "$FINAL_DIR"
mkdir -p "$FINAL_DIR"

# 复制 backend
cp "$DIST_DIR/backend/backend" "$FINAL_DIR/backend" || cp "$DIST_DIR/backend/backend.exe" "$FINAL_DIR/backend"
chmod +x "$FINAL_DIR/backend"

# 复制 Launcher
cp "$DIST_DIR/launcher/Launcher" "$FINAL_DIR/Launcher" || cp "$DIST_DIR/launcher/Launcher.exe" "$FINAL_DIR/Launcher"
chmod +x "$FINAL_DIR/Launcher"

# 复制前端静态文件
if [ -d "$PROJECT_ROOT/dist" ]; then
    cp -r "$PROJECT_ROOT/dist"/* "$FINAL_DIR/ui/"
else
    echo "[警告] 未找到 dist 目录，请先运行 npm run build"
fi

# 创建 README
cat > "$FINAL_DIR/README.txt" << 'EOF'
AI Interview Assistant - 桌面版
========================================

使用说明:
  1. 运行 ./Launcher 启动应用（Linux/Mac）
     或双击 Launcher.exe（Windows）
  2. 启动器会自动启动后端服务并打开浏览器
  3. 关闭启动器窗口将停止后端服务

文件说明:
  - Launcher: 启动器程序
  - backend: 后端服务程序（已编译）
  - ui/: 前端界面文件

注意事项:
  - 首次运行可能需要几秒钟启动后端服务
  - 请确保防火墙允许本地连接
  - API Key 和计费逻辑在云端，不在本地
EOF

echo ""
echo "========================================"
echo "✅ 打包完成！"
echo "========================================"
echo ""
echo "分发目录: $FINAL_DIR"
echo ""
echo "下一步:"
echo "  1. 测试 Launcher 是否正常工作"
echo "  2. 将 $FINAL_DIR 目录压缩为 ZIP/TAR.GZ"
echo "  3. 上传到网站提供下载"
echo ""

