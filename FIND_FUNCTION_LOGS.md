# 🔍 如何找到 Vercel Function Logs

## 📍 查找 Function Logs 的步骤

### 方法 1：通过部署详情页（推荐）

1. **进入部署详情**
   - 在 Vercel Dashboard → 你的项目
   - 点击 **Deployments** 标签
   - 点击最新的部署（最上面的那个）

2. **查看 Functions**
   - 在部署详情页，向下滚动
   - 找到 **Functions** 部分（在 Build Logs 下面）
   - 应该能看到 `api/index.py` 函数
   - 点击函数名称或右侧的 **View Function Logs** 链接

### 方法 2：通过项目设置

1. **进入项目**
   - Vercel Dashboard → 选择项目

2. **查看 Functions 列表**
   - 点击左侧菜单的 **Functions**（如果没有看到，可能在 **Settings** 下面）
   - 或者直接访问：`https://vercel.com/[你的用户名]/[项目名]/functions`

3. **点击函数**
   - 找到 `api/index.py`
   - 点击进入函数详情
   - 在函数详情页，点击 **Logs** 标签

### 方法 3：触发请求后查看

1. **先触发一次请求**
   - 访问：`https://www.desktopai.org/api/webhooks/stripe`
   - 或者使用 curl：
     ```bash
     curl https://www.desktopai.org/api/webhooks/stripe
     ```

2. **等待几秒钟**

3. **查看日志**
   - 按照方法 1 或 2 进入 Functions
   - 现在应该能看到日志了

## 🚨 如果找不到 Functions 选项

### 可能的原因：

1. **函数还没有被调用**
   - 先访问端点触发一次请求
   - 等待 10-30 秒后刷新页面

2. **部署还在进行中**
   - 等待部署完全完成（状态变为 Ready）

3. **函数没有正确部署**
   - 检查 `api/index.py` 是否存在
   - 检查 `vercel.json` 配置是否正确

## 🔍 快速检查清单

1. ✅ 访问 `https://www.desktopai.org/api/webhooks/stripe` 触发请求
2. ✅ 等待 10-30 秒
3. ✅ 进入 Vercel Dashboard → 项目 → Deployments
4. ✅ 点击最新部署
5. ✅ 向下滚动找到 **Functions** 部分
6. ✅ 点击 `api/index.py` 或 **View Function Logs**

## 📸 如果还是找不到

请告诉我：
1. 在部署详情页能看到 **Functions** 部分吗？
2. 能看到 `api/index.py` 函数吗？
3. 点击函数后能看到什么页面？

或者，你可以：
- 截图分享你看到的页面
- 告诉我你在哪个页面，我帮你定位

