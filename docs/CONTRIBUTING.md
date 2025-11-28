# 贡献指南

感谢你考虑为 AI 面试助手做出贡献！

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请创建一个 Issue，包含：

1. **问题描述**: 清晰描述遇到的问题
2. **复现步骤**: 详细的复现步骤
3. **期望行为**: 你期望发生什么
4. **实际行为**: 实际发生了什么
5. **环境信息**: 
   - 操作系统版本
   - Node.js 版本
   - Python 版本
   - 应用版本

### 建议新功能

1. 先检查是否已有相关 Issue
2. 创建新 Issue，说明：
   - 功能描述
   - 使用场景
   - 预期效果

### 提交代码

1. **Fork 项目**
   ```bash
   git clone https://github.com/your-username/ai-interview-assistant.git
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **进行修改**
   - 遵循现有代码风格
   - 添加必要的注释
   - 测试你的更改

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加某某功能"
   ```

5. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**

## 代码规范

### JavaScript/TypeScript

- 使用 2 空格缩进
- 使用分号
- 使用单引号
- 遵循 ESLint 规则

### Python

- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 添加类型注解
- 编写文档字符串

### 提交信息

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

示例：
```
feat: 添加区域截图功能
fix: 修复悬浮窗位置错误
docs: 更新使用指南
```

## 开发流程

### 前端开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建
npm run build
```

### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python start.py
```

### 测试

目前项目还没有自动化测试，欢迎添加！

计划添加：
- 单元测试
- 集成测试
- E2E 测试

## 项目结构

```
├── electron/          # Electron 主进程
├── src/              # React 前端
│   ├── App.tsx       # 主界面
│   ├── Overlay.tsx   # 悬浮窗
│   └── ...
├── backend/          # Python 后端
│   ├── main.py       # FastAPI 应用
│   ├── vision.py     # 视觉分析
│   └── ...
├── resources/        # 资源文件
└── ...
```

## 需要帮助的领域

- 🎨 UI/UX 设计改进
- 🐛 Bug 修复
- 📚 文档完善
- 🌍 多语言支持
- 🧪 测试覆盖
- ⚡ 性能优化
- 🔒 安全增强

## 行为准则

- 尊重他人
- 保持友好
- 接受建设性批评
- 关注对项目最有利的事情

## 许可证

贡献的代码将采用项目的 MIT 许可证。

---

**感谢你的贡献！** 🙏






