# 🚀 快速开始指南

## 5 分钟上手 AI 面试助手

### 📋 前提条件

确保你已安装：
- ✅ Node.js 18+ ([下载](https://nodejs.org/))
- ✅ Python 3.8+ ([下载](https://www.python.org/downloads/))
- ✅ OpenAI API Key ([获取](https://platform.openai.com/api-keys))

### 🎯 三步启动

#### 步骤 1: 安装依赖（首次使用）

双击运行：
```
install.bat
```

或手动执行：
```bash
npm install
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 步骤 2: 配置 API Key

1. 打开 `backend\.env` 文件
2. 找到 `OPENAI_API_KEY=your_openai_api_key_here`
3. 替换为你的真实 API Key：
   ```env
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
   ```
4. 保存文件

#### 步骤 3: 启动应用

双击运行：
```
start-all.bat
```

等待几秒，会自动打开两个窗口：
- 📱 主窗口（显示详细信息）
- 🎯 悬浮窗（右上角，永远置顶）

### ⌨️ 开始使用

1. **截图**: 按 `Ctrl+H`
   - 全屏截图会被捕获
   - 悬浮窗显示截图缩略图

2. **AI 分析**: 按 `Ctrl+Enter`
   - 截图发送给 AI
   - 等待 2-5 秒
   - 查看 AI 回复

### 🎓 第一次测试

试试这个简单的测试：

1. 打开一个网页或文档
2. 按 `Ctrl+H` 截图
3. 按 `Ctrl+Enter` 分析
4. 查看 AI 的回复

### 📱 界面说明

**悬浮窗（右上角）:**
- 显示最新截图
- 显示 AI 简短回复
- 点击顶部按钮可最小化

**主窗口:**
- 显示完整信息
- 手动操作按钮
- 详细的 AI 回复

### ❓ 遇到问题？

#### 快捷键不工作
→ 重启应用，确保没有其他程序占用快捷键

#### 后端连接失败
→ 检查后端窗口是否在运行，访问 http://127.0.0.1:8000/health

#### API 调用失败
→ 检查 `.env` 文件中的 API Key 是否正确

### 📚 更多帮助

- 📖 [完整文档](README.md)
- 📘 [使用指南](USAGE.md)
- 🔧 [后端文档](backend/README.md)
- 💬 [贡献指南](CONTRIBUTING.md)

### 🎉 完成！

现在你可以开始使用 AI 面试助手了！

**下一步:**
- 尝试截取算法题并分析
- 自定义快捷键（参考 [USAGE.md](USAGE.md)）
- 探索更多功能

---

**提示**: 第一次 API 调用可能需要几秒钟，这是正常的。后续调用会更快。






