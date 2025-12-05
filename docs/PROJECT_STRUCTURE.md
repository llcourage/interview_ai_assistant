# 项目结构文档

本文档详细说明了 Desktop AI 项目的目录结构和组织方式。

## 📁 目录结构

```
Desktop AI/
├── 📂 src/                    # React 前端源代码
│   ├── components/           # 可复用组件
│   │   ├── Header.tsx       # 页面头部组件
│   │   ├── PlanCard.tsx     # 订阅计划卡片
│   │   ├── PlanSelector.tsx # 计划选择器
│   │   ├── Settings.tsx     # 设置组件
│   │   └── Profile/         # 用户资料相关组件
│   ├── lib/                  # 库文件
│   │   ├── api.ts           # API 客户端
│   │   └── supabase.ts      # Supabase 客户端
│   ├── styles/              # 全局样式
│   ├── types/               # TypeScript 类型定义
│   ├── utils/               # 工具函数
│   ├── App.tsx              # 主应用组件
│   ├── AppRouter.tsx        # 路由配置
│   ├── Overlay.tsx          # 桌面悬浮窗组件
│   ├── Landing.tsx          # 首页
│   ├── Login.tsx            # 登录页
│   ├── Plans.tsx            # 订阅计划页
│   ├── Checkout.tsx         # 支付页面
│   ├── Profile.tsx          # 用户资料页
│   └── main.tsx             # 入口文件
│
├── 📂 backend/               # Python FastAPI 后端
│   ├── main.py              # FastAPI 主服务
│   ├── vision.py            # 图片分析模块
│   ├── speech.py            # 语音转文字模块
│   ├── auth_supabase.py     # Supabase 认证
│   ├── db_models.py         # 数据库模型
│   ├── db_operations.py     # 数据库操作
│   ├── db_supabase.py       # Supabase 数据库连接
│   ├── payment_stripe.py    # Stripe 支付集成
│   ├── migrations/          # 数据库迁移脚本
│   ├── requirements.txt     # Python 依赖
│   └── README.md            # 后端文档
│
├── 📂 electron/              # Electron 桌面应用
│   ├── main.js              # Electron 主进程
│   ├── preload.js           # 预加载脚本（IPC 桥接）
│   └── whisper_local.py     # 本地 Whisper 语音识别
│
├── 📂 api/                   # Vercel 服务器less 函数
│   ├── index.py             # API 入口
│   ├── stripe_webhook.py    # Stripe Webhook 处理
│   └── requirements.txt     # API 依赖
│
├── 📂 launcher/              # C# 启动器
│   ├── Launcher.cs          # 启动器主程序
│   ├── Launcher.csproj      # 项目配置
│   └── launcher.py          # Python 启动脚本
│
├── 📂 scripts/               # 构建和启动脚本
│   ├── install.bat          # 安装依赖
│   ├── start-all.bat        # 启动所有服务
│   ├── start-backend.bat    # 启动后端
│   ├── start-frontend.bat   # 启动前端
│   ├── build.bat            # 构建应用
│   └── ...                  # 其他脚本
│
├── 📂 docs/                  # 项目文档
│   ├── PROJECT_STRUCTURE.md # 本文件
│   ├── START_HERE.md        # 快速开始指南
│   ├── DESKTOP_BUILD.md     # 桌面版构建说明
│   ├── STRIPE_SETUP.md      # Stripe 配置说明
│   └── ...                  # 其他文档
│
├── 📂 tests/                 # 测试相关
│   ├── test-desktop/        # 桌面版测试
│   └── test-launcher/       # 启动器测试
│
├── 📂 resources/             # 应用资源
│   └── icon.ico             # 应用图标
│
├── 📂 installer/             # 安装程序
│   └── DesktopAI.iss        # Inno Setup 配置
│
├── 📂 dist/                  # 构建输出目录
│   └── ...                  # 前端构建产物
│
├── 📄 package.json           # 根 package.json（Electron 配置）
├── 📄 vite.config.ts         # Vite 配置
├── 📄 tsconfig.json          # TypeScript 配置
├── 📄 vercel.json            # Vercel 部署配置
├── 📄 README.md              # 项目主文档
└── 📄 LICENSE                # 许可证
```

## 🏗️ 架构说明

### 前端架构
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **路由**: React Router
- **状态管理**: React Hooks + LocalStorage
- **UI 库**: 自定义 CSS（支持主题切换）

### 后端架构
- **框架**: FastAPI (Python)
- **数据库**: Supabase (PostgreSQL)
- **认证**: Supabase Auth
- **支付**: Stripe
- **AI 服务**: OpenAI API

### 桌面应用架构
- **框架**: Electron 28
- **主进程**: Node.js (main.js)
- **渲染进程**: React (复用前端代码)
- **IPC 通信**: Context Isolation + Preload Script

### 部署架构
- **Web 版**: Vercel (服务器less)
- **桌面版**: PyInstaller (后端) + Electron Builder (前端)
- **API**: Vercel Functions

## 🔄 数据流

1. **用户认证流程**
   - 前端 → Supabase Auth → 后端验证 → 返回 Token

2. **AI 请求流程**
   - 桌面/Web → 后端 API → OpenAI API → 返回结果 → 记录使用量

3. **支付流程**
   - 前端 → Stripe Checkout → Webhook → 更新订阅状态

4. **桌面版特殊流程**
   - 桌面版后端 → 转发请求到 Vercel API → 返回结果

## 📝 开发规范

### 文件命名
- **组件**: PascalCase (如 `PlanCard.tsx`)
- **工具函数**: camelCase (如 `isElectron.ts`)
- **样式文件**: 与组件同名 (如 `PlanCard.css`)
- **配置文件**: kebab-case (如 `vite.config.ts`)

### 目录组织
- **组件**: 按功能模块组织，相关文件放在同一目录
- **工具**: 按类型分类（lib, utils, types）
- **文档**: 按主题分类，放在 `docs/` 目录

### 导入路径
- 使用相对路径导入同级或子级文件
- 使用绝对路径（从 `src/` 开始）导入跨模块文件
- 避免深层嵌套的相对路径（如 `../../../`）

## 🔧 配置文件说明

- `package.json`: Electron 构建配置、依赖管理
- `vite.config.ts`: Vite 构建配置
- `tsconfig.json`: TypeScript 编译配置
- `vercel.json`: Vercel 部署配置
- `backend/requirements.txt`: Python 后端依赖
- `api/requirements.txt`: Vercel API 依赖

## 📚 相关文档

- [快速开始指南](START_HERE.md)
- [桌面版构建说明](DESKTOP_BUILD.md)
- [Stripe 配置说明](STRIPE_SETUP.md)
- [后端开发文档](../backend/README.md)

