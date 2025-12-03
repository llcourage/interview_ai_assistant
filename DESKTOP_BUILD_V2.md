# Desktop Version Build Guide (V2)

This guide explains how to build the DesktopAI desktop version using:
- PyInstaller (onedir mode) for backend
- C# Launcher
- Inno Setup installer

## Architecture

The desktop version consists of:

1. **Backend** - Python backend packaged with PyInstaller in `onedir` mode
2. **Launcher.exe** - C# launcher that starts backend and opens browser
3. **UI/** - Frontend static files
4. **Installer** - Inno Setup installer package

## Build Steps

### 1. Prerequisites

```bash
# Python 3.8+
python --version

# PyInstaller
pip install pyinstaller

# .NET SDK 6.0+
dotnet --version

# Inno Setup (Windows only)
# Download from: https://jrsoftware.org/isdl.php
```

### 2. Build Backend (onedir mode)

```bash
cd backend
python -m PyInstaller build_backend.spec --clean
```

Output: `dist/backend/backend/` directory containing:
- `backend.exe`
- All dependency files (DLLs, Python libraries, etc.)

### 3. Build C# Launcher

```bash
cd launcher
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```

Output: `bin/Release/net6.0/win-x64/publish/Launcher.exe`

### 4. Build Frontend

```bash
npm run build
```

Output: `dist/` directory with static files

### 5. Organize Release Files

Create `release_root/` directory structure:

```
release_root/
├── Launcher.exe          # C# launcher
├── backend/               # Backend directory (from PyInstaller)
│   ├── backend.exe
│   └── [dependencies]
└── ui/                    # Frontend static files
    ├── index.html
    └── assets/
```

### 6. Create Installer (Inno Setup)

1. Open Inno Setup Compiler
2. Open `installer/DesktopAI.iss`
3. Click "Build" → "Compile"
4. Output: `installer/Output/DesktopAI-Setup-1.0.0.exe`

## Automated Build Script

Use the automated build script:

**Windows:**
```bash
scripts\build-desktop-v2.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/build-desktop-v2.sh
./scripts/build-desktop-v2.sh
```

The script will:
1. Build frontend
2. Build backend (onedir mode)
3. Build C# Launcher
4. Organize release files
5. Create installer (if Inno Setup is installed)

## File Structure

### Backend (onedir mode)

```
backend/
├── backend.exe           # Main executable
├── python311.dll         # Python runtime
├── _internal/            # Python libraries
│   ├── base_library.zip
│   └── [all dependencies]
└── [other DLLs]
```

### Launcher (C#)

- Single executable: `Launcher.exe`
- Self-contained (includes .NET runtime)
- Finds `backend/backend.exe` in same directory
- Starts backend and opens browser

### Installer

- Creates desktop shortcut
- Installs to `C:\Program Files\DesktopAI\`
- Adds uninstaller
- Optional: Start menu shortcut, desktop icon

## Security

- ✅ No API keys in desktop version
- ✅ All API requests forwarded to Vercel
- ✅ Backend is compiled (not source code)
- ✅ Launcher is compiled (C# binary)

## Distribution

1. Test `Launcher.exe` in `release_root/`
2. Create installer using Inno Setup
3. Upload `DesktopAI-Setup-1.0.0.exe` to website
4. Users download and install

## Troubleshooting

### Backend not starting

- Check `backend/backend.exe` exists
- Check port 8000 is not in use
- Check firewall settings

### Launcher not finding backend

- Ensure `backend/backend.exe` is in `backend/` subdirectory
- Check file permissions

### Installer creation fails

- Ensure Inno Setup is installed
- Check `release_root/` directory structure
- Verify all files exist




