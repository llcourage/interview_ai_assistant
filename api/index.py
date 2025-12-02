"""
Vercel Serverless Function 适配器
将 FastAPI 应用适配为 Vercel Serverless Function
"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 导入必须在函数内部进行，避免模块级别的导入错误
def create_handler():
    """创建 Mangum handler（延迟导入）"""
    try:
        from mangum import Mangum
        from main import app
        return Mangum(app, lifespan="off")
    except Exception as e:
        # 记录详细的导入错误
        import traceback
        error_trace = traceback.format_exc()
        print(f"⚠️ 导入 FastAPI 应用时出错: {e}")
        print(f"详细错误信息:\n{error_trace}")
        raise

# 创建 handler（延迟执行）
try:
    handler = create_handler()
except Exception as e:
    # 如果导入失败，记录错误并创建一个错误 handler
    import traceback
    error_trace = traceback.format_exc()
    print(f"⚠️ 创建 handler 时出错: {e}")
    print(f"详细错误信息:\n{error_trace}")
    
    # 创建一个错误 handler，返回详细的错误信息
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
    
    handler = Mangum(error_app, lifespan="off")

