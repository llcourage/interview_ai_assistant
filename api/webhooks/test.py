"""
测试文件：检查是否是 stripe 包导致的问题
"""
import os
import json

def handler(request):
    """最简单的测试 handler"""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "message": "Test endpoint works"})
    }

