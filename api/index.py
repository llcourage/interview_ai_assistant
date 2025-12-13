"""
Vercel Serverless Function Adapter
Adapts FastAPI application to Vercel Serverless Function

Vercel Python runtime requires handler to be a class inheriting from BaseHTTPRequestHandler
"""
import sys
import os
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# Add backend directory to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Lazy load FastAPI application
_app = None

def get_app():
    """Get or create FastAPI application (lazy import)"""
    global _app
    if _app is None:
        try:
            from main import app
            _app = app
        except Exception as exc:
            # Log detailed import error
            import traceback
            error_trace = traceback.format_exc()
            error_details = str(exc)  # Capture error details in local variable
            print(f"⚠️ Error importing FastAPI application: {exc}")
            print(f"Detailed error information:\n{error_trace}")
            # Create an error application
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
    """Vercel Python function entry point - must inherit from BaseHTTPRequestHandler"""
    
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
        """Handle all HTTP requests - directly call FastAPI ASGI app"""
        try:
            # Print logs to Vercel (using print, will be captured by Vercel)
            print(f"🔥 Vercel Function received request: {self.command} {self.path}")
            print(f"   - User-Agent: {self.headers.get('User-Agent', 'N/A')}")
            print(f"   - Origin: {self.headers.get('Origin', 'N/A')}")
            print(f"   - Content-Type: {self.headers.get('Content-Type', 'N/A')}")
            print(f"   - Method: {self.command}")
            print(f"   - Path (self.path): {self.path}")
            # Print all relevant headers to debug path issues
            for header_name in ['X-Rewrite-Url', 'X-Original-Url', 'X-Forwarded-Uri', 'X-Forwarded-Path']:
                header_value = self.headers.get(header_name)
                if header_value:
                    print(f"   - {header_name}: {header_value}")
            # Print all headers (for debugging)
            print(f"   - All headers: {dict(self.headers)}")
            
            # Get FastAPI application
            app = get_app()
            
            # Build ASGI scope
            scope = self._build_scope()
            
            # Create message queues
            receive_queue = []
            send_queue = []
            
            # Read request body
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
            
            # Process request asynchronously
            import asyncio
            
            async def run_app():
                async def receive():
                    return receive_queue.pop(0) if receive_queue else {"type": "http.disconnect"}
                
                async def send(message):
                    send_queue.append(message)
                
                # Directly call FastAPI app (it's an ASGI application)
                await app(scope, receive, send)
            
            # Run async application
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(run_app())
            
            # Process response
            status = 200
            headers = []
            body = b""
            
            for message in send_queue:
                if message["type"] == "http.response.start":
                    status = message["status"]
                    headers = message.get("headers", [])
                elif message["type"] == "http.response.body":
                    body += message.get("body", b"")
            
            # Log response status (especially 405 errors)
            if status == 405:
                print(f"⚠️ Method Not Allowed (405) for {self.command} {self.path}")
                print(f"   This usually means the route exists but doesn't support {self.command} method")
            
            # Send response
            # FastAPI's CORSMiddleware has already set all necessary CORS headers, no need to add manually
            self.send_response(status)
            for header, value in headers:
                self.send_header(header.decode() if isinstance(header, bytes) else header,
                               value.decode() if isinstance(value, bytes) else value)
            self.end_headers()
            self.wfile.write(body)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ Error processing request: {e}")
            print(f"Detailed error information:\n{error_trace}")
            
            # Return error response
            error_body = json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "traceback": error_trace
            }).encode("utf-8")
            
            # Error response also needs correct CORS headers
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
                # If not in whitelist, use default (but don't use *, as it conflicts with credentials)
                self.send_header("Access-Control-Allow-Origin", "https://www.desktopai.org")
            self.end_headers()
            self.wfile.write(error_body)
    
    def _build_scope(self):
        """Build ASGI scope"""
        import urllib.parse
        
        # Parse path and query string
        # Vercel will rewrite /api/* to /api/index, but self.path should maintain original path
        # For example: when requesting /api/auth/exchange-code, self.path should be "/api/auth/exchange-code"
        # not "/api/index"
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_string = parsed_path.query.encode()
        
        # If path is /api/index, might be direct access or path lost
        # Try to recover original path from headers
        if path == "/api/index" or path.startswith("/api/index"):
            print(f"   - ⚠️ Detected rewrite: path is {path}, attempting to recover original path")
            # Vercel might pass original path in different headers
            original_path = None
            
            # Try multiple possible headers
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
                # According to Vercel docs, self.path should maintain original path
                # If it's still /api/index here, might be a change in Vercel behavior
                # In this case, we need to rely on FastAPI route matching
        
        print(f"   - ✅ Final path for FastAPI: {path}")
        
        # Build headers
        headers = []
        for key, value in self.headers.items():
            headers.append((key.lower().encode(), value.encode()))
        
        # Get host
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
