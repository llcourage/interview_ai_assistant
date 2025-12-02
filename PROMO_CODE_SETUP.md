# 🎟️ Stripe 优惠码（Promo Code）设置指南

## 概述

本应用已支持 Stripe 优惠码功能。用户在支付页面可以输入优惠码来获得折扣。

## 功能说明

- ✅ 用户可以在 Stripe Checkout 页面输入优惠码
- ✅ 支持 Stripe 的所有优惠码类型（百分比折扣、固定金额折扣等）
- ✅ 优惠码在 Stripe Dashboard 中统一管理

## 设置步骤

### 1. 在 Stripe Dashboard 中创建优惠码

1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 进入 **Products** → **Coupons**（或直接搜索 "Coupons"）
3. 点击 **Create coupon**

#### 创建优惠券（Coupon）

**基本信息：**
- **Name**: 优惠券名称（例如：`SUMMER2024`）
- **Type**: 选择折扣类型
  - **Percentage**: 百分比折扣（例如：20% off）
  - **Fixed amount**: 固定金额折扣（例如：$10 off）
- **Amount**: 折扣金额
  - 百分比：输入 `20` 表示 20% 折扣
  - 固定金额：输入 `1000` 表示 $10.00 折扣（Stripe 使用最小货币单位，$10 = 1000 cents）
- **Currency**: 选择货币（例如：USD）
- **Duration**: 折扣持续时间
  - **Once**: 仅首次付款
  - **Forever**: 永久折扣（适用于订阅）
  - **Repeating**: 重复折扣（指定月数）

**高级选项（可选）：**
- **Redeem by**: 优惠券过期日期
- **Max redemptions**: 最大使用次数
- **Applies to**: 指定适用的产品

4. 点击 **Create coupon** 保存

#### 创建优惠码（Promo Code）

1. 在 Coupon 页面，找到刚创建的优惠券
2. 点击 **Add promotion code**
3. 配置：
   - **Code**: 优惠码（例如：`SUMMER2024`、`WELCOME20`）
   - **Active**: 启用/禁用
   - **First time transaction only**: 仅首次交易可用
   - **Customer eligibility**: 客户资格限制
4. 点击 **Create promotion code** 保存

### 2. 测试优惠码

#### 在 Stripe Test Mode 中测试

1. 确保在 **Test Mode** 下创建优惠码
2. 使用测试卡号完成支付流程：
   - 卡号：`4242 4242 4242 4242`
   - 在支付页面输入你创建的优惠码
   - 确认折扣已正确应用

#### 验证优惠码生效

1. 在 Stripe Dashboard → **Payments** 中查看支付记录
2. 确认折扣金额已正确应用
3. 检查 Webhook 事件是否正常处理

## 优惠码类型示例

### 示例 1：首次订阅 20% 折扣

**Coupon 配置：**
- Name: `FIRST20`
- Type: Percentage
- Amount: `20`
- Duration: Once（仅首次付款）

**Promo Code：** `FIRST20`

**效果：** 用户首次订阅时享受 20% 折扣，后续按原价收费

### 示例 2：永久 10% 折扣

**Coupon 配置：**
- Name: `LOYAL10`
- Type: Percentage
- Amount: `10`
- Duration: Forever（永久折扣）

**Promo Code：** `LOYAL10`

**效果：** 用户每次订阅都享受 10% 折扣

### 示例 3：固定金额折扣 $5

**Coupon 配置：**
- Name: `SAVE5`
- Type: Fixed amount
- Amount: `500`（$5.00，以 cents 为单位）
- Currency: USD
- Duration: Once

**Promo Code：** `SAVE5`

**效果：** 首次订阅减免 $5

## 代码实现

优惠码功能已在代码中启用：

**文件：** `backend/payment_stripe.py`

```python
session = stripe.checkout.Session.create(
    ...
    allow_promotion_codes=True,  # 启用优惠码输入框
    ...
)
```

用户可以在 Stripe Checkout 页面看到 "Add promotion code" 链接，点击后可以输入优惠码。

## 管理优惠码

### 查看使用情况

1. 在 Stripe Dashboard → **Products** → **Coupons**
2. 点击优惠券查看详情
3. 在 **Promotion codes** 标签页查看：
   - 使用次数
   - 使用时间
   - 关联的支付记录

### 禁用/启用优惠码

1. 进入优惠码详情页
2. 切换 **Active** 开关
3. 禁用后，该优惠码将无法使用

### 限制使用次数

在创建 Coupon 时设置 **Max redemptions**，达到上限后优惠码自动失效。

## 常见问题

### Q: 优惠码在哪里输入？

**A:** 用户在 Stripe Checkout 支付页面会看到 "Add promotion code" 链接，点击后可以输入优惠码。

### Q: 可以创建多个优惠码吗？

**A:** 可以！一个 Coupon 可以关联多个 Promo Code，每个 Promo Code 可以有不同的使用限制。

### Q: 优惠码可以叠加使用吗？

**A:** 默认情况下，Stripe 不支持多个优惠码叠加。每次交易只能使用一个优惠码。

### Q: 如何设置仅限新用户使用的优惠码？

**A:** 在创建 Promo Code 时，勾选 **First time transaction only** 选项。

### Q: 优惠码适用于哪些 Plan？

**A:** 默认情况下，优惠码适用于所有产品。如果需要限制，在创建 Coupon 时设置 **Applies to** 选项，指定特定的产品。

## 最佳实践

1. **使用有意义的优惠码名称**：例如 `SUMMER2024`、`WELCOME20` 等
2. **设置使用限制**：避免优惠码被滥用
3. **设置过期日期**：定期清理过期优惠码
4. **测试优惠码**：在 Test Mode 中充分测试后再发布
5. **监控使用情况**：定期检查优惠码的使用情况，分析效果

## 相关文档

- [Stripe Coupons 文档](https://stripe.com/docs/billing/subscriptions/discounts)
- [Stripe Promotion Codes 文档](https://stripe.com/docs/billing/subscriptions/discounts/codes)


