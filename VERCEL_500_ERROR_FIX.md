# 🔧 Vercel 500 错误修复指南

## 问题

Webhook 端点返回 500 错误，但本地测试通过。

## 可能的原因

1. **Vercel Python handler 格式问题**
2. **环境变量未设置**
3. **运行时异常**

## 诊断步骤

### 1. 检查 Vercel 日志

在 Vercel Dashboard：
- 项目 → Functions → `api/stripe_webhook.py` → Logs
- 查看具体的错误信息

### 2. 测试最小化函数

先测试 `api/test_minimal.py` 是否能工作：
```
https://www.desktopai.org/api/test_minimal
```

如果最小化函数也失败，说明是 Vercel 环境问题。

### 3. 检查环境变量

确保在 Vercel Dashboard → Settings → Environment Variables 中设置了：
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` 或 `SUPABASE_ANON_KEY`

## 解决方案

### 方案 1: 使用 JavaScript Edge Function（推荐）

如果 Python 函数持续有问题，可以使用 Vercel Edge Functions（JavaScript）来处理 webhook。

### 方案 2: 检查函数格式

确保函数格式正确：
```python
def handler(request):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({...})
    }
```

### 方案 3: 添加更详细的错误处理

已在 `api/stripe_webhook.py` 中添加了 try-catch，应该能捕获并返回错误信息。

## 下一步

1. 查看 Vercel 日志获取具体错误
2. 测试最小化函数
3. 检查环境变量
4. 如果仍有问题，考虑使用 JavaScript Edge Function

