# 桌面版打包指南

本指南说明如何将 Desktop AI 打包成桌面版应用程序。

## 架构说明

桌面版包含以下组件：

1. **backend.exe** - 编译后的 Python 后端服务（使用 PyInstaller）
2. **Launcher.exe** - 启动器程序，负责：
   - 启动本地后端服务
   - 打开浏览器访问本地 UI
   - 管理后端进程生命周期
3. **ui/** - 前端静态文件（React 构建产物）

## 安全设计

- ✅ 后端逻辑已编译为 `backend.exe`，不是源码
- ✅ 启动器也是编译后的 `Launcher.exe`
- ✅ API Key 和计费逻辑在云端（Supabase + Stripe），不在本地
- ✅ 本地后端只负责处理请求，所有敏感操作都通过云端 API

## 打包步骤

### 1. 安装依赖

```bash
# 安装 Python 依赖
cd backend
pip install -r requirements.txt
pip install pyinstaller

# 安装前端依赖
cd ..
npm install
```

### 2. 构建前端

```bash
npm run build
```

### 3. 打包后端

```bash
cd backend
python -m PyInstaller build_backend.spec --clean
```

### 4. 打包启动器

```bash
cd launcher
python -m PyInstaller build_launcher.spec --clean
```

### 5. 使用自动化脚本（推荐）

**Windows:**
```bash
scripts\build-desktop.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/build-desktop.sh
./scripts/build-desktop.sh
```

脚本会自动完成所有步骤，最终在 `dist-desktop/Desktop-AI/` 目录生成可分发文件。

## 文件结构

打包后的目录结构：

```
Desktop-AI/
├── Launcher.exe          # 启动器（双击运行）
├── backend.exe           # 后端服务（已编译）
├── ui/                   # 前端静态文件
│   ├── index.html
│   ├── assets/
│   └── ...
└── README.txt            # 使用说明
```

## 分发

1. 将 `AI-Interview-Assistant-Desktop` 目录压缩为 ZIP
2. 上传到网站（如 https://www.desktopai.org/）
3. 提供下载链接

## 用户使用流程

1. 用户从网站下载 ZIP 文件
2. 解压到任意目录
3. 双击 `Launcher.exe`
4. 启动器自动：
   - 启动后端服务（backend.exe）
   - 等待后端就绪
   - 打开浏览器访问 http://127.0.0.1:8000
5. 用户正常使用应用

## 技术细节

### 后端打包

- 使用 PyInstaller 将 Python 代码打包成单个可执行文件
- 包含所有依赖（FastAPI, uvicorn, OpenAI 等）
- 支持静态文件服务（提供前端 UI）

### 前端配置

- 自动检测本地桌面版模式（通过 URL 判断）
- 如果访问 `http://127.0.0.1:8000`，自动使用本地后端
- 否则使用云端 API

### 启动器功能

- 启动后端进程
- 监控后端健康状态
- 自动打开浏览器
- 优雅关闭后端进程

## 故障排除

### 后端启动失败

- 检查防火墙是否阻止本地连接
- 确认端口 8000 未被占用
- 查看启动器控制台输出的错误信息

### 浏览器无法打开

- 手动访问 http://127.0.0.1:8000
- 检查后端是否正常启动（查看启动器窗口）

### 打包文件过大

- 使用 `--onefile` 模式（已在 spec 文件中配置）
- 考虑使用 UPX 压缩（已启用）
- 排除不必要的依赖

## 注意事项

1. **环境变量**：桌面版需要从系统环境变量或配置文件读取敏感信息（如 Supabase keys），不要硬编码
2. **路径问题**：确保所有相对路径正确
3. **依赖管理**：PyInstaller 可能遗漏某些隐式导入，需要在 spec 文件中手动添加
4. **测试**：打包后务必在干净的 Windows 系统上测试

## 更新流程

1. 修改代码
2. 重新运行打包脚本
3. 测试新版本
4. 上传新的 ZIP 文件
5. 更新网站下载链接




