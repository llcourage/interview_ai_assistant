"""
测试 Mangum handler 是否正确导出
"""
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入 webhook 模块
import importlib.util
spec = importlib.util.spec_from_file_location("stripe_webhook", Path(__file__).parent / "stripe.py")
stripe_webhook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stripe_webhook)

# 检查 handler
print("=" * 60)
print("🔍 检查 Handler 导出")
print("=" * 60)

# 检查 app
print(f"✅ app 类型: {type(stripe_webhook.app)}")
print(f"✅ app 是否存在: {hasattr(stripe_webhook, 'app')}")

# 检查 handler
print(f"✅ handler 类型: {type(stripe_webhook.handler)}")
print(f"✅ handler 是否存在: {hasattr(stripe_webhook, 'handler')}")

# 检查 handler 是否可调用
print(f"✅ handler 是否可调用: {callable(stripe_webhook.handler)}")

# 检查 Mangum 实例
if hasattr(stripe_webhook, 'handler'):
    handler = stripe_webhook.handler
    print(f"✅ handler 类: {handler.__class__}")
    print(f"✅ handler 模块: {handler.__class__.__module__}")
    
    # 尝试创建一个测试事件
    print("\n" + "=" * 60)
    print("🧪 测试 Handler 调用")
    print("=" * 60)
    
    # 模拟 Vercel 事件格式
    test_event = {
        "httpMethod": "GET",
        "path": "/",
        "headers": {},
        "body": None,
        "isBase64Encoded": False
    }
    
    try:
        # 注意：Mangum 需要 AWS Lambda 格式的事件
        # 这里只是测试 handler 是否存在和可调用
        print("✅ Handler 可以访问")
        print("⚠️  注意：Mangum 需要 AWS Lambda 格式的事件才能正常工作")
    except Exception as e:
        print(f"❌ Handler 测试失败: {e}")

print("\n" + "=" * 60)
print("✅ 检查完成")
print("=" * 60)

