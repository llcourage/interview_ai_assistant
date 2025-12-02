"""
Stripe Webhook 端点
使用 Vercel 官方要求的格式：继承 BaseHTTPRequestHandler 的 handler 类
"""
from http.server import BaseHTTPRequestHandler
import os
import json
import hmac
import hashlib
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    """Vercel Python 函数入口 - 必须是继承 BaseHTTPRequestHandler 的 handler 类"""
    
    def do_GET(self):
        """处理 GET 请求（健康检查）"""
        try:
            body = {
                "status": "ok",
                "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events.",
                "endpoint": "/api/stripe_webhook",
                "methods": ["POST", "GET"]
            }
            
            body_bytes = json.dumps(body).encode("utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body_bytes)
        except Exception as e:
            self._send_error(500, str(e))
    
    def do_POST(self):
        """处理 POST 请求（Stripe Webhook）"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_length)
            body_str = body_bytes.decode('utf-8')
            
            # 获取 webhook secret
            webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
            if not webhook_secret:
                self._send_error(500, "Webhook secret not configured")
                return
            
            # 获取签名
            sig_header = self.headers.get("stripe-signature") or self.headers.get("Stripe-Signature")
            if not sig_header:
                self._send_error(400, "Missing stripe-signature header")
                return
            
            # 手动验证 webhook 签名
            signatures = {}
            for item in sig_header.split(","):
                parts = item.split("=", 1)
                if len(parts) == 2:
                    signatures[parts[0]] = parts[1]
            
            timestamp = signatures.get("t")
            signature = signatures.get("v1")
            
            if not timestamp or not signature:
                self._send_error(400, "Invalid signature format")
                return
            
            # 检查时间戳（防止重放攻击）
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:  # 5 分钟
                self._send_error(400, "Timestamp too old")
                return
            
            # 计算签名
            signed_payload = f"{timestamp}.{body_str}"
            expected_signature = hmac.new(
                webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # 验证签名
            if not hmac.compare_digest(expected_signature, signature):
                self._send_error(400, "Invalid signature")
                return
            
            # 解析事件
            try:
                event = json.loads(body_str)
            except json.JSONDecodeError as e:
                self._send_error(400, f"Invalid JSON: {str(e)}")
                return
            
            # 处理事件
            event_type = event.get("type")
            result = self._handle_stripe_event(event_type, event)
            
            # 返回成功响应
            response_body = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response_body)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Webhook 处理失败: {e}")
            print(error_details)
            self._send_error(500, str(e))
    
    def _handle_stripe_event(self, event_type, event):
        """处理 Stripe 事件"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise Exception("Supabase credentials not configured")
        
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
                error_body = e.read().decode()
                print(f"Supabase HTTP Error: {e.code} - {error_body}")
                raise
        
        if event_type == "customer.subscription.created":
            # 订阅创建（通常由 checkout.session.completed 触发，但为了完整性也处理）
            subscription = event.get("data", {}).get("object", {})
            customer_id = subscription.get("customer")
            subscription_id = subscription.get("id")
            
            if not customer_id:
                raise Exception("Missing customer_id in subscription")
            
            # 从数据库查找用户
            response = supabase_request("GET", "user_plans", filters={"stripe_customer_id": customer_id})
            
            if not response["data"]:
                # 如果用户记录不存在，可能是通过其他方式创建的订阅，记录日志但不处理
                print(f"⚠️ 订阅创建但未找到用户: customer_id={customer_id}")
                return {"status": "warning", "message": "User not found for subscription creation"}
            
            user_id = response["data"][0]["user_id"]
            
            # 更新订阅ID（如果还没有）
            supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                "stripe_subscription_id": subscription_id,
                "subscription_status": "active",
                "updated_at": datetime.now().isoformat()
            })
            print(f"✅ 用户 {user_id} 订阅已创建")
            return {"status": "success", "event_type": event_type}
        
        elif event_type == "checkout.session.completed":
            # 支付成功
            session = event.get("data", {}).get("object", {})
            user_id = session.get("metadata", {}).get("user_id")
            plan_value = session.get("metadata", {}).get("plan", "normal")
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            
            print(f"🔍 checkout.session.completed - user_id: {user_id}, plan: {plan_value}, customer_id: {customer_id}, subscription_id: {subscription_id}")
            
            if not user_id:
                raise Exception("Missing user_id in session metadata")
            
            # 检查记录是否存在
            response = supabase_request("GET", "user_plans", filters={"user_id": user_id})
            print(f"🔍 当前用户记录: {response['data']}")
            
            update_data = {
                "plan": plan_value,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "subscription_status": "active",
                "updated_at": datetime.now().isoformat()
            }
            
            if response["data"]:
                # 更新现有记录
                print(f"📝 更新用户 {user_id} 的 plan 为 {plan_value}")
                result = supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", update_data)
                print(f"✅ 更新结果: {result}")
            else:
                # 创建新记录
                print(f"📝 创建新用户 {user_id} 的 plan 记录: {plan_value}")
                insert_data = {
                    "user_id": user_id,
                    "plan": plan_value,
                    "created_at": datetime.now().isoformat(),
                    **update_data
                }
                result = supabase_request("POST", "user_plans", insert_data)
                print(f"✅ 创建结果: {result}")
            
            # 验证更新是否成功
            verify_response = supabase_request("GET", "user_plans", filters={"user_id": user_id})
            if verify_response["data"]:
                current_plan = verify_response["data"][0].get("plan")
                print(f"✅ 验证: 用户 {user_id} 当前 plan 为 {current_plan}")
            
            print(f"✅ 用户 {user_id} 已升级到 {plan_value} plan")
            return {"status": "success", "event_type": event_type, "user_id": user_id, "plan": plan_value}
            
        elif event_type == "customer.subscription.updated":
            # 订阅更新
            subscription = event.get("data", {}).get("object", {})
            customer_id = subscription.get("customer")
            status = subscription.get("status")
            
            if not customer_id:
                raise Exception("Missing customer_id in subscription")
            
            # 从数据库查找用户
            response = supabase_request("GET", "user_plans", filters={"stripe_customer_id": customer_id})
            
            if not response["data"]:
                print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                return {"status": "warning", "message": "User not found"}
            
            user_id = response["data"][0]["user_id"]
            
            if status == "active":
                supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                    "subscription_status": "active",
                    "updated_at": datetime.now().isoformat()
                })
                print(f"✅ 用户 {user_id} 订阅已激活")
            elif status in ["canceled", "past_due", "unpaid"]:
                supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                    "plan": "starter",
                    "subscription_status": status,
                    "updated_at": datetime.now().isoformat()
                })
                print(f"⚠️ 用户 {user_id} 订阅已取消/逾期，降级为 starter")
            
            return {"status": "success", "event_type": event_type}
            
        elif event_type == "customer.subscription.deleted":
            # 订阅删除
            subscription = event.get("data", {}).get("object", {})
            customer_id = subscription.get("customer")
            
            if not customer_id:
                raise Exception("Missing customer_id in subscription")
            
            # 从数据库查找用户
            response = supabase_request("GET", "user_plans", filters={"stripe_customer_id": customer_id})
            
            if not response["data"]:
                print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
                return {"status": "warning", "message": "User not found"}
            
            user_id = response["data"][0]["user_id"]
            
            supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                "plan": "starter",
                "subscription_status": "canceled",
                "updated_at": datetime.now().isoformat()
            })
            print(f"⚠️ 用户 {user_id} 订阅已删除，降级为 starter")
            return {"status": "success", "event_type": event_type}
        
        return {"status": "success", "event_type": event_type, "message": "Event processed"}
    
    def _send_error(self, status_code, message):
        """发送错误响应"""
        try:
            error_body = json.dumps({"error": message}).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            print(f"Failed to send error response: {e}")
