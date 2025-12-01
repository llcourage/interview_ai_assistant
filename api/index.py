"""
Vercel Serverless Function 适配器
将 FastAPI 应用适配为 Vercel Serverless Function
使用延迟导入避免模块级别的导入错误
"""
import sys
import os
from pathlib import Path
from mangum import Mangum

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 延迟导入 FastAPI 应用，避免模块级别的导入错误
def get_app():
    """延迟导入 FastAPI 应用"""
    from main import app
    return app

# 创建应用实例（延迟加载）
_app = None

def get_handler():
    """获取 Mangum handler"""
    global _app
    if _app is None:
        _app = get_app()
    return Mangum(_app, lifespan="off")

# Vercel 会调用这个 handler
# 延迟创建，避免在模块级别导入时出错
handler = None

def __getattr__(name):
    """延迟创建 handler"""
    if name == "handler":
        global handler
        if handler is None:
            handler = get_handler()
        return handler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# 为了兼容性，也直接创建 handler（但使用延迟导入）
try:
    handler = get_handler()
except Exception as e:
    # 如果导入失败，handler 会在第一次调用时创建
    print(f"⚠️ 延迟导入 FastAPI 应用: {e}")
    handler = None

