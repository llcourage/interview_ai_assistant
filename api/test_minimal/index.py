"""
最小化测试：完全独立的函数，不依赖任何第三方库
放在独立目录中，使用独立的 requirements.txt
"""
import json
import sys

def handler(request):
    """
    Vercel Python 函数入口
    只使用标准库，避免任何依赖冲突
    """
    try:
        # 获取请求信息
        method = "GET"
        if isinstance(request, dict):
            method = request.get("method", "GET")
        
        # 返回成功响应
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "ok",
                "message": "Minimal test works - isolated function",
                "method": method,
                "python_version": sys.version.split()[0],
                "handler_type": "minimal_isolated"
            })
        }
    except Exception as e:
        # 捕获所有可能的错误
        import traceback
        error_trace = traceback.format_exc()
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Handler execution failed",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": error_trace
            })
        }

