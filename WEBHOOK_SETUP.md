# 🔗 Stripe Webhook 设置指南

## ⚠️ 重要区别

### ❌ 不是这个（前端页面）：
```
https://www.desktopai.org/checkout?plan=normal
```
这是**前端页面**，用户点击"Get Started"后跳转到这里。

### ✅ 应该是这个（后端 API 端点）：
```
https://www.desktopai.org/api/webhooks/stripe
```
这是**后端 API 端点**，Stripe 会发送支付事件到这里。

---

## 📋 在 Stripe Dashboard 中设置 Webhook

### 1. 进入 Webhooks 设置

1. 登录 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 进入 **Developers** → **Webhooks**
3. 点击 **Add endpoint** 按钮

### 2. 配置 Webhook Endpoint

**Endpoint URL**（重要！）：
```
https://www.desktopai.org/api/webhooks/stripe
```

**Events to send**（选择以下事件）：
- ✅ `checkout.session.completed` - 支付成功时触发
- ✅ `customer.subscription.updated` - 订阅更新时触发
- ✅ `customer.subscription.deleted` - 订阅取消时触发

### 3. 复制 Webhook Secret

创建后，Stripe 会生成一个 **Signing secret**，格式类似：
```
whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. 配置环境变量

在 Vercel Dashboard 或 `backend/.env` 中添加：

```env
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🔄 完整流程

### 用户支付流程：

1. **用户点击 Plan 按钮** → 前端调用 `POST /api/plan/checkout`
2. **后端创建 Checkout Session** → 返回 `checkout_url`
3. **用户跳转到 Stripe** → 完成支付
4. **Stripe 发送 Webhook** → `POST https://www.desktopai.org/api/webhooks/stripe`
5. **后端处理事件** → 更新用户 Plan 权限
6. **用户跳转回网站** → `success_url`（如 `/success?plan=normal`）

### Webhook 处理的事件：

| 事件类型 | 触发时机 | 后端处理 |
|---------|---------|---------|
| `checkout.session.completed` | 支付成功 | 升级用户 Plan |
| `customer.subscription.updated` | 订阅状态变化 | 更新订阅状态 |
| `customer.subscription.deleted` | 订阅取消 | 降级为 Normal Plan |

---

## 🧪 测试 Webhook

### 使用 Stripe CLI（本地测试）

```bash
# 安装 Stripe CLI
# https://stripe.com/docs/stripe-cli

# 转发 webhook 到本地
stripe listen --forward-to http://localhost:8000/api/webhooks/stripe

# 触发测试事件
stripe trigger checkout.session.completed
```

### 在 Stripe Dashboard 测试

1. 进入 **Developers** → **Webhooks**
2. 点击你的 Webhook endpoint
3. 点击 **Send test webhook**
4. 选择事件类型（如 `checkout.session.completed`）
5. 查看后端日志确认收到事件

---

## ✅ 验证 Webhook 是否工作

### 检查清单：

- [ ] Webhook URL 设置为 `https://www.desktopai.org/api/webhooks/stripe`
- [ ] 已选择正确的事件类型（3个事件）
- [ ] `STRIPE_WEBHOOK_SECRET` 已配置在环境变量中
- [ ] 后端 API 已部署到 Vercel
- [ ] 测试支付后，用户 Plan 自动更新

### 查看 Webhook 日志：

在 Stripe Dashboard → **Developers** → **Webhooks** → 点击你的 endpoint → **Events** 标签

可以看到：
- ✅ 成功的事件（绿色）
- ❌ 失败的事件（红色）及错误信息

---

## 🚨 常见问题

### Q: Webhook 没有收到事件？

**A**: 检查：
1. Webhook URL 是否正确（必须是 `/api/webhooks/stripe`）
2. 后端 API 是否正常运行
3. Vercel 函数是否已部署
4. 查看 Stripe Dashboard 中的 Webhook 日志

### Q: Webhook 签名验证失败？

**A**: 确保：
1. `STRIPE_WEBHOOK_SECRET` 环境变量已正确设置
2. 使用的是正确的 Webhook secret（不是 API key）
3. 环境变量已重新部署到 Vercel

### Q: 支付成功但用户权限没有更新？

**A**: 检查：
1. Webhook 是否成功发送（查看 Stripe Dashboard）
2. 后端日志是否有错误
3. 数据库连接是否正常
4. `user_id` 是否正确传递到 metadata

---

## 📝 相关文件

- `backend/main.py` - Webhook 端点实现（第 431 行）
- `backend/payment_stripe.py` - Webhook 事件处理函数
- `STRIPE_SETUP.md` - 完整的 Stripe 设置指南

