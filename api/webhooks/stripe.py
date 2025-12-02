"""
独立的 Stripe Webhook 端点
使用 Vercel 原生 Python 函数格式，不使用 FastAPI/Mangum
"""
import os
import json

def handler(request):
    """
    Vercel Python 函数入口
    request 是一个字典，包含：
    - method: HTTP 方法
    - path: 请求路径
    - headers: 请求头
    - body: 请求体（字符串）
    """
    # 延迟导入所有依赖
    try:
        import stripe
        from supabase import create_client
        from datetime import datetime
    except ImportError as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Import error: {str(e)}"})
        }
    
    method = request.get("method", "GET")
    path = request.get("path", "")
    headers = request.get("headers", {})
    body = request.get("body", "")
    
    # GET 请求：健康检查
    if method == "GET":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "ok",
                "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events.",
                "endpoint": "/api/webhooks/stripe",
                "methods": ["POST", "GET"]
            })
        }
    
    # POST 请求：处理 Webhook
    if method == "POST":
        try:
            # 获取 webhook secret
            webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
            if not webhook_secret:
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Webhook secret not configured"})
                }
            
            # 获取签名
            sig_header = headers.get("stripe-signature") or headers.get("Stripe-Signature")
            if not sig_header:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing stripe-signature header"})
                }
            
            # 验证 webhook
            try:
                event = stripe.Webhook.construct_event(
                    body.encode() if isinstance(body, str) else body,
                    sig_header,
                    webhook_secret
                )
            except ValueError as e:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid payload", "details": str(e)})
                }
            except stripe.error.SignatureVerificationError as e:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid signature", "details": str(e)})
                }
            
            # 处理事件
            event_type = event["type"]
            
            # 获取 Supabase 客户端
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            if not supabase_url or not supabase_key:
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Supabase credentials not configured"})
                }
            
            supabase = create_client(supabase_url, supabase_key)
            
            if event_type == "checkout.session.completed":
                # 支付成功
                session = event["data"]["object"]
                user_id = session.get("metadata", {}).get("user_id")
                plan_value = session.get("metadata", {}).get("plan", "normal")
                subscription_id = session.get("subscription")
                customer_id = session.get("customer")
                
                if not user_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing user_id in session metadata"})
                    }
                
                # 更新用户 Plan
                update_data = {
                    "plan": plan_value,
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "subscription_status": "active",
                    "updated_at": datetime.now().isoformat()
                }
                
                # 检查记录是否存在
                response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
                
                if response.data:
                    supabase.table("user_plans").update(update_data).eq("user_id", user_id).execute()
                else:
                    insert_data = {
                        "user_id": user_id,
                        "plan": plan_value,
                        "created_at": datetime.now().isoformat(),
                        **update_data
                    }
                    supabase.table("user_plans").insert(insert_data).execute()
                
                print(f"✅ 用户 {user_id} 已升级到 {plan_value} plan")
                
            elif event_type == "customer.subscription.updated":
                # 订阅更新
                subscription = event["data"]["object"]
                customer_id = subscription.get("customer")
                status = subscription.get("status")
                
                if not customer_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing customer_id in subscription"})
                    }
                
                # 从数据库查找用户
                response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).single().execute()
                
                if not response.data:
                    print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"status": "warning", "message": "User not found"})
                    }
                
                user_id = response.data["user_id"]
                
                if status == "active":
                    supabase.table("user_plans").update({
                        "subscription_status": "active",
                        "updated_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
                    print(f"✅ 用户 {user_id} 订阅已激活")
                elif status in ["canceled", "past_due", "unpaid"]:
                    supabase.table("user_plans").update({
                        "plan": "normal",
                        "subscription_status": status,
                        "updated_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
                    print(f"⚠️ 用户 {user_id} 订阅已取消/逾期，降级为 normal")
                    
            elif event_type == "customer.subscription.deleted":
                # 订阅删除
                subscription = event["data"]["object"]
                customer_id = subscription.get("customer")
                
                if not customer_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing customer_id in subscription"})
                    }
                
                # 从数据库查找用户
                response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).single().execute()
                
                if not response.data:
                    print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"status": "warning", "message": "User not found"})
                    }
                
                user_id = response.data["user_id"]
                
                supabase.table("user_plans").update({
                    "plan": "normal",
                    "subscription_status": "canceled",
                    "updated_at": datetime.now().isoformat()
                }).eq("user_id", user_id).execute()
                print(f"⚠️ 用户 {user_id} 订阅已删除，降级为 normal")
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"status": "success", "event_type": event_type})
            }
            
        except Exception as e:
            print(f"❌ 处理 Webhook 事件失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to process webhook", "details": str(e)})
            }
    
    # 其他方法
    return {
        "statusCode": 405,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "Method not allowed"})
    }
