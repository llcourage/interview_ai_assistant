# 🔧 Checkout 错误排查指南

## 错误信息

如果看到以下错误：
```
❌ Error
Failed to create checkout session. Please try again later.
```

## 可能的原因和解决方法

### 1. ✅ 检查环境变量配置

**问题**：Stripe Price ID 或 Secret Key 未正确配置

**解决方法**：

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目
3. 进入 **Settings** → **Environment Variables**
4. 确认以下变量都已设置：
   - `STRIPE_SECRET_KEY` - 应该是 `sk_test_...` 或 `sk_live_...`
   - `STRIPE_PRICE_NORMAL` - 应该是 `price_xxxxxxxxxxxxx`（不是 `price_xxx`）
   - `STRIPE_PRICE_HIGH` - 应该是 `price_yyyyyyyyyyyyy`（不是 `price_yyy`）

5. **重要**：如果修改了环境变量，需要：
   - 点击 **Save** 保存
   - 进入 **Deployments** 标签
   - 点击最新部署右侧的 **⋯** → **Redeploy**
   - 或者推送新的代码触发重新部署

### 2. ✅ 检查 Price ID 格式

**问题**：Price ID 格式错误或使用了占位符

**检查方法**：

1. 打开浏览器开发者工具（F12）
2. 进入 **Console** 标签
3. 点击购买按钮
4. 查看控制台错误信息

**常见错误**：
- `未找到 normal 对应的 Stripe Price ID` - 说明 `STRIPE_PRICE_NORMAL` 未设置或格式错误
- `未找到 high 对应的 Stripe Price ID` - 说明 `STRIPE_PRICE_HIGH` 未设置或格式错误

**解决方法**：
- 确保 Price ID 以 `price_` 开头
- 确保没有包含引号或空格
- 参考 [STRIPE_SETUP.md](./STRIPE_SETUP.md) 第 3 节获取正确的 Price ID

### 3. ✅ 检查 API 端点

**问题**：API 端点无法访问或返回 404/500

**检查方法**：

1. 打开浏览器开发者工具（F12）
2. 进入 **Network** 标签
3. 点击购买按钮
4. 查看 `/api/plan/checkout` 请求：
   - **Status**: 应该是 `200`，如果是 `404` 或 `500` 说明有问题
   - **Response**: 查看返回的错误信息

**可能的问题**：

#### 404 Not Found
- **原因**：API 路由未正确配置
- **解决方法**：检查 `vercel.json` 配置，确保 `rewrites` 正确设置

#### 500 Internal Server Error
- **原因**：后端代码错误或环境变量缺失
- **解决方法**：
  1. 查看 Vercel 函数日志：
     - Vercel Dashboard → 项目 → **Functions** 标签
     - 找到 `/api/index` 函数
     - 查看 **Logs** 获取详细错误信息
  2. 检查环境变量是否都已设置
  3. 检查 Stripe API Key 是否有效

#### 401 Unauthorized
- **原因**：用户未登录或 token 无效
- **解决方法**：确保用户已登录

### 4. ✅ 检查 Stripe API Key

**问题**：Stripe Secret Key 无效或过期

**检查方法**：

1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 进入 **Developers** → **API keys**
3. 确认：
   - **Test Mode** 下使用 `sk_test_...`
   - **Live Mode** 下使用 `sk_live_...`
   - 确保 Key 没有被撤销或禁用

**解决方法**：
- 如果 Key 无效，生成新的 Secret Key
- 在 Vercel 环境变量中更新 `STRIPE_SECRET_KEY`
- 重新部署应用

### 5. ✅ 检查 Price ID 是否存在于 Stripe

**问题**：Price ID 在 Stripe 中不存在或已被删除

**检查方法**：

1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 进入 **Products**
3. 点击你创建的产品（Normal Plan 或 High Plan）
4. 在 **Pricing** 部分确认 Price ID 存在
5. 确认 Price ID 与 Vercel 环境变量中的值一致

**解决方法**：
- 如果 Price ID 不存在，重新创建 Product 和 Price
- 更新 Vercel 环境变量中的 Price ID
- 重新部署应用

### 6. ✅ 检查网络请求

**问题**：前端无法访问后端 API

**检查方法**：

1. 打开浏览器开发者工具（F12）
2. 进入 **Console** 标签
3. 运行以下命令查看 API URL：
   ```javascript
   console.log('API URL:', import.meta.env.VITE_API_URL || window.location.origin);
   ```

**可能的问题**：

- **开发环境**：如果 `VITE_API_URL` 未设置，默认使用 `http://127.0.0.1:8000`
  - 确保本地后端服务正在运行
  - 或者设置 `.env` 文件中的 `VITE_API_URL`

- **生产环境**：应该使用 `window.location.origin`（你的域名）
  - 确保 Vercel 部署成功
  - 确保 `vercel.json` 配置正确

## 🔍 详细调试步骤

### 步骤 1：检查浏览器控制台

1. 打开浏览器开发者工具（F12）
2. 进入 **Console** 标签
3. 点击购买按钮
4. 查看错误信息，记录：
   - 错误消息
   - 错误堆栈
   - 网络请求状态

### 步骤 2：检查网络请求

1. 在开发者工具中进入 **Network** 标签
2. 点击购买按钮
3. 找到 `/api/plan/checkout` 请求
4. 查看：
   - **Request URL**: 确认是正确的 API 地址
   - **Request Headers**: 确认包含 `Authorization: Bearer ...`
   - **Request Payload**: 确认包含 `plan`, `success_url`, `cancel_url`
   - **Response**: 查看服务器返回的错误信息

### 步骤 3：检查 Vercel 函数日志

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目
3. 进入 **Functions** 标签
4. 找到 `/api/index` 函数
5. 点击查看 **Logs**
6. 查找错误信息，常见错误：
   - `未找到 {plan} 对应的 Stripe Price ID`
   - `No such price: price_xxx`
   - `Invalid API Key provided`

### 步骤 4：测试 Stripe API

如果怀疑 Stripe API 配置问题，可以：

1. 在本地测试 Stripe API（需要本地后端运行）
2. 使用 Stripe CLI 测试：
   ```bash
   stripe listen --forward-to http://localhost:8000/api/webhooks/stripe
   ```

## 📝 常见错误信息对照表

| 错误信息 | 可能原因 | 解决方法 |
|---------|---------|---------|
| `未找到 {plan} 对应的 Stripe Price ID` | Price ID 未配置或格式错误 | 检查 Vercel 环境变量 |
| `No such price: price_xxx` | Price ID 在 Stripe 中不存在 | 重新创建 Product 和 Price |
| `Invalid API Key provided` | Stripe Secret Key 无效 | 检查并更新 Stripe API Key |
| `404 NOT_FOUND` | API 路由未配置 | 检查 `vercel.json` 配置 |
| `500 Internal Server Error` | 后端代码错误 | 查看 Vercel 函数日志 |
| `401 Unauthorized` | 用户未登录 | 确保用户已登录 |

## 🆘 仍然无法解决？

如果以上步骤都无法解决问题，请：

1. **收集信息**：
   - 浏览器控制台的完整错误信息
   - Network 标签中的请求和响应
   - Vercel 函数日志中的错误信息

2. **检查配置**：
   - 确认所有环境变量都已设置
   - 确认 Stripe Dashboard 中的配置正确
   - 确认 Vercel 部署成功

3. **重新部署**：
   - 在 Vercel 中触发重新部署
   - 确保环境变量已保存

## 📚 相关文档

- [STRIPE_SETUP.md](./STRIPE_SETUP.md) - Stripe 设置指南
- [VERCEL_ENV_SETUP.md](./VERCEL_ENV_SETUP.md) - Vercel 环境变量配置





