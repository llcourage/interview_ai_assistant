# Launcher - 桌面版启动器

Launcher 是桌面版应用的启动器程序，负责启动本地后端服务并打开浏览器。

## 功能

- ✅ 自动启动后端服务（backend.exe）
- ✅ 监控后端健康状态
- ✅ 自动打开浏览器访问本地 UI
- ✅ 优雅关闭后端进程

## 使用方法

1. 确保 `backend.exe` 和 `Launcher.exe` 在同一目录
2. 确保 `ui/` 目录存在（包含前端静态文件）
3. 双击 `Launcher.exe` 启动

## 打包

使用 PyInstaller 打包：

```bash
cd launcher
python -m PyInstaller build_launcher.spec --clean
```

打包后的 `Launcher.exe` 位于 `dist/launcher/` 目录。

## 技术细节

- 使用 Python 编写，打包为单个 exe 文件
- 通过 subprocess 启动后端进程
- 使用 urllib 检测后端健康状态
- 使用 webbrowser 模块打开浏览器




