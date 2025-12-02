# 🔧 Vercel 部署问题修复

## 问题：部署后还是显示旧页面（登录页面）

### 原因分析

Vercel 可能：
1. 没有重新构建最新代码
2. 使用了缓存的旧版本
3. 构建配置不正确

## 解决方案

### 1. 检查 Vercel 项目设置

在 Vercel Dashboard → **Settings** → **General**：

#### Build & Development Settings

- **Framework Preset**: `Other` 或 `Vite`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`
- **Root Directory**: `.` (或留空)

### 2. 清除 Vercel 缓存并重新部署

#### 方法 1：通过 Dashboard
1. 进入项目 → **Deployments**
2. 点击最新的部署记录
3. 点击 **...** → **Redeploy**
4. 勾选 **Use existing Build Cache** 的 **取消勾选**（清除缓存）
5. 点击 **Redeploy**

#### 方法 2：通过 CLI
```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录
vercel login

# 清除缓存并部署
vercel --prod --force
```

### 3. 检查构建日志

1. 进入 **Deployments**
2. 点击最新的部署
3. 查看 **Build Logs**
4. 确认：
   - ✅ `npm run build` 成功执行
   - ✅ `dist` 目录已生成
   - ✅ 没有构建错误

### 4. 验证部署的文件

在 Vercel Dashboard → **Deployments** → 点击部署 → **View Function Logs**

检查是否包含：
- `src/Landing.tsx`
- `src/AppRouter.tsx`
- `src/components/Header.tsx`

### 5. 强制重新构建

如果还是不行，尝试：

1. **删除并重新导入项目**：
   - Settings → General → Delete Project
   - 重新 Import Git Repository
   - 重新配置所有设置

2. **或者使用 Vercel CLI 强制部署**：
   ```bash
   vercel --prod --force --no-cache
   ```

## 快速检查清单

- [ ] Root Directory = `.` (或留空)
- [ ] Build Command = `npm run build`
- [ ] Output Directory = `dist`
- [ ] 最新代码已 push 到 GitHub
- [ ] Vercel 已连接到正确的 GitHub 仓库
- [ ] 清除缓存后重新部署
- [ ] 检查构建日志无错误

## 验证部署

部署成功后，访问：
- `https://your-app.vercel.app/` → 应该显示 Landing Page（YouTube 视频）
- `https://your-app.vercel.app/login` → 应该显示登录页面
- `https://your-app.vercel.app/plans` → 应该显示 Plans 页面

如果 `/` 还是显示登录页面，说明部署的还是旧代码。

