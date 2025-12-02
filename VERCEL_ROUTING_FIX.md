# 🔧 Vercel API 路由修复说明

## 问题

`/api/plan/checkout` 返回 404 错误，说明 Vercel 没有正确路由到 FastAPI 应用。

## 原因

在 Vercel 中，`api/index.py` 默认只处理 `/api` 路径，而不自动处理 `/api/*` 子路径。需要明确配置 `rewrites` 规则来将子路径路由到 FastAPI 应用。

## 解决方案

我已经更新了 `vercel.json`，添加了 `rewrites` 规则来明确路由以下路径到 `api/index.py`：

- `/api/plan/*` - Plan 管理相关 API
- `/api/chat` - Chat API
- `/api/vision_query` - 视觉分析 API
- `/api/speech_to_text` - 语音转文字 API
- `/api/plan` - Plan 信息 API

## 注意事项

以下路径**不会**被重写，因为它们有独立的函数文件：

- `/api/test_api` → `api/test_api.py`
- `/api/stripe_webhook` → `api/stripe_webhook.py`

## 部署后测试

1. 等待 Vercel 重新部署完成
2. 测试 `/api/test_api` 是否工作
3. 测试 `/api/plan/checkout` 是否工作

如果还有问题，可能需要检查：
- Vercel 函数日志
- FastAPI 应用是否正确加载
- 环境变量是否正确配置

