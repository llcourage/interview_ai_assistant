# 🔧 Vercel 自动部署问题排查

## 问题：Push 到 GitHub 后 Vercel 没有自动构建

### 可能原因和解决方案：

## 1. 检查 Vercel 项目是否连接到 GitHub

### 步骤：
1. 登录 [Vercel Dashboard](https://vercel.com/dashboard)
2. 进入你的项目
3. 点击 **Settings** → **Git**
4. 检查 **Connected Git Repository**

### 如果没有连接：
1. 点击 **Connect Git Repository**
2. 选择 GitHub
3. 授权访问
4. 选择仓库：`llcourage/interview_ai_assistant`
5. 点击 **Import**

## 2. 检查自动部署设置

### 步骤：
1. **Settings** → **Git**
2. 确认 **Production Branch** 是 `main`
3. 确认 **Auto-deploy** 已启用

### 如果未启用：
- 启用 **Deploy Hooks** 和 **Automatic deployments from Git**

## 3. 检查 Root Directory 设置

### 步骤：
1. **Settings** → **General**
2. **Root Directory** 应该设置为：
   - `.` (点号)
   - 或者 **留空**（默认根目录）

### 如果设置错误：
- 改为 `.` 或留空
- 保存设置
- 手动触发一次部署

## 4. 手动触发部署

### 方法 1：通过 Vercel Dashboard
1. 进入项目
2. 点击 **Deployments** 标签
3. 点击 **Redeploy** 按钮
4. 选择最新的 commit（`56ac746`）
5. 点击 **Redeploy**

### 方法 2：通过 Vercel CLI
```bash
# 安装 Vercel CLI（如果还没安装）
npm i -g vercel

# 登录
vercel login

# 部署
vercel --prod
```

## 5. 检查 GitHub Webhook

### 步骤：
1. 在 GitHub 仓库页面
2. 点击 **Settings** → **Webhooks**
3. 检查是否有 Vercel 的 webhook
4. 如果没有，Vercel 会在连接仓库时自动创建

### 如果 Webhook 存在但有问题：
1. 在 Vercel Dashboard → **Settings** → **Git**
2. 点击 **Disconnect** 然后重新连接

## 6. 检查构建配置

### 在 Vercel Dashboard → **Settings** → **General**：

- **Framework Preset**: `Other` 或 `Vite`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`
- **Root Directory**: `.` (或留空)

## 7. 查看部署日志

### 步骤：
1. 进入 Vercel Dashboard
2. 点击 **Deployments**
3. 查看最新的部署记录
4. 点击查看日志，检查是否有错误

## 快速修复步骤

1. ✅ **确认 Root Directory = `.`** (Settings → General)
2. ✅ **确认 Git 连接正常** (Settings → Git)
3. ✅ **手动触发一次部署** (Deployments → Redeploy)
4. ✅ **检查构建日志** 看是否有错误

## 如果还是不行

### 尝试重新连接仓库：
1. **Settings** → **Git** → **Disconnect**
2. 重新 **Connect Git Repository**
3. 选择仓库并导入
4. 确认所有设置正确

### 或者使用 Vercel CLI 部署：
```bash
vercel --prod
```

