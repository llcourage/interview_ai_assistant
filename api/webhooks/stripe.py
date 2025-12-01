"""
独立的 Stripe Webhook 端点
用于 Vercel Serverless Function
"""
import sys
import os
from pathlib import Path

from mangum import Mangum
from fastapi import FastAPI, HTTPException, Request
import stripe

# 创建 FastAPI 应用（仅用于 webhook）
app = FastAPI()

@app.get("/")
async def webhook_get():
    """Webhook 端点健康检查"""
    return {
        "status": "ok",
        "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events.",
        "endpoint": "/api/webhooks/stripe",
        "methods": ["POST"]
    }

@app.post("/")
async def webhook_post(request: Request):
    """Stripe Webhook 处理"""
    # 延迟导入 backend 模块，避免模块级别的导入问题
    backend_path = Path(__file__).parent.parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # 在函数内部导入，避免模块级别的导入错误
    from payment_stripe import (
        handle_checkout_completed,
        handle_subscription_updated,
        handle_subscription_deleted
    )
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # 处理不同的事件类型
    event_type = event["type"]
    
    try:
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            await handle_checkout_completed(session)
        elif event_type == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await handle_subscription_updated(subscription)
        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await handle_subscription_deleted(subscription)
        
        return {"status": "success", "event_type": event_type}
    except Exception as e:
        print(f"❌ 处理 Webhook 事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")

# Vercel Serverless Function handler
handler = Mangum(app, lifespan="off")

