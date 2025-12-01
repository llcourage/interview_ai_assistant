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
    from mangum import Mangum
    from main import app
    return Mangum(app, lifespan="off")

# 创建 handler（延迟执行）
try:
    handler = create_handler()
except Exception as e:
    # 如果导入失败，记录错误但继续
    print(f"⚠️ 导入 FastAPI 应用时出错: {e}")
    import traceback
    traceback.print_exc()
    # 创建一个错误 handler
    from mangum import Mangum
    from fastapi import FastAPI
    error_app = FastAPI()
    @error_app.get("/{path:path}")
    @error_app.post("/{path:path}")
    async def error_handler():
        return {"error": "Failed to load application", "details": str(e)}
    handler = Mangum(error_app, lifespan="off")

