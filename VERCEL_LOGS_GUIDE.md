# 📊 如何查看 Vercel 日志

## 🔍 查看日志的步骤

### 方法 1：通过 Vercel Dashboard（推荐）

1. **登录 Vercel Dashboard**
   - 访问：https://vercel.com/dashboard
   - 使用你的 GitHub 账户登录

2. **选择项目**
   - 在 Dashboard 中找到你的项目（AI Interview Assistant）
   - 点击项目名称进入项目详情页

3. **查看部署日志**
   - 点击顶部的 **Deployments** 标签
   - 找到最新的部署（通常在最上面）
   - 点击部署卡片进入详情页
   - 点击 **Build Logs** 标签查看构建日志

4. **查看函数日志（运行时日志）**
   - 在项目详情页，点击左侧菜单的 **Functions** 选项
   - 找到 `api/index.py` 函数
   - 点击函数名称
   - 在函数详情页，点击 **Logs** 标签
   - 这里会显示所有运行时日志和错误

### 方法 2：通过部署详情页

1. **进入部署详情**
   - 项目详情页 → **Deployments** → 点击最新部署

2. **查看函数日志**
   - 在部署详情页，向下滚动找到 **Functions** 部分
   - 找到 `api/index.py`
   - 点击函数名称或 **View Function Logs** 按钮

### 方法 3：实时查看日志（推荐用于调试）

1. **使用 Vercel CLI**
   ```bash
   # 安装 Vercel CLI
   npm i -g vercel
   
   # 登录
   vercel login
   
   # 查看实时日志
   vercel logs --follow
   ```

2. **查看特定函数的日志**
   ```bash
   vercel logs api/index.py --follow
   ```

## 📋 日志类型说明

### 构建日志（Build Logs）
- **位置**：Deployments → 部署详情 → Build Logs
- **内容**：构建过程中的输出，包括：
  - 依赖安装
  - 构建命令执行
  - 错误和警告

### 函数日志（Function Logs）
- **位置**：Functions → api/index.py → Logs
- **内容**：运行时日志，包括：
  - `print()` 输出
  - 错误堆栈跟踪
  - 请求/响应信息
  - 环境变量检查结果

## 🔍 查找特定错误

### 查找 500 错误

1. 进入 **Functions** → `api/index.py` → **Logs**
2. 在日志中搜索：
   - `ERROR`
   - `Traceback`
   - `500`
   - `INTERNAL_SERVER_ERROR`

### 查找导入错误

在日志中搜索：
- `ModuleNotFoundError`
- `ImportError`
- `TypeError: issubclass`

### 查找环境变量问题

在日志中搜索：
- `not configured`
- `missing`
- `environment variable`

## 📸 截图位置参考

### 在 Vercel Dashboard 中的路径：

```
Vercel Dashboard
└─ 你的项目 (AI Interview Assistant)
   ├─ Deployments (部署列表)
   │  └─ 最新部署
   │     ├─ Build Logs (构建日志) ← 查看构建错误
   │     └─ Functions
   │        └─ api/index.py
   │           └─ Logs (运行时日志) ← 查看运行时错误
   │
   └─ Functions (函数列表)
      └─ api/index.py
         └─ Logs (运行时日志) ← 查看所有请求的日志
```

## 🚨 常见问题

### Q: 找不到 Functions 选项？

**A**: 
- 确保你的项目已经部署
- 确保 `api/` 目录下有 Python 文件
- 在项目设置中检查 **Functions** 是否启用

### Q: 日志是空的？

**A**: 
- 确保有请求触发了函数
- 尝试访问 `https://www.desktopai.org/api/webhooks/stripe` 触发一次请求
- 等待几秒钟后刷新日志页面

### Q: 如何查看历史日志？

**A**: 
- 在 **Functions** → `api/index.py` → **Logs** 中
- 可以查看最近 24 小时的日志
- 更早的日志需要升级到付费计划

### Q: 如何导出日志？

**A**: 
- 使用 Vercel CLI：`vercel logs --output logs.txt`
- 或者复制粘贴日志内容

## 🎯 快速检查清单

访问 `https://www.desktopai.org/api/webhooks/stripe` 后：

1. ✅ 进入 Vercel Dashboard
2. ✅ 选择项目
3. ✅ 进入 Functions → api/index.py → Logs
4. ✅ 查看最新的日志条目
5. ✅ 查找错误信息（红色标记）
6. ✅ 复制错误信息给我

## 📝 需要提供的信息

如果遇到错误，请提供：

1. **错误类型**：500, 404, 或其他
2. **错误消息**：完整的错误文本
3. **堆栈跟踪**：如果有 Traceback
4. **时间戳**：错误发生的时间
5. **请求路径**：`/api/webhooks/stripe`

这样我可以更准确地帮你解决问题！

