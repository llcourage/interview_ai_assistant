# 🔧 Vercel API 404 问题排查

## ✅ 已完成的修复

1. **添加了 GET 端点**：现在可以用浏览器访问 `https://www.desktopai.org/api/webhooks/stripe` 进行健康检查
2. **更新了 Vercel 配置**：添加了 `runtime: python3.11` 明确指定 Python 版本

## 🔍 排查步骤

### 1. 等待 Vercel 重新部署

代码已推送，等待 Vercel 自动部署（通常 1-2 分钟）。

### 2. 测试健康检查端点

部署完成后，访问：
```
https://www.desktopai.org/api/webhooks/stripe
```

**预期响应**（GET 请求）：
```json
{
  "status": "ok",
  "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events.",
  "endpoint": "/api/webhooks/stripe",
  "methods": ["POST"]
}
```

### 3. 如果还是 404，检查以下内容：

#### A. 检查 Vercel 部署状态

1. 进入 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目
3. 查看 **Deployments** 标签
4. 确认最新的部署是否成功（绿色 ✅）

#### B. 检查构建日志

在 Vercel Dashboard → **Deployments** → 点击最新部署 → **Build Logs**

查找：
- ✅ Python 函数是否成功构建
- ✅ `api/index.py` 是否被识别
- ❌ 是否有错误信息

#### C. 检查文件结构

确保项目根目录有以下文件：
```
项目根目录/
├── api/
│   ├── index.py          ✅ 必须存在
│   └── requirements.txt   ✅ 必须存在
├── backend/
│   └── main.py           ✅ 必须存在
└── vercel.json           ✅ 必须存在
```

#### D. 检查 Vercel 函数配置

在 Vercel Dashboard → **Settings** → **Functions**

确认：
- Python 版本：3.11
- 函数超时：30 秒
- `api/index.py` 是否出现在函数列表中

### 4. 手动触发重新部署

如果自动部署没有触发：

1. 在 Vercel Dashboard → **Deployments**
2. 点击 **Create Deployment**
3. 选择最新 commit
4. 取消勾选 "Use existing Build Cache"
5. 点击 **Deploy**

### 5. 测试其他 API 端点

测试其他端点是否工作：

```bash
# 健康检查
curl https://www.desktopai.org/api/health

# 或者访问
https://www.desktopai.org/api/health
```

如果 `/api/health` 也返回 404，说明整个 API 路由都有问题。

### 6. 检查 Vercel 项目设置

在 Vercel Dashboard → **Settings** → **General**：

- **Root Directory**: `.` (或留空)
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

## 🚨 常见问题

### Q: 为什么浏览器访问返回 404？

**A**: 
- 之前只有 POST 端点，浏览器访问是 GET 请求
- 现在已经添加了 GET 端点用于健康检查
- 等待 Vercel 重新部署后应该可以访问

### Q: Stripe Webhook 测试失败？

**A**: 
- Stripe 发送的是 POST 请求，不是 GET
- 确保在 Stripe Dashboard 中配置的 URL 是：`https://www.desktopai.org/api/webhooks/stripe`
- 使用 Stripe CLI 或 Dashboard 的 "Send test webhook" 功能测试

### Q: 如何查看 API 日志？

**A**: 
在 Vercel Dashboard → **Functions** → 点击 `api/index.py` → **Logs** 标签

### Q: 如何本地测试？

**A**: 
```bash
# 安装 Vercel CLI
npm i -g vercel

# 在项目根目录运行
vercel dev
```

然后访问 `http://localhost:3000/api/webhooks/stripe`

## 📝 验证清单

部署完成后，验证：

- [ ] 访问 `https://www.desktopai.org/api/webhooks/stripe` 返回 JSON（不是 404）
- [ ] Vercel Dashboard 显示部署成功
- [ ] 构建日志中没有错误
- [ ] `api/index.py` 出现在 Functions 列表中
- [ ] Stripe Dashboard 可以成功发送测试 webhook

## 🔗 相关文件

- `api/index.py` - Vercel Serverless Function 入口
- `backend/main.py` - FastAPI 应用和 Webhook 端点
- `vercel.json` - Vercel 配置文件

