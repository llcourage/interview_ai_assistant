"""
最小化测试：使用 Vercel 官方要求的格式
必须是继承 BaseHTTPRequestHandler 的 handler 类
"""
from http.server import BaseHTTPRequestHandler
import json
import sys

class handler(BaseHTTPRequestHandler):
    """
    Vercel Python 函数入口
    官方要求：必须是继承 BaseHTTPRequestHandler 的 handler 类
    """
    
    def do_GET(self):
        """处理 GET 请求"""
        try:
            body = {
                "status": "ok",
                "message": "Minimal test works - Vercel format",
                "method": "GET",
                "python_version": sys.version.split()[0],
                "handler_type": "BaseHTTPRequestHandler"
            }
            
            body_bytes = json.dumps(body).encode("utf-8")
            
            # 状态码
            self.send_response(200)
            # 头
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # body
            self.wfile.write(body_bytes)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            
            error_body = {
                "error": "Handler execution failed",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": error_trace,
            }
            
            body_bytes = json.dumps(error_body).encode("utf-8")
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body_bytes)
    
    def do_POST(self):
        """处理 POST 请求"""
        self.do_GET()  # 暂时复用 GET 逻辑

