"""
Vercel Serverless Function 适配器
将 FastAPI 应用适配为 Vercel Serverless Function

Vercel Python runtime 要求 handler 必须是一个继承自 BaseHTTPRequestHandler 的类
"""
import sys
import os
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 延迟加载 FastAPI 应用和 Mangum
_mangum_handler = None

def get_mangum_handler():
    """获取或创建 Mangum handler（延迟导入）"""
    global _mangum_handler
    if _mangum_handler is None:
        try:
            from mangum import Mangum
            from main import app
            _mangum_handler = Mangum(app, lifespan="off")
        except Exception as e:
            # 记录详细的导入错误
            import traceback
            error_trace = traceback.format_exc()
            print(f"⚠️ 导入 FastAPI 应用时出错: {e}")
            print(f"详细错误信息:\n{error_trace}")
            # 创建一个错误应用
            from mangum import Mangum
            from fastapi import FastAPI, Request
            error_app = FastAPI()
            
            @error_app.get("/{path:path}")
            @error_app.post("/{path:path}")
            @error_app.put("/{path:path}")
            @error_app.delete("/{path:path}")
            async def error_handler(request: Request, path: str = ""):
                return {
                    "error": "Failed to load application",
                    "details": str(e),
                    "traceback": error_trace,
                    "path": str(request.url.path)
                }
            
            _mangum_handler = Mangum(error_app, lifespan="off")
    return _mangum_handler

class handler(BaseHTTPRequestHandler):
    """Vercel Python 函数入口 - 必须继承 BaseHTTPRequestHandler"""
    
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def do_PUT(self):
        self._handle_request()
    
    def do_DELETE(self):
        self._handle_request()
    
    def do_PATCH(self):
        self._handle_request()
    
    def do_OPTIONS(self):
        self._handle_request()
    
    def _handle_request(self):
        """处理所有 HTTP 请求"""
        try:
            # 获取 Mangum handler
            mangum_handler = get_mangum_handler()
            
            # 构建 ASGI scope
            scope = self._build_scope()
            
            # 创建 ASGI 应用调用
            from mangum.protocols.http import ASGIAdapter
            adapter = ASGIAdapter(mangum_handler.app)
            
            # 处理请求
            response = adapter(self._build_scope(), self._receive, self._send)
            
            # 等待响应完成
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(response)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ 处理请求时出错: {e}")
            print(f"详细错误信息:\n{error_trace}")
            
            # 返回错误响应
            error_body = json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "traceback": error_trace
            }).encode("utf-8")
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error_body)
    
    def _build_scope(self):
        """构建 ASGI scope"""
        import urllib.parse
        
        # 解析路径和查询字符串
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_string = parsed_path.query.encode()
        
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = b''
        if content_length > 0:
            body = self.rfile.read(content_length)
        
        # 构建 headers
        headers = []
        for key, value in self.headers.items():
            headers.append((key.lower().encode(), value.encode()))
        
        scope = {
            "type": "http",
            "method": self.command,
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string,
            "headers": headers,
            "body": body,
            "server": (self.headers.get('Host', 'localhost').split(':')[0], 80),
            "client": self.client_address,
            "scheme": "https" if self.headers.get('X-Forwarded-Proto') == 'https' else 'http',
            "http_version": self.request_version,
            "asgi": {"version": "3.0", "spec_version": "2.1"}
        }
        
        return scope
    
    async def _receive(self):
        """ASGI receive 函数"""
        return {
            "type": "http.request",
            "body": self._body if hasattr(self, '_body') else b'',
            "more_body": False
        }
    
    async def _send(self, message):
        """ASGI send 函数"""
        if message["type"] == "http.response.start":
            self.send_response(message["status"])
            for header, value in message.get("headers", []):
                self.send_header(header.decode(), value.decode())
            self.end_headers()
        elif message["type"] == "http.response.body":
            if "body" in message:
                self.wfile.write(message["body"])

