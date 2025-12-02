# 🔧 Vercel 构建问题排查

## 问题：构建日志显示旧的 Commit

### 发现的问题

日志显示：
```
Cloning github.com/llcourage/interview_ai_assistant (Branch: main, Commit: 567eb17)
```

但最新的 commit 应该是 `76b69de`（包含 Landing Page 的更新）。

### 可能原因

1. **Vercel 没有检测到最新的 push**
2. **GitHub webhook 延迟**
3. **Vercel 项目设置问题**

## 解决方案

### 1. 手动触发部署（推荐）

在 Vercel Dashboard：

1. 进入项目 → **Deployments**
2. 点击 **Create Deployment**
3. 选择：
   - **Branch**: `main`
   - **Commit**: 选择最新的 commit（`76b69de`）
4. 点击 **Deploy**
5. **取消勾选** "Use existing Build Cache"

### 2. 检查 Vercel 项目设置

**Settings** → **Git**：
- 确认 **Production Branch** = `main`
- 确认 **Auto-deploy** 已启用
- 检查 **Connected Git Repository** 是否正确

### 3. 检查 GitHub Webhook

1. 在 GitHub 仓库 → **Settings** → **Webhooks**
2. 检查 Vercel 的 webhook 是否存在
3. 检查最近的 webhook 调用记录
4. 如果 webhook 失败，重新连接仓库

### 4. 使用 Vercel CLI 强制部署

```bash
# 安装 CLI（如果还没安装）
npm i -g vercel

# 登录
vercel login

# 强制部署最新代码
vercel --prod --force
```

### 5. 验证构建配置

在 Vercel Dashboard → **Settings** → **General**：

- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`
- **Root Directory**: `.` (或留空)

## 验证最新代码

确认最新的 commit 包含：
- ✅ `src/Landing.tsx`
- ✅ `src/AppRouter.tsx`
- ✅ `src/components/Header.tsx`
- ✅ `vercel.json` 已更新

## 如果构建成功但页面还是旧的

可能是 CDN 缓存问题：

1. **清除浏览器缓存**
2. **使用无痕模式访问**
3. **等待几分钟**（CDN 缓存更新需要时间）
4. **检查部署的构建产物**：
   - 在 Vercel Dashboard → **Deployments** → 点击部署
   - 查看 **Build Logs** 确认 `dist` 目录包含新文件

## 快速修复步骤

1. ✅ 手动创建部署，选择最新 commit
2. ✅ 清除构建缓存
3. ✅ 等待构建完成
4. ✅ 清除浏览器缓存后访问

