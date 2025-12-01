"""
本地测试 webhook 端点
直接运行 FastAPI 应用，不使用 Vercel 环境
"""
import uvicorn
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 直接导入并运行 webhook 应用
# 为了避免与 stripe 包名冲突，我们直接导入文件
import importlib.util
spec = importlib.util.spec_from_file_location("stripe_webhook", Path(__file__).parent / "stripe.py")
stripe_webhook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stripe_webhook)
app = stripe_webhook.app

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 本地 Webhook 测试服务器")
    print("=" * 60)
    print("📡 服务地址: http://localhost:8001")
    print("🔗 Webhook 端点: http://localhost:8001/")
    print("📚 健康检查: http://localhost:8001/ (GET)")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info",
        reload=False
    )

