# 桌面版快速开始

## 📦 打包步骤

### 1. 安装依赖

```bash
# Python 依赖
cd backend
pip install -r requirements.txt
pip install pyinstaller

# 前端依赖
cd ..
npm install
```

### 2. 一键打包

**Windows:**
```bash
scripts\build-desktop.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/build-desktop.sh
./scripts/build-desktop.sh
```

### 3. 获取打包文件

打包完成后，在 `dist-desktop/AI-Interview-Assistant-Desktop/` 目录下：

```
AI-Interview-Assistant-Desktop/
├── Launcher.exe      # 启动器（用户双击这个）
├── backend.exe       # 后端服务（已编译）
├── ui/               # 前端静态文件
│   ├── index.html
│   └── assets/
└── README.txt
```

### 4. 测试

1. 进入 `dist-desktop/AI-Interview-Assistant-Desktop/` 目录
2. 双击 `Launcher.exe`
3. 等待后端启动（约 3-5 秒）
4. 浏览器会自动打开 http://127.0.0.1:8000

### 5. 分发

将整个 `AI-Interview-Assistant-Desktop` 目录压缩为 ZIP，上传到网站提供下载。

## 🔒 安全特性

- ✅ **后端已编译**：`backend.exe` 是编译后的二进制文件，不是 Python 源码
- ✅ **启动器已编译**：`Launcher.exe` 也是编译后的二进制文件
- ✅ **API Key 在云端**：所有敏感配置（OpenAI API Key、Supabase keys、Stripe keys）都在云端，不在本地
- ✅ **计费逻辑在云端**：所有订阅、支付、限流逻辑都在云端服务器

## 🎯 工作原理

1. **用户双击 Launcher.exe**
   - Launcher 启动 `backend.exe` 进程
   - 等待后端服务就绪（检测 `/health` 端点）
   - 打开浏览器访问 `http://127.0.0.1:8000`

2. **后端服务（backend.exe）**
   - 提供 API 服务（`/api/*`）
   - 提供静态文件服务（前端 UI）
   - 所有 API Key 和配置从环境变量读取（云端配置）

3. **前端（ui/ 目录）**
   - 自动检测本地模式（通过 URL 判断）
   - 如果访问 `http://127.0.0.1:8000`，使用本地后端
   - 否则使用云端 API

## 📝 注意事项

1. **环境变量**：桌面版需要从系统环境变量或配置文件读取敏感信息，不要硬编码
2. **端口占用**：确保 8000 端口未被占用
3. **防火墙**：首次运行可能需要允许本地连接
4. **路径问题**：确保 `backend.exe`、`Launcher.exe` 和 `ui/` 目录在同一文件夹

## 🐛 故障排除

### 后端启动失败

- 检查控制台输出的错误信息
- 确认端口 8000 未被占用
- 检查防火墙设置

### 浏览器无法打开

- 手动访问 http://127.0.0.1:8000
- 检查后端是否正常启动

### 前端无法加载

- 确认 `ui/` 目录存在且包含 `index.html`
- 检查浏览器控制台的错误信息

## 📚 更多信息

详细文档请参考 [DESKTOP_BUILD.md](./DESKTOP_BUILD.md)

