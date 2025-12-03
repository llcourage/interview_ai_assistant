#!/bin/bash
# ========================================
# Desktop Version Build Script (Linux/Mac)
# Using onedir mode + C# Launcher + Inno Setup
# ========================================

set -e

echo "========================================"
echo "DesktopAI - Desktop Version Build"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found, please install Python 3.8+"
    exit 1
fi

# Check PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[INSTALL] Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Check .NET SDK
if ! command -v dotnet &> /dev/null; then
    echo "[ERROR] .NET SDK not found, please install .NET 6.0 or later"
    exit 1
fi

# Set paths
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
LAUNCHER_DIR="$PROJECT_ROOT/launcher"
INSTALLER_DIR="$PROJECT_ROOT/installer"
RELEASE_ROOT="$PROJECT_ROOT/release_root"
DIST_DIR="$PROJECT_ROOT/dist-desktop"
BUILD_DIR="$PROJECT_ROOT/build-desktop"

echo "[1/7] Cleaning old build files..."
rm -rf "$RELEASE_ROOT" "$DIST_DIR" "$BUILD_DIR"
mkdir -p "$RELEASE_ROOT" "$DIST_DIR" "$BUILD_DIR"

echo "[2/7] Building frontend..."
cd "$PROJECT_ROOT"
npm run build
if [ $? -ne 0 ]; then
    echo "[ERROR] Frontend build failed"
    exit 1
fi

echo "[3/7] Building backend (onedir mode)..."
cd "$BACKEND_DIR"
python3 -m PyInstaller build_backend.spec --clean --distpath "$DIST_DIR/backend" --workpath "$BUILD_DIR/backend"
if [ $? -ne 0 ]; then
    echo "[ERROR] Backend build failed"
    exit 1
fi

# Check if backend directory was created
if [ ! -d "$DIST_DIR/backend/backend" ]; then
    echo "[ERROR] Backend directory not found in dist"
    exit 1
fi

echo "[4/7] Building C# Launcher..."
cd "$LAUNCHER_DIR"
dotnet publish -c Release -r linux-x64 --self-contained true -p:PublishSingleFile=true
if [ $? -ne 0 ]; then
    echo "[ERROR] Launcher build failed"
    exit 1
fi

# Find Launcher executable
LAUNCHER_EXE=$(find "$LAUNCHER_DIR/bin/Release/net8.0/linux-x64/publish" -name "Launcher" -type f | head -1)

if [ -z "$LAUNCHER_EXE" ]; then
    echo "[ERROR] Launcher executable not found"
    exit 1
fi

echo "[5/7] Organizing release files..."
# Copy Launcher
cp "$LAUNCHER_EXE" "$RELEASE_ROOT/Launcher"
chmod +x "$RELEASE_ROOT/Launcher"

# Copy backend directory
cp -r "$DIST_DIR/backend/backend"/* "$RELEASE_ROOT/backend/"

# Copy frontend static files
if [ -d "$PROJECT_ROOT/dist" ]; then
    cp -r "$PROJECT_ROOT/dist"/* "$RELEASE_ROOT/ui/"
else
    echo "[WARNING] dist directory not found, skipping frontend files"
fi

echo "[6/7] Note: Inno Setup is Windows-only"
echo "   For Linux/Mac, create a tar.gz or AppImage instead"

echo "[7/7] Build complete!"
echo ""
echo "========================================"
echo "✅ Build completed successfully!"
echo "========================================"
echo ""
echo "Release directory: $RELEASE_ROOT"
echo ""
echo "Next steps:"
echo "  1. Test Launcher in $RELEASE_ROOT"
echo "  2. Create distribution package (tar.gz, AppImage, etc.)"
echo "  3. Upload to your website for download"
echo ""


