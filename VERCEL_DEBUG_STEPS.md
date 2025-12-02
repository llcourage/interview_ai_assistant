# 🔍 Vercel 500 错误调试步骤

## 当前状态

- ✅ 本地测试通过
- ❌ Vercel 返回 500 错误
- ❌ `test_minimal` 返回 404

## 调试步骤

### 1. 查看 Vercel 日志（最重要）

在 Vercel Dashboard：
1. 进入项目
2. 点击 **Functions** 标签
3. 找到 `api/stripe_webhook.py`
4. 点击进入函数详情
5. 点击 **Logs** 标签
6. 查看最新的错误日志

**需要的信息**：
- 完整的错误堆栈跟踪
- 错误发生的行号
- 具体的错误消息

### 2. 检查环境变量

在 Vercel Dashboard → **Settings** → **Environment Variables**：

确保设置了：
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` 或 `SUPABASE_ANON_KEY`

### 3. 测试不同的端点

尝试访问：
- `https://www.desktopai.org/api/stripe_webhook` (GET) - 应该返回健康检查
- `https://www.desktopai.org/api/test_minimal` - 测试最小化函数

### 4. 检查函数格式

Vercel Python 函数应该：
- 导出 `handler` 函数
- 接收 `request` 字典
- 返回包含 `statusCode`, `headers`, `body` 的字典

## 常见问题

### Q: 为什么本地测试通过但 Vercel 失败？

**A**: 可能的原因：
1. 环境变量未设置
2. Vercel Python 版本不同
3. 依赖安装问题
4. Vercel handler 的 bug

### Q: 如何获取详细的错误信息？

**A**: 
1. 查看 Vercel Dashboard 的 Logs
2. 使用 `vercel dev` 在本地模拟 Vercel 环境
3. 检查函数的返回内容

## 下一步

请提供：
1. Vercel Logs 中的完整错误信息
2. 错误发生的具体行号
3. 堆栈跟踪

这样我可以准确定位问题并修复。

