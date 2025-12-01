"""
Vercel Serverless Function 适配器
将 FastAPI 应用适配为 Vercel Serverless Function
"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from mangum import Mangum
from main import app

# 创建 Mangum 适配器
# Vercel 会将 /api/* 的请求路由到这里
# Mangum 会自动处理路径匹配
handler = Mangum(app, lifespan="off")

