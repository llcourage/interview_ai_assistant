# 🔍 调试 Checkout 错误 - Stripe 没有日志

## 问题分析

如果 **Stripe 仪表板没有 API 日志**，说明：
- ❌ 请求**根本没有到达 Stripe API**
- ✅ 错误发生在调用 Stripe 之前

## 可能的原因

根据代码逻辑，在调用 Stripe API 之前会进行以下检查：

1. **环境变量检查**（第 40-41 行）
   - `STRIPE_SECRET_KEY` 是否为空
   - 如果为空，会抛出：`STRIPE_SECRET_KEY 未配置，请在环境变量中设置`

2. **Price ID 检查**（第 43-49 行）
   - `STRIPE_PRICE_NORMAL` 或 `STRIPE_PRICE_HIGH` 是否为空
   - 是否是占位符值（`price_xxx` 或 `price_yyy`）
   - 如果检查失败，会抛出：`未找到 {plan} 对应的 Stripe Price ID`

3. **数据库操作**（第 52 行）
   - 获取用户 plan 数据
   - 如果 Supabase 连接失败，会抛出异常

## 🔍 立即检查步骤

### 步骤 1：查看 Vercel 函数日志（最重要）

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目
3. 进入 **Functions** 标签
4. 找到 `/api/index` 函数
5. 点击查看 **Logs**
6. **点击购买按钮**，然后立即查看日志
7. 查找以下错误信息：

#### 错误 1：环境变量未配置
```
❌ Checkout 配置错误: STRIPE_SECRET_KEY 未配置，请在环境变量中设置
```
**解决方法**：在 Vercel 环境变量中设置 `STRIPE_SECRET_KEY`

#### 错误 2：Price ID 是占位符
```
❌ Checkout 配置错误: 未找到 normal 对应的 Stripe Price ID。当前值: price_xxx。请在 Vercel 环境变量中设置 STRIPE_PRICE_NORMAL
```
**解决方法**：更新 `STRIPE_PRICE_NORMAL` 和 `STRIPE_PRICE_HIGH` 为真实的 Price ID

#### 错误 3：数据库连接失败
```
❌ Checkout 错误: ...
```
**解决方法**：检查 Supabase 环境变量配置

### 步骤 2：检查浏览器控制台

1. 打开浏览器开发者工具（F12）
2. 进入 **Console** 标签
3. 点击购买按钮
4. 查看错误信息

**现在会显示更详细的错误**（我已经改进了错误处理）：
- 如果看到 `未找到 {plan} 对应的 Stripe Price ID` → Price ID 未配置
- 如果看到 `STRIPE_SECRET_KEY 未配置` → API Key 未配置
- 如果看到 `Server error: 500` → 查看 Vercel 函数日志

### 步骤 3：检查网络请求

1. 在开发者工具中进入 **Network** 标签
2. 点击购买按钮
3. 找到 `/api/plan/checkout` 请求
4. 查看：
   - **Status**: 应该是 `200`，如果是 `400` 或 `500` 说明有问题
   - **Response**: 查看返回的错误信息

## 🎯 快速诊断

### 场景 A：看到 "未找到 {plan} 对应的 Stripe Price ID"

**原因**：Price ID 未配置或是占位符

**解决**：
1. 在 Stripe Dashboard 中创建 Product 和 Price
2. 复制真实的 Price ID
3. 在 Vercel 环境变量中更新
4. **重新部署**

### 场景 B：看到 "STRIPE_SECRET_KEY 未配置"

**原因**：Stripe API Key 未设置

**解决**：
1. 在 Stripe Dashboard → **Developers** → **API keys** 中获取 Secret Key
2. 在 Vercel 环境变量中设置 `STRIPE_SECRET_KEY`
3. **重新部署**

### 场景 C：看到 "500 Internal Server Error"

**原因**：后端代码错误或数据库连接失败

**解决**：
1. 查看 Vercel 函数日志获取详细错误
2. 检查 Supabase 环境变量配置
3. 检查所有必需的环境变量是否都已设置

## 📋 检查清单

在报告问题前，请确认：

- [ ] 查看了 Vercel 函数日志（**最重要**）
- [ ] 查看了浏览器控制台错误
- [ ] 查看了网络请求的响应
- [ ] `STRIPE_SECRET_KEY` 已设置且不是空值
- [ ] `STRIPE_PRICE_NORMAL` 已设置且不是 `price_xxx`
- [ ] `STRIPE_PRICE_HIGH` 已设置且不是 `price_yyy`
- [ ] 环境变量已保存
- [ ] 已重新部署应用

## 🔧 下一步

1. **立即查看 Vercel 函数日志** - 这是最关键的诊断信息
2. 将日志中的错误信息发给我，我可以帮你进一步诊断
3. 如果看到具体的错误信息（如 "未找到 normal 对应的 Stripe Price ID"），按照上面的解决方法操作

## 💡 提示

Vercel 函数日志会显示：
- ✅ 代码执行到哪一步
- ✅ 具体的错误信息
- ✅ 环境变量的实际值（在错误信息中）

这些信息对于诊断问题非常重要！





