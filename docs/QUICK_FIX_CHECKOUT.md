# ⚡ 快速修复 Checkout 错误

## 🔍 立即检查（按优先级）

### 1️⃣ 检查环境变量（最常见问题）

**在 Vercel Dashboard 中检查**：

1. 访问 https://vercel.com/dashboard
2. 选择你的项目
3. 进入 **Settings** → **Environment Variables**
4. 确认以下变量**都已设置且不是占位符**：

```
✅ STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx  (不是空值或 "your-secret-key-here")
✅ STRIPE_PRICE_NORMAL=price_xxxxxxxxxxxxx  (不是 "price_xxx")
✅ STRIPE_PRICE_HIGH=price_yyyyyyyyyyyyy     (不是 "price_yyy")
```

**如果发现占位符值**：
- 参考 [STRIPE_SETUP.md](./STRIPE_SETUP.md) 获取正确的值
- 更新环境变量
- **重要**：点击 **Save** 后，必须重新部署！

### 2️⃣ 重新部署（环境变量更改后必须）

**方法 1：通过 Dashboard**
1. Vercel Dashboard → 你的项目
2. 进入 **Deployments** 标签
3. 点击最新部署右侧的 **⋯** → **Redeploy**

**方法 2：通过 Git**
```bash
git commit --allow-empty -m "Trigger redeploy for env vars"
git push origin main
```

### 3️⃣ 检查浏览器控制台

1. 打开你的网站
2. 按 **F12** 打开开发者工具
3. 进入 **Console** 标签
4. 点击购买按钮
5. 查看错误信息

**常见错误信息**：
- `未找到 normal 对应的 Stripe Price ID` → 环境变量未设置
- `STRIPE_SECRET_KEY 未配置` → Stripe API Key 未设置
- `No such price: price_xxx` → Price ID 在 Stripe 中不存在
- `404 NOT_FOUND` → API 路由问题
- `500 Internal Server Error` → 查看 Vercel 函数日志

### 4️⃣ 检查 Vercel 函数日志

1. Vercel Dashboard → 你的项目
2. 进入 **Functions** 标签
3. 找到 `/api/index` 函数
4. 点击查看 **Logs**
5. 查找错误信息（通常以 `❌` 开头）

## 🎯 最可能的问题和解决方案

### 问题 1：Price ID 是占位符

**症状**：错误信息包含 `price_xxx` 或 `price_yyy`

**解决**：
1. 在 Stripe Dashboard 中创建 Product 和 Price
2. 复制真实的 Price ID（格式：`price_1ABC123def456GHI789`）
3. 在 Vercel 环境变量中更新
4. 重新部署

### 问题 2：环境变量未保存

**症状**：设置了环境变量但仍然报错

**解决**：
1. 确认点击了 **Save** 按钮
2. 确认选择了正确的环境（Production/Preview/Development）
3. 重新部署应用

### 问题 3：Stripe API Key 无效

**症状**：错误信息包含 `Invalid API Key`

**解决**：
1. 在 Stripe Dashboard → **Developers** → **API keys** 中检查
2. 确认使用的是正确的 Key（Test Mode 用 `sk_test_...`，Live Mode 用 `sk_live_...`）
3. 如果 Key 被撤销，生成新的 Key
4. 在 Vercel 中更新 `STRIPE_SECRET_KEY`
5. 重新部署

## 📋 检查清单

在报告问题前，请确认：

- [ ] 所有环境变量都已设置（不是占位符）
- [ ] 环境变量已保存
- [ ] 已重新部署应用
- [ ] 检查了浏览器控制台错误
- [ ] 检查了 Vercel 函数日志
- [ ] Price ID 格式正确（`price_` 开头，约 20-30 个字符）
- [ ] Stripe API Key 有效

## 🆘 仍然无法解决？

如果以上步骤都无法解决问题，请提供：

1. **浏览器控制台错误**（完整错误信息）
2. **Vercel 函数日志**（最近的错误日志）
3. **环境变量配置**（隐藏敏感信息，只显示变量名和格式）

然后查看 [CHECKOUT_TROUBLESHOOTING.md](./CHECKOUT_TROUBLESHOOTING.md) 获取更详细的排查步骤。





