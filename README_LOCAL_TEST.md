# 🧪 本地测试 Webhook 函数

## 快速测试

运行测试脚本：

```bash
# 测试 1: 基本功能测试
python test_webhook_local.py

# 测试 2: Vercel 格式检查
python test_webhook_vercel_format.py
```

## 测试内容

### test_webhook_local.py
- ✅ 导入函数测试
- ✅ GET 请求测试（健康检查）
- ✅ POST 请求测试（无签名）
- ✅ 环境变量检查
- ✅ 模块导入检查

### test_webhook_vercel_format.py
- ✅ 文件存在性检查
- ✅ 文件读取测试
- ✅ 导入语句分析
- ✅ 语法编译测试
- ✅ 模块规范检查
- ✅ 模块级别代码检查

## 环境变量

创建 `.env` 文件（可选，用于完整测试）：

```env
STRIPE_WEBHOOK_SECRET=whsec_test_xxx
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
```

或者设置环境变量：

```bash
# Windows PowerShell
$env:STRIPE_WEBHOOK_SECRET="whsec_test_xxx"
$env:SUPABASE_URL="https://your-project.supabase.co"

# Linux/Mac
export STRIPE_WEBHOOK_SECRET="whsec_test_xxx"
export SUPABASE_URL="https://your-project.supabase.co"
```

## 预期结果

如果所有测试通过，说明：
- ✅ 代码语法正确
- ✅ 导入没有问题
- ✅ 函数逻辑正确

如果 Vercel 仍然报错，可能是：
- Vercel 环境配置问题
- Python 版本问题
- Vercel handler 的 bug

## 下一步

如果本地测试通过但 Vercel 失败，可以：
1. 检查 Vercel 的 Python 版本设置
2. 尝试使用不同的函数格式
3. 联系 Vercel 支持

