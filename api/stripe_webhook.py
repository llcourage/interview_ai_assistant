"""
Stripe Webhook 端点
放在 api/ 根目录，避免子目录可能导致的导入问题
"""
import os
import json
import hmac
import hashlib
import time

def handler(request):
    """
    Vercel Python 函数入口
    手动验证 Stripe webhook，不使用任何外部包
    """
    method = request.get("method", "GET")
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
                "endpoint": "/api/stripe_webhook",
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
            
            # 手动验证 webhook 签名
            body_bytes = body.encode() if isinstance(body, str) else body
            
            # 解析签名
            signatures = {}
            for item in sig_header.split(","):
                parts = item.split("=", 1)
                if len(parts) == 2:
                    signatures[parts[0]] = parts[1]
            
            timestamp = signatures.get("t")
            signature = signatures.get("v1")
            
            if not timestamp or not signature:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid signature format"})
                }
            
            # 检查时间戳（防止重放攻击）
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:  # 5 分钟
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Timestamp too old"})
                }
            
            # 计算签名
            signed_payload = f"{timestamp}.{body_bytes.decode() if isinstance(body_bytes, bytes) else body_bytes}"
            expected_signature = hmac.new(
                webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # 验证签名
            if not hmac.compare_digest(expected_signature, signature):
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid signature"})
                }
            
            # 解析事件
            try:
                event = json.loads(body_bytes.decode() if isinstance(body_bytes, bytes) else body_bytes)
            except json.JSONDecodeError as e:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON", "details": str(e)})
                }
            
            # 处理事件
            event_type = event.get("type")
            
            # 使用 HTTP 请求直接调用 Supabase API
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            if not supabase_url or not supabase_key:
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Supabase credentials not configured"})
                }
            
            # 使用 urllib 进行 HTTP 请求
            from urllib.request import Request, urlopen
            from urllib.error import HTTPError
            from datetime import datetime
            
            def supabase_request(method, table, data=None, filters=None):
                """使用 HTTP 请求调用 Supabase API"""
                url = f"{supabase_url}/rest/v1/{table}"
                if filters:
                    url += "?" + "&".join([f"{k}=eq.{v}" for k, v in filters.items()])
                
                req = Request(url)
                req.add_header("apikey", supabase_key)
                req.add_header("Authorization", f"Bearer {supabase_key}")
                req.add_header("Content-Type", "application/json")
                req.add_header("Prefer", "return=representation")
                
                if method == "GET":
                    req.get_method = lambda: "GET"
                elif method == "POST":
                    req.get_method = lambda: "POST"
                    req.data = json.dumps(data).encode() if data else None
                elif method == "PATCH":
                    req.get_method = lambda: "PATCH"
                    req.data = json.dumps(data).encode() if data else None
                
                try:
                    response = urlopen(req)
                    result = json.loads(response.read().decode())
                    return {"data": result if isinstance(result, list) else [result]}
                except HTTPError as e:
                    if e.code == 404:
                        return {"data": []}
                    raise
            
            if event_type == "checkout.session.completed":
                # 支付成功
                session = event.get("data", {}).get("object", {})
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
                
                # 检查记录是否存在
                response = supabase_request("GET", "user_plans", filters={"user_id": user_id})
                
                update_data = {
                    "plan": plan_value,
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "subscription_status": "active",
                    "updated_at": datetime.now().isoformat()
                }
                
                if response["data"]:
                    # 更新现有记录
                    supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", update_data)
                else:
                    # 创建新记录
                    insert_data = {
                        "user_id": user_id,
                        "plan": plan_value,
                        "created_at": datetime.now().isoformat(),
                        **update_data
                    }
                    supabase_request("POST", "user_plans", insert_data)
                
                print(f"✅ 用户 {user_id} 已升级到 {plan_value} plan")
                
            elif event_type == "customer.subscription.updated":
                # 订阅更新
                subscription = event.get("data", {}).get("object", {})
                customer_id = subscription.get("customer")
                status = subscription.get("status")
                
                if not customer_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing customer_id in subscription"})
                    }
                
                # 从数据库查找用户
                response = supabase_request("GET", "user_plans", filters={"stripe_customer_id": customer_id})
                
                if not response["data"]:
                    print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"status": "warning", "message": "User not found"})
                    }
                
                user_id = response["data"][0]["user_id"]
                
                if status == "active":
                    supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                        "subscription_status": "active",
                        "updated_at": datetime.now().isoformat()
                    })
                    print(f"✅ 用户 {user_id} 订阅已激活")
                elif status in ["canceled", "past_due", "unpaid"]:
                    supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                        "plan": "normal",
                        "subscription_status": status,
                        "updated_at": datetime.now().isoformat()
                    })
                    print(f"⚠️ 用户 {user_id} 订阅已取消/逾期，降级为 normal")
                    
            elif event_type == "customer.subscription.deleted":
                # 订阅删除
                subscription = event.get("data", {}).get("object", {})
                customer_id = subscription.get("customer")
                
                if not customer_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing customer_id in subscription"})
                    }
                
                # 从数据库查找用户
                response = supabase_request("GET", "user_plans", filters={"stripe_customer_id": customer_id})
                
                if not response["data"]:
                    print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"status": "warning", "message": "User not found"})
                    }
                
                user_id = response["data"][0]["user_id"]
                
                supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                    "plan": "normal",
                    "subscription_status": "canceled",
                    "updated_at": datetime.now().isoformat()
                })
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

