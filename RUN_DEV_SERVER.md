# 开发服务器启动指南

## 快速启动（推荐）

使用开发启动脚本：
```batch
start-backend-dev.bat
```

## 手动启动命令

### Windows PowerShell

```powershell
# 1. 切换到项目根目录
cd "D:\codebase\AI Assistant"

# 2. 设置 PYTHONPATH 环境变量（临时）
$env:PYTHONPATH = "$PWD\backend;$env:PYTHONPATH"

# 3. 启动服务（带热重载）
uvicorn backend.main:app --port 8000 --reload --reload-dir backend
```

### Windows CMD

```cmd
cd /d "D:\codebase\AI Assistant"
set "PYTHONPATH=%CD%\backend;%PYTHONPATH%"
uvicorn backend.main:app --port 8000 --reload --reload-dir backend
```

### Linux/Mac Bash

```bash
cd "/path/to/project"
export PYTHONPATH="$(pwd)/backend:$PYTHONPATH"
uvicorn backend.main:app --port 8000 --reload --reload-dir backend
```

## 关键说明

1. **必须在项目根目录运行**（不是 `backend` 目录）
2. **必须设置 PYTHONPATH**，添加 `backend` 目录，这样 Python 才能找到 `vision`、`speech` 等模块
3. **使用 `--reload-dir backend`** 限制热重载只监视 backend 目录，避免 Windows 路径扫描问题

## 常见错误

### ModuleNotFoundError: No module named 'vision'

**原因**：未设置 PYTHONPATH

**解决**：确保设置了 `PYTHONPATH` 环境变量，包含 `backend` 目录

### Error loading ASGI app. Could not import module 'main'

**原因**：在错误的目录运行（比如在 `backend` 目录下）

**解决**：切换到项目根目录运行

