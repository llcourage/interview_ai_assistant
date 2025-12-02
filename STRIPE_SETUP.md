# 💳 Stripe 支付系统设置指南

## 概述

本项目已集成 Stripe 支付系统，支持订阅式付费。支付成功后会自动更新用户权限。

## 支付流程

1. **用户选择 Plan** → 点击 "Get Started"
2. **创建 Checkout Session** → 后端调用 Stripe API
3. **跳转到 Stripe 支付页面** → 用户完成支付
4. **Webhook 处理** → Stripe 发送支付成功事件
5. **更新用户权限** → 自动升级用户 Plan

## 设置步骤

### 1. 创建 Stripe 账户

1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 注册/登录账户
3. 切换到 **Test Mode**（开发阶段）或 **Live Mode**（生产环境）

### 2. 获取 API Keys

在 Stripe Dashboard 中：

1. 进入 **Developers** → **API keys**
2. 复制以下密钥：
   - **Secret key** (sk_test_... 或 sk_live_...)
   - **Publishable key** (pk_test_... 或 pk_live_...)

### 3. 创建 Products 和 Prices

1. 进入 **Products** → **Add product**

#### Normal Plan ($19.99/月)
- **Name**: Normal Plan
- **Description**: GPT-4o mini access
- **Pricing**: 
  - Type: Recurring
  - Price: $19.99
  - Billing period: Monthly
- 复制生成的 **Price ID** (price_xxx)

#### High Plan ($49.99/月)
- **Name**: High Plan
- **Description**: GPT-4o access
- **Pricing**:
  - Type: Recurring
  - Price: $49.99
  - Billing period: Monthly
- 复制生成的 **Price ID** (price_yyy)

### 4. 设置 Webhook

> ✅ **好消息**：Webhook 端点代码已经实现好了！
> 
> - 代码位置：`backend/main.py` 第 431 行
> - 端点路径：`POST /api/webhooks/stripe`
> - 已处理的事件：`checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
> 
> 您只需要在 Stripe Dashboard 中注册这个 URL 即可。

#### 在 Stripe Dashboard 中注册 Webhook

1. 进入 **Developers** → **Webhooks**
2. 点击 **Add endpoint** 按钮
3. 配置：
   - **Endpoint URL**: `https://www.desktopai.org/api/stripe_webhook`
     > ⚠️ 注意：将 `www.desktopai.org` 替换为您的实际域名（Vercel 部署的域名）
   - **Description**（可选）: "AI Interview Assistant Webhook"
   - **Events to send**: 选择以下事件：
     - ✅ `checkout.session.completed` - 支付成功
     - ✅ `customer.subscription.updated` - 订阅更新
     - ✅ `customer.subscription.deleted` - 订阅取消
4. 点击 **Add endpoint** 保存
5. 复制生成的 **Signing secret** (whsec_xxx)
   > 这个 secret 需要添加到 **Vercel 环境变量** `STRIPE_WEBHOOK_SECRET` 中

### 5. 配置环境变量

> ⚠️ **重要**：由于应用部署在 Vercel，环境变量需要在 **Vercel Dashboard** 中配置，而不是本地 `.env` 文件。

#### 在 Vercel 中配置环境变量

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目
3. 进入 **Settings** → **Environment Variables**
4. 添加以下环境变量：

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your-secret-key-here
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret-here
STRIPE_PRICE_NORMAL=price_xxx  # Normal Plan Price ID
STRIPE_PRICE_HIGH=price_yyy    # High Plan Price ID

# Supabase Configuration (Webhook 需要)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

> 📝 **详细步骤**：参考 [VERCEL_ENV_SETUP.md](./VERCEL_ENV_SETUP.md) 获取完整的环境变量配置指南。

### 6. 安装 Stripe Python SDK

已在 `backend/requirements.txt` 中包含：
```
stripe>=7.0.0
```

如果未安装，运行：
```bash
pip install stripe
```

## 支付流程详解

### 前端流程

1. **用户点击 Plan 按钮** (`src/Plans.tsx` 或 `src/Landing.tsx`)
2. **检查登录状态** → 未登录则跳转到登录页
3. **调用后端 API** → `POST /api/plan/checkout`
4. **跳转到 Stripe** → 使用返回的 `checkout_url`

### 后端流程

#### 创建 Checkout Session (`backend/payment_stripe.py`)

```python
async def create_checkout_session(user_id, plan, success_url, cancel_url):
    # 1. 获取或创建 Stripe Customer
    # 2. 创建 Checkout Session
    # 3. 返回 checkout_url
```

#### Webhook 处理 (`backend/main.py`)

```python
@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    # 1. 验证 Webhook 签名
    # 2. 处理不同事件类型
    # 3. 更新用户权限
```

### 支付成功后更新权限

当 Stripe 发送 `checkout.session.completed` 事件时：

1. **提取用户信息** → 从 session metadata 获取 `user_id` 和 `plan`
2. **更新数据库** → 调用 `update_user_plan()` 更新：
   - `plan`: normal 或 high
   - `stripe_customer_id`: Stripe 客户 ID
   - `stripe_subscription_id`: 订阅 ID
   - `subscription_status`: "active"
3. **用户权限立即生效** → 下次 API 调用时使用新的 Plan

## 测试支付

### 使用测试卡号

在 Stripe Test Mode 中，使用以下测试卡号：

- **成功支付**: `4242 4242 4242 4242`
- **需要 3D Secure**: `4000 0025 0000 3155`
- **支付失败**: `4000 0000 0000 9995`

其他信息：
- **Expiry**: 任意未来日期（如 12/34）
- **CVC**: 任意 3 位数字（如 123）
- **ZIP**: 任意 5 位数字（如 12345）

### 测试 Webhook

1. 在 Stripe Dashboard → **Developers** → **Webhooks**
2. 点击你的 Webhook endpoint
3. 点击 **Send test webhook**
4. 选择事件类型测试

## 生产环境部署

### 1. 切换到 Live Mode

1. 在 Stripe Dashboard 切换为 **Live Mode**
2. 获取 Live API keys
3. 更新 `backend/.env` 中的密钥

### 2. 更新 Webhook URL

确保 Webhook URL 指向生产环境：
```
https://your-production-domain.com/api/webhooks/stripe
```

### 3. 安全配置

- ✅ 使用 HTTPS
- ✅ 验证 Webhook 签名
- ✅ 保护 API keys（不要提交到 Git）
- ✅ 使用环境变量存储敏感信息

## 常见问题

### Q: 支付成功后用户权限没有更新？

**A**: 检查：
1. Webhook URL 是否正确配置
2. Webhook secret 是否正确
3. 后端日志是否有错误
4. 数据库连接是否正常

### Q: 如何查看支付记录？

**A**: 在 Stripe Dashboard → **Payments** 查看所有支付记录

### Q: 如何取消订阅？

**A**: 
- 用户可以通过前端调用 `POST /api/plan/cancel`
- 或在 Stripe Dashboard 手动取消

### Q: 订阅到期后会发生什么？

**A**: 
- Stripe 会发送 `customer.subscription.deleted` 事件
- Webhook 会自动将用户降级为 `normal` plan

## 相关文件

- `backend/payment_stripe.py` - Stripe 支付逻辑
- `backend/main.py` - API 端点和 Webhook 处理
- `backend/db_operations.py` - 用户权限更新
- `src/Plans.tsx` - 前端支付流程
- `src/Checkout.tsx` - 支付页面
- `src/Success.tsx` - 支付成功页面

## 下一步

1. ✅ 配置 Stripe 账户和 API keys
2. ✅ 创建 Products 和 Prices
3. ✅ 设置 Webhook endpoint
4. ✅ 测试支付流程
5. ✅ 部署到生产环境

