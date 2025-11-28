# 📁 项目结构说明

## 完整目录树

```
AI-Interview-Assistant/
│
├── 📁 electron/                    # Electron 主进程
│   ├── main.js                    # 主进程入口（窗口管理、全局快捷键）
│   └── preload.js                 # 预加载脚本（IPC 桥接）
│
├── 📁 src/                        # React 前端源码
│   ├── main.tsx                   # 前端入口
│   ├── App.tsx                    # 主界面组件
│   ├── App.css                    # 主界面样式
│   ├── Overlay.tsx                # 悬浮窗组件
│   ├── Overlay.css                # 悬浮窗样式
│   ├── index.css                  # 全局样式
│   └── 📁 types/
│       └── window.d.ts            # TypeScript 类型声明
│
├── 📁 backend/                    # FastAPI 后端
│   ├── main.py                    # FastAPI 应用入口
│   ├── vision.py                  # 视觉分析模块（OpenAI API）
│   ├── start.py                   # 启动脚本（带环境检查）
│   ├── requirements.txt           # Python 依赖
│   ├── env.example                # 环境变量模板
│   └── README.md                  # 后端文档
│
├── 📁 resources/                  # 资源文件
│   └── README.md                  # 图标说明
│
├── 📄 package.json                # Node.js 配置和依赖
├── 📄 vite.config.ts              # Vite 构建配置
├── 📄 tsconfig.json               # TypeScript 配置
├── 📄 tsconfig.node.json          # TypeScript Node 配置
├── 📄 index.html                  # HTML 入口
│
├── 🚀 install.bat                 # 一键安装脚本
├── 🚀 start-all.bat               # 一键启动（前端+后端）
├── 🚀 start-backend.bat           # 启动后端
├── 🚀 start-backend.sh            # 启动后端（Linux/Mac）
├── 🚀 start-frontend.bat          # 启动前端
├── 🚀 build.bat                   # 打包构建
│
├── 📖 README.md                   # 项目说明
├── 📖 QUICKSTART.md               # 快速开始
├── 📖 USAGE.md                    # 使用指南
├── 📖 CHANGELOG.md                # 更新日志
├── 📖 CONTRIBUTING.md             # 贡献指南
├── 📖 LICENSE                     # MIT 许可证
│
├── 📄 .gitignore                  # Git 忽略文件
├── 📄 .npmrc                      # npm 配置
└── 📄 .editorconfig               # 编辑器配置
```

## 核心文件说明

### 🎯 Electron 主进程

#### `electron/main.js`
- 创建主窗口和悬浮窗
- 注册全局快捷键（Ctrl+H, Ctrl+Enter）
- 实现截图功能（desktopCapturer）
- IPC 进程间通信

**关键功能：**
```javascript
- createMainWindow()      // 创建主窗口
- createOverlayWindow()   // 创建悬浮窗
- captureScreen()         // 截图功能
- registerShortcuts()     // 注册快捷键
- sendToWindows()         // 广播消息
```

#### `electron/preload.js`
- 暴露安全的 API 给渲染进程
- 隔离 Node.js 和浏览器环境
- 实现 IPC 通信桥接

**暴露的 API：**
```javascript
window.aiShot = {
  onScreenshotTaken()       // 监听截图
  onSendScreenshotRequest() // 监听发送请求
  captureScreen()           // 手动截图
  minimizeOverlay()         // 最小化悬浮窗
}
```

### 🎨 React 前端

#### `src/main.tsx`
- React 应用入口
- 路由配置（HashRouter）
- 根组件渲染

#### `src/App.tsx` - 主界面
- 快捷键说明
- 状态显示
- 截图预览
- 完整 AI 回复
- 手动控制按钮

**状态管理：**
```typescript
- status          // 当前状态
- lastScreenshot  // 最新截图
- aiResponse      // AI 回复
```

#### `src/Overlay.tsx` - 悬浮窗
- 紧凑界面设计
- 截图缩略图
- 简短 AI 回复
- 可折叠/展开

**特点：**
- 永远置顶
- 半透明背景
- 无边框
- 可最小化

### 🔥 FastAPI 后端

#### `backend/main.py`
- FastAPI 应用定义
- CORS 中间件配置
- API 路由定义

**API 端点：**
```python
GET  /              # 根路径
GET  /health        # 健康检查
POST /api/vision_query  # 视觉分析
POST /api/test      # 测试接口
```

#### `backend/vision.py`
- OpenAI Vision API 调用
- 图片分析逻辑
- 错误处理

**核心函数：**
```python
analyze_image()             # 主要分析函数
validate_image_base64()     # 图片验证
analyze_image_with_context() # 带上下文分析
```

#### `backend/start.py`
- 启动脚本
- 环境检查
- 配置验证

## 数据流程

### 截图流程
```
用户按 Ctrl+H
    ↓
Electron 主进程捕获屏幕
    ↓
转换为 Base64
    ↓
通过 IPC 发送到渲染进程
    ↓
React 组件接收并显示
```

### AI 分析流程
```
用户按 Ctrl+Enter
    ↓
React 获取当前截图
    ↓
HTTP POST 到 FastAPI
    ↓
FastAPI 调用 OpenAI API
    ↓
AI 返回分析结果
    ↓
React 显示结果
```

## 通信机制

### IPC 通信（Electron）
```
主进程 → 渲染进程:
  - screenshot-taken        # 截图完成
  - send-screenshot-request # 发送请求
  - screenshot-error        # 截图错误

渲染进程 → 主进程:
  - capture-screen         # 手动截图
  - minimize-overlay       # 最小化
  - show-overlay           # 显示
```

### HTTP 通信（前后端）
```
前端 → 后端:
  POST /api/vision_query
  {
    "image_base64": "...",
    "prompt": "..."
  }

后端 → 前端:
  {
    "answer": "...",
    "success": true,
    "error": ""
  }
```

## 配置文件

### `package.json`
- Node.js 依赖管理
- 脚本命令定义
- Electron Builder 配置

### `vite.config.ts`
- Vite 构建配置
- React 插件
- 开发服务器设置

### `tsconfig.json`
- TypeScript 编译选项
- 类型检查规则
- 模块解析配置

### `backend/.env`
- OpenAI API Key
- API Base URL
- 模型配置
- 服务器配置

## 启动脚本

### `install.bat`
- 安装前端依赖（npm install）
- 创建 Python 虚拟环境
- 安装后端依赖（pip install）
- 创建 .env 配置文件

### `start-all.bat`
- 在新窗口启动后端
- 在当前窗口启动前端
- 一键启动整个应用

### `start-backend.bat`
- 激活虚拟环境
- 检查配置文件
- 启动 FastAPI 服务

### `start-frontend.bat`
- 检查依赖
- 启动 Vite + Electron

### `build.bat`
- 构建前端（npm run build）
- 打包 Electron（electron-builder）
- 生成 Windows 安装包

## 开发工作流

### 开发模式
```bash
# 终端 1: 后端
start-backend.bat

# 终端 2: 前端
start-frontend.bat
```

### 调试
- **前端**: 自动打开 DevTools
- **后端**: http://127.0.0.1:8000/docs
- **日志**: 查看终端输出

### 构建发布
```bash
build.bat
# 输出: dist-electron/
```

## 扩展点

### 添加新的快捷键
→ 修改 `electron/main.js` 的 `registerShortcuts()`

### 修改 UI 样式
→ 编辑 `src/App.css` 和 `src/Overlay.css`

### 添加新的 API 端点
→ 在 `backend/main.py` 中添加路由

### 更换 AI 模型
→ 修改 `backend/.env` 的 `OPENAI_MODEL`

### 自定义分析逻辑
→ 编辑 `backend/vision.py` 的提示词

## 依赖说明

### 前端依赖
- `electron`: 桌面应用框架
- `react`: UI 框架
- `react-router-dom`: 路由管理
- `vite`: 构建工具
- `typescript`: 类型检查

### 后端依赖
- `fastapi`: Web 框架
- `uvicorn`: ASGI 服务器
- `openai`: OpenAI API 客户端
- `pydantic`: 数据验证
- `python-dotenv`: 环境变量管理

## 安全考虑

1. **API Key 保护**
   - 存储在本地 `.env` 文件
   - 不提交到版本控制（.gitignore）

2. **Context Isolation**
   - Electron preload 隔离
   - 不暴露 Node.js API

3. **CORS 配置**
   - 生产环境应限制域名
   - 当前允许所有来源（开发用）

## 性能优化

1. **前端**
   - React 组件缓存
   - 图片懒加载
   - 最小化重渲染

2. **后端**
   - 异步 API 调用
   - 连接池管理
   - 请求超时控制

3. **截图**
   - 适当的缩略图尺寸
   - Base64 编码优化
   - 内存管理

---

更多详细信息请查看各个文件的注释和文档。






