"""
独立的 Stripe Webhook 端点
用于 Vercel Serverless Function
完全内联实现，不依赖 backend 模块
"""
import os
import json
from mangum import Mangum
from fastapi import FastAPI, HTTPException, Request
import stripe
from supabase import create_client, Client

# 创建 FastAPI 应用（仅用于 webhook）
app = FastAPI()

def get_supabase() -> Client:
    """获取 Supabase 客户端"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url:
        raise HTTPException(
            status_code=500, 
            detail="SUPABASE_URL environment variable is not configured. Please set it in Vercel Dashboard → Settings → Environment Variables."
        )
    
    if not supabase_key:
        raise HTTPException(
            status_code=500, 
            detail="SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY environment variable is not configured. Please set it in Vercel Dashboard → Settings → Environment Variables."
        )
    
    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Supabase client: {str(e)}"
        )

async def update_user_plan_inline(
    user_id: str,
    plan: str = None,
    stripe_customer_id: str = None,
    stripe_subscription_id: str = None,
    subscription_status: str = None
):
    """内联实现更新用户 Plan"""
    supabase = get_supabase()
    
    update_data = {}
    if plan:
        update_data["plan"] = plan
    if stripe_customer_id:
        update_data["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id:
        update_data["stripe_subscription_id"] = stripe_subscription_id
    if subscription_status:
        update_data["subscription_status"] = subscription_status
    
    from datetime import datetime
    update_data["updated_at"] = datetime.now().isoformat()
    
    # 检查记录是否存在
    response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
    
    if response.data:
        # 更新现有记录
        supabase.table("user_plans").update(update_data).eq("user_id", user_id).execute()
    else:
        # 创建新记录
        from datetime import datetime
        insert_data = {
            "user_id": user_id,
            "plan": plan or "normal",
            "created_at": datetime.now().isoformat(),
            **update_data
        }
        supabase.table("user_plans").insert(insert_data).execute()

@app.get("/")
async def webhook_get():
    """Webhook 端点健康检查"""
    # 检查必要的环境变量
    env_status = {
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        "STRIPE_WEBHOOK_SECRET": bool(os.getenv("STRIPE_WEBHOOK_SECRET"))
    }
    
    all_configured = all(env_status.values())
    
    return {
        "status": "ok" if all_configured else "warning",
        "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events." if all_configured else "Endpoint is active but some environment variables are missing.",
        "endpoint": "/api/webhooks/stripe",
        "methods": ["POST", "GET"],
        "environment_variables": env_status,
        "ready": all_configured
    }

@app.post("/")
async def webhook_post(request: Request):
    """Stripe Webhook 处理"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not webhook_secret:
        raise HTTPException(
            status_code=500, 
            detail="STRIPE_WEBHOOK_SECRET environment variable is not configured. Please set it in Vercel Dashboard → Settings → Environment Variables. You can get the webhook secret from Stripe Dashboard → Developers → Webhooks → Your endpoint → Signing secret."
        )
    
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
            # 支付成功
            session = event["data"]["object"]
            user_id = session["metadata"].get("user_id")
            plan_value = session["metadata"].get("plan", "normal")
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            
            if not user_id:
                raise HTTPException(status_code=400, detail="Missing user_id in session metadata")
            
            await update_user_plan_inline(
                user_id=user_id,
                plan=plan_value,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                subscription_status="active"
            )
            
            print(f"✅ 用户 {user_id} 已升级到 {plan_value} plan")
            
        elif event_type == "customer.subscription.updated":
            # 订阅更新
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            status = subscription.get("status")
            
            if not customer_id:
                raise HTTPException(status_code=400, detail="Missing customer_id in subscription")
            
            # 从数据库查找用户
            supabase = get_supabase()
            response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).single().execute()
            
            if not response.data:
                print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                return {"status": "warning", "message": "User not found"}
            
            user_id = response.data["user_id"]
            
            if status == "active":
                await update_user_plan_inline(
                    user_id=user_id,
                    subscription_status="active"
                )
                print(f"✅ 用户 {user_id} 订阅已激活")
            elif status in ["canceled", "past_due", "unpaid"]:
                await update_user_plan_inline(
                    user_id=user_id,
                    plan="normal",
                    subscription_status=status
                )
                print(f"⚠️ 用户 {user_id} 订阅已取消/逾期，降级为 normal")
                
        elif event_type == "customer.subscription.deleted":
            # 订阅删除
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            
            if not customer_id:
                raise HTTPException(status_code=400, detail="Missing customer_id in subscription")
            
            # 从数据库查找用户
            supabase = get_supabase()
            response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).single().execute()
            
            if not response.data:
                print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                return {"status": "warning", "message": "User not found"}
            
            user_id = response.data["user_id"]
            
            await update_user_plan_inline(
                user_id=user_id,
                plan="normal",
                subscription_status="canceled"
            )
            print(f"⚠️ 用户 {user_id} 订阅已删除，降级为 normal")
        
        return {"status": "success", "event_type": event_type}
    except Exception as e:
        print(f"❌ 处理 Webhook 事件失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")

# Vercel Serverless Function handler
# 直接导出 Mangum handler（与 api/index.py 保持一致）
handler = Mangum(app, lifespan="off")
