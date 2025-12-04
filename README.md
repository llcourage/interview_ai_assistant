# Interview Assistant

一个基于 Electron + React + FastAPI 的智能面试助手应用，支持截图分析和对话交互。

## ✨ 功能特性

- 📸 **多截图捕获**：支持连续截图（Ctrl+H），一次分析多张图片
- 🤖 **AI 图片分析**：使用 OpenAI Vision API 分析截图内容
- 💬 **智能对话**：支持基于上下文的连续对话（包含图片分析历史）
- 🎯 **双模式显示**：
  - **穿透模式**：透明悬浮窗，只显示最新对话
  - **专注模式**（Ctrl+S）：不透明窗口，显示完整对话历史，支持文字输入
- 🔄 **会话管理**：自动保存会话历史，Ctrl+N 创建新会话
- ⌨️ **快捷键操作**：全局快捷键控制，无需切换窗口

## 🚀 快速开始

### 1. 安装依赖

运行 `scripts/install.bat` 一键安装所有依赖。

或手动安装：
```bash
# 安装前端依赖
npm install

# 创建 Python 虚拟环境并安装后端依赖
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：
```
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 启动应用

运行 `scripts/start-all.bat` 启动前端和后端。

或手动启动：
```bash
# 启动后端（新终端）
cd backend
venv\Scripts\activate
python start.py

# 启动前端（新终端）
npm run dev
```

## ⌨️ 快捷键

- **Ctrl+H**：截图
- **Ctrl+Enter**：发送截图进行分析
- **Ctrl+D**：清空当前截图
- **Ctrl+S**：切换专注/穿透模式
- **Ctrl+N**：创建新会话
- **Ctrl+B**：显示/隐藏悬浮窗
- **Ctrl+Up/Down**：滚动 AI 回复内容
- **Ctrl+Left/Right**：移动悬浮窗位置

## 📁 项目结构

```
Interview Assistant/
├── src/              # React 前端源代码
│   ├── components/  # 可复用组件
│   ├── lib/         # API 和 Supabase 客户端
│   └── ...
├── backend/         # Python FastAPI 后端
│   ├── main.py      # 主服务
│   ├── vision.py    # Vision API 集成
│   └── ...
├── electron/        # Electron 桌面应用
│   ├── main.js      # 窗口管理和快捷键
│   └── preload.js   # IPC 桥接
├── api/             # Vercel 服务器less 函数
├── launcher/        # C# 启动器
├── scripts/         # 构建和启动脚本
├── docs/            # 项目文档
├── tests/           # 测试相关
└── resources/       # 应用资源
```

详细结构说明请参阅 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

## 🛠️ 开发

```bash
# 前端开发模式
npm run dev

# 后端开发模式
cd backend
python start.py

# 打包应用
scripts/build.bat
```

## 📝 使用说明

详细使用说明请参阅 [快速开始指南](docs/START_HERE.md) 和 [项目结构文档](docs/PROJECT_STRUCTURE.md)

## 📄 许可证

见 [LICENSE](LICENSE)
