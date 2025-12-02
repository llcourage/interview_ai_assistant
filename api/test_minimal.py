"""
最小化测试：使用与 index.py 相同的导入延迟模式
"""
import json
import sys

# 完全避免模块级别的任何可能出错的导入
# 所有逻辑都在 handler 函数内部

def handler(request):
    """
    Vercel Python 函数入口
    使用最简单的格式，避免任何导入问题
    """
    try:
        # 获取请求信息
        method = request.get("method", "GET") if isinstance(request, dict) else "GET"
        
        # 返回成功响应
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "ok",
                "message": "Minimal test works",
                "method": method,
                "python_version": sys.version.split()[0],
                "handler_type": "minimal"
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
