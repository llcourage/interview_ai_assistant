"""
本地测试 Stripe Webhook 函数
模拟 Vercel 环境，测试 webhook 是否能正常工作
"""
import os
import sys
import json
from pathlib import Path

# 添加 api 目录到路径
api_path = Path(__file__).parent / "api"
sys.path.insert(0, str(api_path))

# 模拟 Vercel 的 request 格式
def create_test_request(method="GET", body="", headers=None):
    """创建测试请求"""
    return {
        "method": method,
        "path": "/api/stripe_webhook",
        "headers": headers or {},
        "body": body
    }

# 测试 1: 导入函数
print("=" * 60)
print("测试 1: 导入 webhook 函数")
print("=" * 60)
try:
    from stripe_webhook import handler
    print("✅ 成功导入 handler 函数")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 2: GET 请求（健康检查）
print("\n" + "=" * 60)
print("测试 2: GET 请求（健康检查）")
print("=" * 60)
try:
    request = create_test_request("GET")
    response = handler(request)
    print(f"状态码: {response.get('statusCode')}")
    print(f"响应体: {response.get('body')}")
    if response.get('statusCode') == 200:
        print("✅ GET 请求成功")
    else:
        print(f"❌ GET 请求失败，状态码: {response.get('statusCode')}")
except Exception as e:
    print(f"❌ GET 请求出错: {e}")
    import traceback
    traceback.print_exc()

# 测试 3: POST 请求（无签名，应该返回错误）
print("\n" + "=" * 60)
print("测试 3: POST 请求（无签名，应该返回错误）")
print("=" * 60)
try:
    test_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "user_id": "test_user_123",
                    "plan": "normal"
                },
                "subscription": "sub_test",
                "customer": "cus_test"
            }
        }
    }
    request = create_test_request(
        "POST",
        body=json.dumps(test_event),
        headers={}
    )
    response = handler(request)
    print(f"状态码: {response.get('statusCode')}")
    print(f"响应体: {response.get('body')}")
    if response.get('statusCode') == 400:
        print("✅ 正确返回 400 错误（缺少签名）")
    else:
        print(f"⚠️ 预期 400，实际: {response.get('statusCode')}")
except Exception as e:
    print(f"❌ POST 请求出错: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 检查环境变量
print("\n" + "=" * 60)
print("测试 4: 检查环境变量")
print("=" * 60)
env_vars = [
    "STRIPE_WEBHOOK_SECRET",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_ANON_KEY"
]
missing_vars = []
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: 已设置 ({value[:10]}...)")
    else:
        print(f"❌ {var}: 未设置")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️ 缺少环境变量: {', '.join(missing_vars)}")
    print("提示: 创建 .env 文件或设置环境变量")
else:
    print("\n✅ 所有环境变量都已设置")

# 测试 5: 检查模块导入
print("\n" + "=" * 60)
print("测试 5: 检查所有导入的模块")
print("=" * 60)
try:
    import os
    import json
    import hmac
    import hashlib
    import time
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from datetime import datetime
    print("✅ 所有标准库模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print("\n如果所有测试通过，说明代码本身没问题。")
print("如果 Vercel 仍然报错，可能是 Vercel 环境的问题。")

