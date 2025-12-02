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

# 延迟加载 FastAPI 应用
_app = None

def get_app():
    """获取或创建 FastAPI 应用（延迟导入）"""
    global _app
    if _app is None:
        try:
            from main import app
            _app = app
        except Exception as e:
            # 记录详细的导入错误
            import traceback
            error_trace = traceback.format_exc()
            print(f"⚠️ 导入 FastAPI 应用时出错: {e}")
            print(f"详细错误信息:\n{error_trace}")
            # 创建一个错误应用
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
            
            _app = error_app
    return _app

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
        """处理所有 HTTP 请求 - 使用 Mangum 适配 FastAPI"""
        try:
            # 获取 FastAPI 应用
            app = get_app()
            
            # 使用 Mangum 处理请求
            from mangum import Mangum
            mangum_handler = Mangum(app, lifespan="off")
            
            # 构建 ASGI scope
            scope = self._build_scope()
            
            # 创建消息队列
            receive_queue = []
            send_queue = []
            
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                receive_queue.append({
                    "type": "http.request",
                    "body": body,
                    "more_body": False
                })
            else:
                receive_queue.append({
                    "type": "http.request",
                    "body": b"",
                    "more_body": False
                })
            
            # 异步处理请求
            import asyncio
            
            async def run_app():
                async def receive():
                    return receive_queue.pop(0) if receive_queue else {"type": "http.disconnect"}
                
                async def send(message):
                    send_queue.append(message)
                
                await mangum_handler(scope, receive, send)
            
            # 运行异步应用
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(run_app())
            
            # 处理响应
            status = 200
            headers = []
            body = b""
            
            for message in send_queue:
                if message["type"] == "http.response.start":
                    status = message["status"]
                    headers = message.get("headers", [])
                elif message["type"] == "http.response.body":
                    body += message.get("body", b"")
            
            # 发送响应
            self.send_response(status)
            for header, value in headers:
                self.send_header(header.decode() if isinstance(header, bytes) else header,
                               value.decode() if isinstance(value, bytes) else value)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            
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
        
        # 构建 headers
        headers = []
        for key, value in self.headers.items():
            headers.append((key.lower().encode(), value.encode()))
        
        # 获取 host
        host = self.headers.get('Host', 'localhost')
        if ':' in host:
            server_host, server_port = host.split(':', 1)
            server_port = int(server_port)
        else:
            server_host = host
            server_port = 80
        
        scope = {
            "type": "http",
            "method": self.command,
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string,
            "headers": headers,
            "server": (server_host, server_port),
            "client": self.client_address,
            "scheme": "https" if self.headers.get('X-Forwarded-Proto') == 'https' else 'http',
            "http_version": self.request_version,
            "asgi": {"version": "3.0", "spec_version": "2.1"}
        }
        
        return scope
