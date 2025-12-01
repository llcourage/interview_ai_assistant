"""
独立的 Stripe Webhook 端点
用于 Vercel Serverless Function
"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

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
    
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session)
    elif event_type == "customer.subscription.updated":
        subscription = event["data"]["object"]
        await handle_subscription_updated(subscription)
    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_deleted(subscription)
    
    return {"status": "success"}

# Vercel Serverless Function handler
handler = Mangum(app, lifespan="off")

