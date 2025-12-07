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
        except Exception as exc:
            # 记录详细的导入错误
            import traceback
            error_trace = traceback.format_exc()
            error_details = str(exc)  # Capture error details in local variable
            print(f"⚠️ 导入 FastAPI 应用时出错: {exc}")
            print(f"详细错误信息:\n{error_trace}")
            # 创建一个错误应用
            from fastapi import FastAPI, Request
            error_app = FastAPI()
            
            # Use default arguments to properly capture variables in closure
            def create_error_handler(err_msg: str, err_tb: str):
                async def error_handler(request: Request, path: str = ""):
                    return {
                        "error": "Failed to load application",
                        "details": err_msg,
                        "traceback": err_tb,
                        "path": str(request.url.path)
                    }
                return error_handler
            
            error_handler_func = create_error_handler(error_details, error_trace)
            
            error_app.get("/{path:path}")(error_handler_func)
            error_app.post("/{path:path}")(error_handler_func)
            error_app.put("/{path:path}")(error_handler_func)
            error_app.delete("/{path:path}")(error_handler_func)
            
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
        """处理所有 HTTP 请求 - 直接调用 FastAPI ASGI app"""
        try:
            # 打印日志到 Vercel（使用 print，会被 Vercel 捕获）
            print(f"🔥 Vercel Function 收到请求: {self.command} {self.path}")
            print(f"   - User-Agent: {self.headers.get('User-Agent', 'N/A')}")
            print(f"   - Origin: {self.headers.get('Origin', 'N/A')}")
            print(f"   - Content-Type: {self.headers.get('Content-Type', 'N/A')}")
            print(f"   - Method: {self.command}")
            print(f"   - Path (self.path): {self.path}")
            # 打印所有相关 headers 以调试路径问题
            for header_name in ['X-Rewrite-Url', 'X-Original-Url', 'X-Forwarded-Uri', 'X-Forwarded-Path']:
                header_value = self.headers.get(header_name)
                if header_value:
                    print(f"   - {header_name}: {header_value}")
            # 打印所有 headers（用于调试）
            print(f"   - All headers: {dict(self.headers)}")
            
            # 获取 FastAPI 应用
            app = get_app()
            
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
                
                # 直接调用 FastAPI app（它是 ASGI 应用）
                await app(scope, receive, send)
            
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
            
            # 记录响应状态（特别是 405 错误）
            if status == 405:
                print(f"⚠️ Method Not Allowed (405) for {self.command} {self.path}")
                print(f"   This usually means the route exists but doesn't support {self.command} method")
            
            # 发送响应
            # FastAPI 的 CORSMiddleware 已经设置了所有必要的 CORS 头部，不需要手动添加
            self.send_response(status)
            for header, value in headers:
                self.send_header(header.decode() if isinstance(header, bytes) else header,
                               value.decode() if isinstance(value, bytes) else value)
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
            
            # 错误响应也需要正确的 CORS 头部
            origin = self.headers.get('Origin', '')
            allowed_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "https://www.desktopai.org",
            ]
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Credentials", "true")
            else:
                # 如果不在白名单，使用默认值（但不使用 *，因为会与 credentials 冲突）
                self.send_header("Access-Control-Allow-Origin", "https://www.desktopai.org")
            self.end_headers()
            self.wfile.write(error_body)
    
    def _build_scope(self):
        """构建 ASGI scope"""
        import urllib.parse
        
        # 解析路径和查询字符串
        # Vercel 会将 /api/* 重写到 /api/index，但 self.path 应该保持原始路径
        # 例如：请求 /api/auth/exchange-code 时，self.path 应该是 "/api/auth/exchange-code"
        # 而不是 "/api/index"
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_string = parsed_path.query.encode()
        
        # 如果路径是 /api/index，可能是直接访问或路径丢失
        # 尝试从 header 中恢复原始路径
        if path == "/api/index" or path.startswith("/api/index"):
            print(f"   - ⚠️ Detected rewrite: path is {path}, attempting to recover original path")
            # Vercel 可能在不同的 header 中传递原始路径
            original_path = None
            
            # 尝试多个可能的 header
            for header_name in ['X-Rewrite-Url', 'X-Original-Url', 'X-Forwarded-Uri', 'X-Forwarded-Path']:
                header_value = self.headers.get(header_name)
                if header_value:
                    original_path = header_value
                    print(f"   - Found {header_name}: {original_path}")
                    break
            
            if original_path:
                parsed_path = urllib.parse.urlparse(original_path)
                path = parsed_path.path
                query_string = parsed_path.query.encode()
                print(f"   - ✅ Using original path: {path}")
            else:
                print(f"   - ⚠️ Warning: Path is {path} but no original path found in headers")
                print(f"   - ⚠️ This may cause routing issues. Checking if Vercel preserves path in self.path...")
                # 根据 Vercel 文档，self.path 应该保持原始路径
                # 如果这里仍然是 /api/index，可能是 Vercel 的行为变化
                # 在这种情况下，我们需要依赖 FastAPI 的路由匹配
        
        print(f"   - ✅ Final path for FastAPI: {path}")
        
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
