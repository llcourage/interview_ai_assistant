"""
最小化测试：只有最基本的 handler
用于测试是否是代码结构导致的问题
"""
import json

def handler(request):
    """最简单的 handler"""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "message": "Minimal test works"})
    }

