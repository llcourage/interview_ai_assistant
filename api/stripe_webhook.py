"""
Stripe Webhook Endpoint
Uses Vercel's required format: handler class inheriting from BaseHTTPRequestHandler
"""
from http.server import BaseHTTPRequestHandler
import os
import sys
import json
import hmac
import hashlib
import time
import asyncio
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime
from pathlib import Path

# Add project root to Python path for importing backend modules
# In Vercel, the working directory is the project root, so we need to ensure backend can be imported
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class handler(BaseHTTPRequestHandler):
    """Vercel Python function entry point - must be a handler class inheriting from BaseHTTPRequestHandler"""
    
    def do_GET(self):
        """Handle GET requests (health check)"""
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
        """Handle POST requests (Stripe Webhook)"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_length)
            body_str = body_bytes.decode('utf-8')
            
            # Get webhook secret
            webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
            if not webhook_secret:
                self._send_error(500, "Webhook secret not configured")
                return
            
            # Get signature
            sig_header = self.headers.get("stripe-signature") or self.headers.get("Stripe-Signature")
            if not sig_header:
                self._send_error(400, "Missing stripe-signature header")
                return
            
            # Manually verify webhook signature
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
            
            # Check timestamp (prevent replay attacks)
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:  # 5 minutes
                self._send_error(400, "Timestamp too old")
                return
            
            # Calculate signature
            signed_payload = f"{timestamp}.{body_str}"
            expected_signature = hmac.new(
                webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            if not hmac.compare_digest(expected_signature, signature):
                self._send_error(400, "Invalid signature")
                return
            
            # Parse event
            try:
                event = json.loads(body_str)
            except json.JSONDecodeError as e:
                self._send_error(400, f"Invalid JSON: {str(e)}")
                return
            
            # Process event
            event_type = event.get("type")
            print(f"🔍 Received Stripe event: {event_type}")
            
            try:
                result = self._handle_stripe_event(event_type, event)
                print(f"✅ Event processed successfully: {event_type}")
                
                # Return success response
                response_body = json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response_body)
            except Exception as event_error:
                import traceback
                error_details = traceback.format_exc()
                error_msg = f"Failed to process event {event_type}: {type(event_error).__name__}: {str(event_error)}"
                print(f"❌ {error_msg}")
                print(error_details)
                # Still return 200, but log error (Stripe requires fast response)
                error_response = {
                    "status": "error",
                    "event_type": event_type,
                    "error": error_msg,
                    "traceback": error_details
                }
                response_body = json.dumps(error_response).encode("utf-8")
                self.send_response(200)  # Stripe requires 200 even if processing fails
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response_body)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = f"Webhook processing failed: {type(e).__name__}: {str(e)}"
            print(f"❌ {error_msg}")
            print(error_details)
            self._send_error(500, error_msg)
    
    def _handle_stripe_event(self, event_type, event):
        """Handle Stripe events"""
        try:
            print(f"🔍 Starting to process Stripe event: {event_type}")
            print(f"🔍 Event data: {json.dumps(event, indent=2)[:500]}...")  # Only print first 500 chars
            
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            if not supabase_url or not supabase_key:
                error_msg = "Supabase credentials not configured"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            def supabase_request(method, table, data=None, filters=None):
                """Call Supabase API using HTTP requests"""
                try:
                    url = f"{supabase_url}/rest/v1/{table}"
                    if filters:
                        url += "?" + "&".join([f"{k}=eq.{v}" for k, v in filters.items()])
                    
                    print(f"🔍 Supabase request: {method} {url}")
                    if data:
                        print(f"🔍 Request data: {json.dumps(data, indent=2)[:300]}...")
                    
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
                        response = urlopen(req, timeout=10)
                        result = json.loads(response.read().decode())
                        print(f"✅ Supabase response successful: {len(result) if isinstance(result, list) else 1} record(s)")
                        return {"data": result if isinstance(result, list) else [result]}
                    except HTTPError as e:
                        error_body = e.read().decode() if hasattr(e, 'read') else str(e)
                        print(f"❌ Supabase HTTP Error {e.code}: {error_body}")
                        if e.code == 404:
                            print(f"⚠️ 404 - Record not found, returning empty data")
                            return {"data": []}
                        raise Exception(f"Supabase HTTP {e.code}: {error_body}")
                    except Exception as e:
                        print(f"❌ Supabase request exception: {type(e).__name__}: {str(e)}")
                        raise
                except Exception as e:
                    import traceback
                    print(f"❌ supabase_request failed: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    raise
            
            if event_type == "customer.subscription.created":
                try:
                    # Subscription created (usually triggered by checkout.session.completed, but handle for completeness)
                    # Note: This event typically arrives after checkout.session.completed, which already handles
                    # plan updates, next_update_at, etc. This handler only updates subscription_id and status
                    # to ensure they're set, without affecting other fields.
                    subscription = event.get("data", {}).get("object", {})
                    customer_id = subscription.get("customer")
                    subscription_id = subscription.get("id")
                    
                    print(f"🔍 customer.subscription.created - customer_id: {customer_id}, subscription_id: {subscription_id}")
                    
                    if not customer_id:
                        raise Exception("Missing customer_id in subscription")
                    
                    # Find user from database
                    response = supabase_request("GET", "user_plans", filters={"stripe_customer_id": customer_id})
                    
                    if not response["data"]:
                        # If user record doesn't exist, subscription might be created through other means, log but don't process
                        print(f"⚠️ Subscription created but user not found: customer_id={customer_id}")
                        return {"status": "warning", "message": "User not found for subscription creation"}
                    
                    user_id = response["data"][0]["user_id"]
                    
                    # Update subscription ID and status only (safe to do directly as it doesn't affect plan/next_update_at)
                    # This is a minimal update that complements checkout.session.completed, not a replacement
                    supabase_request("PATCH", f"user_plans?user_id=eq.{user_id}", {
                        "stripe_subscription_id": subscription_id,
                        "subscription_status": "active",
                        "updated_at": datetime.now().isoformat()
                    })
                    print(f"✅ User {user_id} subscription created")
                    return {"status": "success", "event_type": event_type}
                except Exception as e:
                    import traceback
                    print(f"❌ Failed to process customer.subscription.created: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    raise
            
            elif event_type == "checkout.session.completed":
                try:
                    # Payment successful - use backend/payment_stripe.py handler for consistency
                    session = event.get("data", {}).get("object", {})
                    user_id = session.get("metadata", {}).get("user_id")
                    plan_value = session.get("metadata", {}).get("plan", "normal")
                    subscription_id = session.get("subscription")
                    customer_id = session.get("customer")
                    
                    print(f"🔍 checkout.session.completed - user_id: {user_id}, plan: {plan_value}, customer_id: {customer_id}, subscription_id: {subscription_id}")
                    
                    if not user_id:
                        raise Exception("Missing user_id in session metadata")
                    
                    # Import and call handle_checkout_completed from backend/payment_stripe.py
                    # This ensures we use the same logic as integration tests and properly set next_update_at
                    try:
                        from backend.payment_stripe import handle_checkout_completed
                        
                        # Run async function in sync context
                        # Check if there's a running event loop (e.g., in tests)
                        try:
                            loop = asyncio.get_running_loop()
                            # If there's a running loop, we can't use asyncio.run()
                            # Instead, create a new event loop in a new thread
                            import concurrent.futures
                            import threading
                            
                            def run_async():
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    return new_loop.run_until_complete(handle_checkout_completed(session))
                                finally:
                                    new_loop.close()
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_async)
                                future.result()  # Wait for completion
                        except RuntimeError:
                            # No running loop, safe to use asyncio.run()
                            asyncio.run(handle_checkout_completed(session))
                        
                        print(f"✅ User {user_id} upgraded to {plan_value} plan (via handle_checkout_completed)")
                        return {"status": "success", "event_type": event_type, "user_id": user_id, "plan": plan_value}
                    except ImportError as import_err:
                        # Fallback to direct database update if import fails (shouldn't happen in production)
                        print(f"⚠️ Failed to import handle_checkout_completed: {import_err}, falling back to direct update")
                        raise Exception(f"Failed to import handle_checkout_completed: {import_err}")
                except Exception as e:
                    import traceback
                    print(f"❌ Failed to process checkout.session.completed: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    raise
            
            elif event_type == "customer.subscription.updated":
                try:
                    # Subscription updated - use backend/payment_stripe.py handler for consistency
                    subscription = event.get("data", {}).get("object", {})
                    event_created = event.get("created")
                    event_id = event.get("id")
                    
                    print(f"🔍 customer.subscription.updated - subscription_id: {subscription.get('id')}, customer_id: {subscription.get('customer')}, status: {subscription.get('status')}")
                    
                    # Import and call handle_subscription_updated from backend/payment_stripe.py
                    try:
                        from backend.payment_stripe import handle_subscription_updated
                        
                        # Run async function in sync context
                        try:
                            loop = asyncio.get_running_loop()
                            import concurrent.futures
                            
                            def run_async():
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    return new_loop.run_until_complete(handle_subscription_updated(subscription, event_created, event_id))
                                finally:
                                    new_loop.close()
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_async)
                                future.result()  # Wait for completion
                        except RuntimeError:
                            # No running loop, safe to use asyncio.run()
                            asyncio.run(handle_subscription_updated(subscription, event_created, event_id))
                        
                        print(f"✅ Subscription updated processed (via handle_subscription_updated)")
                        return {"status": "success", "event_type": event_type}
                    except ImportError as import_err:
                        print(f"⚠️ Failed to import handle_subscription_updated: {import_err}")
                        raise Exception(f"Failed to import handle_subscription_updated: {import_err}")
                except Exception as e:
                    import traceback
                    print(f"❌ Failed to process customer.subscription.updated: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    raise
            
            elif event_type == "customer.subscription.deleted":
                try:
                    # Subscription deleted - use backend/payment_stripe.py handler for consistency
                    subscription = event.get("data", {}).get("object", {})
                    
                    print(f"🔍 customer.subscription.deleted - subscription_id: {subscription.get('id')}, customer_id: {subscription.get('customer')}")
                    
                    # Import and call handle_subscription_deleted from backend/payment_stripe.py
                    try:
                        from backend.payment_stripe import handle_subscription_deleted
                        
                        # Run async function in sync context
                        try:
                            loop = asyncio.get_running_loop()
                            import concurrent.futures
                            
                            def run_async():
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    return new_loop.run_until_complete(handle_subscription_deleted(subscription))
                                finally:
                                    new_loop.close()
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_async)
                                future.result()  # Wait for completion
                        except RuntimeError:
                            # No running loop, safe to use asyncio.run()
                            asyncio.run(handle_subscription_deleted(subscription))
                        
                        print(f"✅ Subscription deleted processed (via handle_subscription_deleted)")
                        return {"status": "success", "event_type": event_type}
                    except ImportError as import_err:
                        print(f"⚠️ Failed to import handle_subscription_deleted: {import_err}")
                        raise Exception(f"Failed to import handle_subscription_deleted: {import_err}")
                except Exception as e:
                    import traceback
                    print(f"❌ Failed to process customer.subscription.deleted: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    raise
        
            # Unknown event type
            print(f"⚠️ Unknown event type: {event_type}")
            return {"status": "success", "event_type": event_type, "message": "Event processed"}
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to process Stripe event: {type(e).__name__}: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            raise Exception(error_msg)
    
    def _send_error(self, status_code, message):
        """Send error response"""
        try:
            error_body = json.dumps({"error": message}).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            print(f"Failed to send error response: {e}")
