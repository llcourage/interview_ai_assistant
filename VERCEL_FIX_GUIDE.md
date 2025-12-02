# 🔧 Vercel Python Handler 错误修复指南

## 问题

`TypeError: issubclass() arg 1 must be a class` 错误发生在 Vercel 的 Python handler 中。

## 原因

这个错误通常由以下原因引起：

1. **依赖版本不兼容**：Pydantic、typing-extensions 等库的版本冲突
2. **类型提示问题**：某些库在导入时执行了类型检查代码
3. **Vercel 环境问题**：Python 版本或依赖解析问题

## 解决方案

### ✅ 已实施的修复

1. **固定依赖版本** (`api/requirements.txt`)
   - 使用精确版本号而不是 `>=`
   - 固定 `typing-extensions==4.9.0`（避免版本冲突）
   - 固定所有依赖的版本

2. **分离 webhook 端点**
   - `api/stripe_webhook.py`：零外部依赖，只使用标准库
   - `api/index.py`：使用 FastAPI（已固定版本）

### 📋 检查清单

- [x] 固定 `typing-extensions` 版本
- [x] 固定 `pydantic` 版本
- [x] 固定 `fastapi` 版本
- [x] 固定所有依赖版本
- [x] Webhook 端点使用零依赖实现

## 如果问题仍然存在

### 方案 1: 进一步降级 typing-extensions

如果仍然有问题，尝试：

```txt
typing-extensions==4.5.0
pydantic==1.10.8
```

### 方案 2: 检查 Python 版本

在 `vercel.json` 中明确指定 Python 版本：

```json
{
  "env": {
    "PYTHON_VERSION": "3.11"
  }
}
```

### 方案 3: 使用 Edge Functions（JavaScript）

如果 Python 函数持续有问题，可以考虑使用 Vercel Edge Functions（JavaScript）来处理 webhook。

## 测试

运行本地测试：

```bash
python test_webhook_local.py
python test_webhook_vercel_format.py
```

如果本地测试通过但 Vercel 失败，说明是 Vercel 环境问题。

## 相关文件

- `api/requirements.txt` - 已修复的依赖版本
- `api/stripe_webhook.py` - 零依赖的 webhook 实现
- `api/index.py` - FastAPI 应用（使用固定版本）

