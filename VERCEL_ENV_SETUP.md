# 🔧 Vercel 环境变量配置指南

## 📋 概述

在 Vercel 部署后，需要配置以下环境变量才能让应用正常工作。

## 🚀 配置步骤

### 1. 进入 Vercel 项目设置

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目（AI Interview Assistant）
3. 点击 **Settings** → **Environment Variables**

### 2. 配置环境变量

在 Vercel 中添加以下环境变量：

#### 🔑 OpenAI 配置（必需）

```
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

#### 🗄️ Supabase 配置（必需）

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

> ⚠️ **重要**：`SUPABASE_SERVICE_ROLE_KEY` 用于 Webhook 更新用户权限，必须有写入权限。

#### 💳 Stripe 配置（必需）

```
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
STRIPE_PRICE_NORMAL=price_xxx
STRIPE_PRICE_HIGH=price_yyy
```

> 📝 **注意**：
> - 开发环境使用 `sk_test_...`，生产环境使用 `sk_live_...`
> - `STRIPE_WEBHOOK_SECRET` 需要在 Stripe Dashboard 中创建 Webhook 后获取
> - `STRIPE_PRICE_NORMAL` 和 `STRIPE_PRICE_HIGH` 是 Stripe Product 的 Price ID

### 3. 环境变量作用域

建议为所有环境变量选择：
- ✅ **Production**
- ✅ **Preview** 
- ✅ **Development**

这样可以确保在所有环境中都能正常工作。

## 📝 详细配置说明

### OpenAI API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 创建新的 API Key
3. 复制并粘贴到 `OPENAI_API_KEY`

### Supabase 配置

1. 访问 [Supabase Dashboard](https://app.supabase.com/)
2. 选择你的项目
3. 进入 **Settings** → **API**
4. 复制：
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_ANON_KEY`
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY`

> ⚠️ **安全提示**：`SUPABASE_SERVICE_ROLE_KEY` 有完整数据库访问权限，请妥善保管。

### Stripe 配置

#### 获取 Stripe API Keys

1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 进入 **Developers** → **API keys**
3. 复制：
   - **Secret key** → `STRIPE_SECRET_KEY`
   - **Publishable key**（前端使用，如果需要）

#### 创建 Products 和 Prices

1. 进入 **Products** → **Add product**

**Normal Plan ($19.99/月)**
- Name: Normal Plan
- Description: GPT-4o mini access
- Pricing: $19.99/month (Recurring)
- 复制生成的 **Price ID** → `STRIPE_PRICE_NORMAL`

**High Plan ($49.99/月)**
- Name: High Plan
- Description: GPT-4o access
- Pricing: $49.99/month (Recurring)
- 复制生成的 **Price ID** → `STRIPE_PRICE_HIGH`

#### 配置 Stripe Webhook

1. 进入 **Developers** → **Webhooks**
2. 点击 **Add endpoint**
3. 配置：
   - **Endpoint URL**: `https://www.desktopai.org/api/stripe_webhook`
   - **Description**: "AI Interview Assistant Webhook"
   - **Events to send**: 选择以下事件：
     - ✅ `checkout.session.completed` - 支付成功
     - ✅ `customer.subscription.updated` - 订阅更新
     - ✅ `customer.subscription.deleted` - 订阅取消
4. 点击 **Add endpoint**
5. 复制生成的 **Signing secret** (whsec_xxx) → `STRIPE_WEBHOOK_SECRET`

> 📝 **注意**：Webhook URL 必须是你的实际域名。如果是测试环境，可以使用 Vercel 提供的预览 URL。

## ✅ 验证配置

### 1. 检查环境变量

在 Vercel Dashboard → **Settings** → **Environment Variables** 中确认所有变量都已添加。

### 2. 测试 Webhook

1. 访问 `https://www.desktopai.org/api/stripe_webhook` (GET 请求)
2. 应该返回：
   ```json
   {
     "status": "ok",
     "message": "Stripe Webhook endpoint is active..."
   }
   ```

### 3. 测试 Stripe Webhook（在 Stripe Dashboard）

1. 进入 **Developers** → **Webhooks**
2. 点击你的 Webhook endpoint
3. 点击 **Send test webhook**
4. 选择 `checkout.session.completed` 事件
5. 检查 Vercel 函数日志，确认事件被正确处理

## 🔍 故障排查

### 问题：Webhook 返回 500 错误

**可能原因**：
1. `STRIPE_WEBHOOK_SECRET` 未配置或错误
2. `SUPABASE_URL` 或 `SUPABASE_SERVICE_ROLE_KEY` 未配置
3. 环境变量未正确保存

**解决方法**：
1. 检查 Vercel 环境变量配置
2. 重新部署项目（环境变量更改后需要重新部署）
3. 查看 Vercel 函数日志获取详细错误信息

### 问题：支付成功后用户权限未更新

**可能原因**：
1. Webhook 未正确配置
2. `SUPABASE_SERVICE_ROLE_KEY` 权限不足
3. 数据库表结构不正确

**解决方法**：
1. 检查 Stripe Webhook 日志，确认事件已发送
2. 检查 Vercel 函数日志，查看是否有错误
3. 确认 Supabase 数据库表 `user_plans` 已创建

### 问题：无法创建 Checkout Session

**可能原因**：
1. `STRIPE_SECRET_KEY` 未配置或错误
2. `STRIPE_PRICE_NORMAL` 或 `STRIPE_PRICE_HIGH` 未配置

**解决方法**：
1. 检查 Stripe API keys 是否正确
2. 确认 Price IDs 已正确配置
3. 检查 Stripe Dashboard 中的 Products 和 Prices

## 📚 相关文档

- [Stripe Setup Guide](./STRIPE_SETUP.md) - 详细的 Stripe 配置指南
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables) - Vercel 官方文档

## 🎯 下一步

配置完成后：
1. ✅ 重新部署项目（Vercel 会自动检测环境变量更改）
2. ✅ 测试支付流程
3. ✅ 验证 Webhook 正常工作
4. ✅ 测试用户权限更新

