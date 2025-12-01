"""
测试 handler 是否能处理 Vercel 格式的事件
"""
import sys
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入 webhook 模块
import importlib.util
spec = importlib.util.spec_from_file_location("stripe_webhook", Path(__file__).parent / "stripe.py")
stripe_webhook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stripe_webhook)

print("=" * 60)
print("🧪 测试 Vercel 格式的事件")
print("=" * 60)

# 模拟 Vercel/AWS Lambda 格式的事件
test_event = {
    "httpMethod": "GET",
    "path": "/",
    "headers": {
        "Host": "localhost:8001",
        "User-Agent": "test"
    },
    "queryStringParameters": None,
    "body": None,
    "isBase64Encoded": False
}

test_context = {}

try:
    print("📤 发送测试事件...")
    print(f"   Method: {test_event['httpMethod']}")
    print(f"   Path: {test_event['path']}")
    
    # 调用 handler
    result = stripe_webhook.handler(test_event, test_context)
    
    print("✅ Handler 调用成功")
    print(f"   返回类型: {type(result)}")
    
    if isinstance(result, dict):
        print(f"   状态码: {result.get('statusCode', 'N/A')}")
        if 'body' in result:
            try:
                body = json.loads(result['body'])
                print(f"   响应体: {json.dumps(body, indent=2, ensure_ascii=False)}")
            except:
                print(f"   响应体: {result['body']}")
    
except Exception as e:
    print(f"❌ Handler 调用失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60)

