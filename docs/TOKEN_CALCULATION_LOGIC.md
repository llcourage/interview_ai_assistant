# Token 计算逻辑总结

## 概述

系统完全基于 **Token 配额**进行计量，不再使用请求数（request count）。所有用户都有一个月度 Token 配额限制，每次 API 调用都会计算和扣除相应的 Token 使用量。

---

## 1. Token 配额定义

### Plan 配额限制
定义在 `backend/db_models.py` 的 `PLAN_LIMITS` 中：

```python
PLAN_LIMITS = {
    PlanType.NORMAL: {
        "monthly_token_limit": 500_000,  # 50万 tokens/月
        ...
    },
    PlanType.HIGH: {
        "monthly_token_limit": 500_000,  # 50万 tokens/月（相同）
        ...
    }
}
```

### 数据库存储
- **表名**: `usage_quotas`
- **关键字段**: `monthly_tokens_used` (当前月已使用的 tokens)
- **重置机制**: 每月1号或距离上次重置超过30天时自动重置

---

## 2. Token 估算逻辑

### 2.1 文本 Token 估算
**文件**: `backend/token_estimator.py`

```python
def estimate_tokens_text(text: str) -> int:
    """
    估算文本的 token 数量
    - 启发式算法: 混合中英文文本平均 ~2 字符/token
    - 最小开销: 10 tokens (消息结构开销)
    """
    if not text:
        return 0
    estimated = len(text) // 2
    return max(estimated, 10)
```

**公式**:
- Token 数 = `max(文本长度 / 2, 10)`

### 2.2 图片 Token 估算
```python
def estimate_tokens_image(image_base64: str, detail: str = "high") -> int:
    """
    估算图片的 token 数量
    - Low detail: 85 tokens/图片
    - High detail: 170 tokens 基础 + 基于图片大小的变量
    """
    if detail == "low":
        return 85
    
    base_tokens = 170
    # 基于 base64 长度估算图片大小
    # 简化估算: 每 1000 个 base64 字符约 1 token
    size_tokens = len(image_base64) // 1000
    return base_tokens + size_tokens
```

**公式**:
- Low detail: `85 tokens`
- High detail: `170 + (base64长度 / 1000) tokens`

### 2.3 完整请求 Token 估算
```python
def estimate_tokens_for_request(
    user_input: str = None,
    context: str = None,
    prompt: str = None,
    images: Union[str, List[str]] = None,
    max_output_tokens: int = 2000
) -> int:
    """
    估算完整请求的总 token 数（输入 + 输出）
    """
    total_input_tokens = 0
    
    # 1. 系统提示词 tokens
    if prompt:
        total_input_tokens += estimate_tokens_text(prompt)
    
    # 2. 上下文 tokens
    if context:
        total_input_tokens += estimate_tokens_text(context)
    
    # 3. 用户输入 tokens
    if user_input:
        total_input_tokens += estimate_tokens_text(user_input)
    
    # 4. 图片 tokens
    if images:
        for img in images:
            total_input_tokens += estimate_tokens_image(img, detail="high")
    
    # 5. 消息结构开销 (~5 tokens/消息)
    message_count = sum([...])
    total_input_tokens += message_count * 5
    
    # 6. 估算输出 tokens (保守估计: 60% 的 max_tokens)
    estimated_output_tokens = int(max_output_tokens * 0.6)
    
    return total_input_tokens + estimated_output_tokens
```

**公式**:
```
总 Tokens = 
    输入 Tokens (文本 + 图片 + 消息结构) + 
    预估输出 Tokens (max_output_tokens * 0.6)
```

---

## 3. Token 使用流程

### 3.1 API 请求处理流程 (`/api/chat`)
**文件**: `backend/main.py`

#### 步骤 1: Token 预估
```python
# 在调用 API 之前，先估算本次请求将使用的 tokens
estimated_tokens = estimate_tokens_for_request(
    user_input=request.user_input,
    context=request.context,
    prompt=request.prompt,
    images=request.image_base64,
    max_output_tokens=3000 if request.image_base64 else 2000
)
```

#### 步骤 2: 配额预检查
```python
# 检查配额是否足够
allowed, error_msg = await check_rate_limit(
    user_id=current_user.id, 
    estimated_tokens=estimated_tokens
)
if not allowed:
    raise HTTPException(status_code=429, detail=error_msg)
```

#### 步骤 3: 调用 OpenAI API
- **文字对话**: 调用 `client.chat.completions.create()`
- **图片分析**: 调用 `analyze_image()` 函数

#### 步骤 4: 获取实际 Token 使用量
```python
# 从 OpenAI API 响应中获取真实的 token 使用量
estimated_input_tokens = response.usage.prompt_tokens
estimated_output_tokens = response.usage.completion_tokens
total_tokens = estimated_input_tokens + estimated_output_tokens
```

#### 步骤 5: 配额最终检查
```python
# 再次检查实际使用的 tokens 是否超过配额
quota_before = await get_user_quota(current_user.id)
current_tokens_used = quota_before.monthly_tokens_used
if current_tokens_used + total_tokens > monthly_token_limit:
    # 超过配额，记录失败但不扣除配额
    await log_usage(..., success=False)
    raise HTTPException(status_code=429, detail="Token quota exceeded")
```

#### 步骤 6: 更新配额
```python
# 增加用户配额使用量（使用实际 token 数量）
await increment_user_quota(
    user_id=current_user.id, 
    tokens_used=total_tokens
)
```

#### 步骤 7: 记录使用日志
```python
# 记录详细的使用日志
await log_usage(
    user_id=current_user.id,
    plan=user_plan.plan,
    api_endpoint="/api/chat",
    model_used=model,
    input_tokens=estimated_input_tokens,
    output_tokens=estimated_output_tokens,
    success=True
)
```

---

## 4. Token 配额管理

### 4.1 获取配额
**文件**: `backend/db_operations.py`

```python
async def get_user_quota(user_id: str) -> UsageQuota:
    """
    获取用户配额
    - 如果不存在则创建
    - 自动检查并重置过期配额
    """
    quota = await get_user_quota(user_id)
    # 检查是否需要重置（每月1号或超过30天）
    if quota.quota_reset_date < now:
        quota = await reset_user_quota(user_id)
    return quota
```

### 4.2 增加配额使用量
```python
async def increment_user_quota(user_id: str, tokens_used: int = 0) -> UsageQuota:
    """
    增加用户的 token 使用量
    - 只更新 monthly_tokens_used 字段
    - 使用实际 token 数量（不是估算值）
    """
    quota = await get_user_quota(user_id)
    current_tokens = quota.monthly_tokens_used
    update_data["monthly_tokens_used"] = current_tokens + tokens_used
    # 更新数据库
```

### 4.3 配额检查
```python
async def check_rate_limit(user_id: str, estimated_tokens: int = 0) -> tuple[bool, str]:
    """
    检查用户是否超过 token 配额限制
    - 使用预估 tokens 提前检查
    - 返回 (是否允许, 错误信息)
    """
    quota = await get_user_quota(user_id)
    monthly_tokens_used = quota.monthly_tokens_used
    monthly_token_limit = PLAN_LIMITS[user_plan.plan]["monthly_token_limit"]
    
    if monthly_tokens_used + estimated_tokens > monthly_token_limit:
        return False, "本月 tokens 配额不足"
    return True, ""
```

### 4.4 配额重置
```python
async def reset_user_quota(user_id: str) -> UsageQuota:
    """
    重置用户配额（每月重置）
    - 每月1号自动重置
    - 或距离上次重置超过30天时重置
    """
    should_reset_monthly = (now.day == 1) or (days_since_reset >= 30)
    if should_reset_monthly:
        update_data["monthly_tokens_used"] = 0
```

---

## 5. Token 成本计算

### 5.1 模型定价
**文件**: `backend/db_models.py`

```python
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},        # $2.5/1K input, $10/1K output
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006}, # $0.15/1K input, $0.6/1K output
}
```

### 5.2 成本计算
**文件**: `backend/db_operations.py` - `log_usage()`

```python
# 计算成本（美元）
pricing = MODEL_PRICING.get(model_used, {"input": 0, "output": 0})
cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
```

**公式**:
```
成本 = (输入 tokens / 1000) * 输入单价 + (输出 tokens / 1000) * 输出单价
```

---

## 6. 关键区别：预估 vs 实际

### 6.1 预估 Token（请求前）
- **用途**: 提前检查配额是否足够
- **方法**: 使用启发式算法估算
- **位置**: `check_rate_limit()` 中的预检查

### 6.2 实际 Token（请求后）
- **用途**: 真正扣除配额和记录日志
- **方法**: 从 OpenAI API 响应获取 (`response.usage`)
- **位置**: `increment_user_quota()` 和 `log_usage()`

### 6.3 双重检查机制
1. **请求前**: 使用预估 tokens 检查配额（避免无效请求）
2. **请求后**: 使用实际 tokens 再次检查（防止配额溢出）
3. **更新配额**: 只使用实际 tokens 数量

---

## 7. 数据流图

```
用户请求
    ↓
[1] 估算 Token (estimate_tokens_for_request)
    ↓
[2] 预检查配额 (check_rate_limit with estimated_tokens)
    ├─ 配额不足 → 返回 429 错误
    └─ 配额足够 → 继续
    ↓
[3] 调用 OpenAI API
    ↓
[4] 获取实际 Token (response.usage)
    ↓
[5] 最终配额检查 (实际 tokens)
    ├─ 超过配额 → 记录失败，返回 429
    └─ 未超过 → 继续
    ↓
[6] 更新配额 (increment_user_quota with actual_tokens)
    ↓
[7] 记录使用日志 (log_usage)
    ↓
返回结果给用户
```

---

## 8. 示例计算

### 示例 1: 文字对话
**输入**: "什么是快速排序？"

1. **估算**:
   - 用户输入: `len("什么是快速排序？") // 2 = 5 tokens`
   - 系统提示: `~200 tokens`
   - 消息结构: `~15 tokens`
   - 预估输出: `2000 * 0.6 = 1200 tokens`
   - **总计预估**: ~1420 tokens

2. **实际**:
   - 输入: `150 tokens` (从 API 获取)
   - 输出: `800 tokens` (从 API 获取)
   - **总计实际**: 950 tokens

3. **配额扣除**: 950 tokens

### 示例 2: 图片分析
**输入**: 1张 1024x1024 的 PNG 图片

1. **估算**:
   - 图片 (high detail): `170 + (500KB / 1000) = 670 tokens`
   - 提示词: `~300 tokens`
   - 预估输出: `3000 * 0.6 = 1800 tokens`
   - **总计预估**: ~2770 tokens

2. **实际**:
   - 输入: `1500 tokens`
   - 输出: `1200 tokens`
   - **总计实际**: 2700 tokens

3. **配额扣除**: 2700 tokens

---

## 9. 配额重置逻辑

### 重置时机
1. **每月1号**: 自动重置
2. **超过30天**: 如果距离上次重置超过30天，也会重置

### 重置内容
- `monthly_tokens_used = 0`
- `quota_reset_date = now + 1 day` (每日检查用)

---

## 10. 错误处理

### 配额不足的情况
1. **预检查失败**: 返回 429，不调用 API
2. **后检查失败**: 调用 API 成功但配额已超，返回 429，记录失败日志，**不扣除配额**

### 异常情况
- API 调用失败: 记录失败日志，**不扣除配额**
- 数据库错误: 允许请求继续（避免阻塞用户），但在日志中记录错误

---

## 11. 重要注意事项

1. **只使用实际 Token 扣除配额**: 预估仅用于提前检查，实际扣除使用 API 返回的真实值
2. **双重检查机制**: 请求前后都检查配额，防止超额使用
3. **配额不足不扣除**: 如果最终发现配额不足，不会扣除已使用的 tokens
4. **每月重置**: 配额每月自动重置，不受请求数限制
5. **成本跟踪**: 每次使用都记录成本，用于统计分析

---

## 总结

- **计量方式**: 100% 基于 Token，不再使用请求数
- **配额限制**: 每月 500K tokens（Normal 和 High Plan 相同）
- **Token 计算**: 估算用于预检查，实际值用于扣除配额
- **双重保护**: 请求前后都检查配额
- **自动重置**: 每月1号或超过30天自动重置配额

