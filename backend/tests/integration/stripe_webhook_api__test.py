"""
Integration tests for api/stripe_webhook.py
Tests that the webhook API correctly calls handle_checkout_completed and sets next_update_at
"""
import pytest
import uuid
import unittest.mock
import sys
import json
import hmac
import hashlib
import time
import io
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path to import api module
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.db_supabase import get_supabase_admin
from backend.db_operations import get_user_plan
from backend.db_models import PlanType


@pytest.mark.asyncio
async def test_stripe_webhook_checkout_completed_sets_next_update_at():
    """
    Test that api/stripe_webhook.py correctly calls handle_checkout_completed
    and sets next_update_at when processing checkout.session.completed event
    
    Scenario:
    - Precondition: DB has user_plan=start
    - Trigger: POST /api/stripe_webhook with checkout.session.completed event
    - Assert: plan=normal, next_update_at is set, stripe_subscription_id set
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    session_id = f"cs_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with start plan
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "start",
            "stripe_customer_id": customer_id,
        }).execute()
        
        # Create Stripe event payload
        event = {
            "id": f"evt_test_{uuid.uuid4().hex[:8]}",
            "type": "checkout.session.completed",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": session_id,
                    "customer": customer_id,
                    "subscription": subscription_id,
                    "metadata": {
                        "user_id": user_id,
                        "plan": "normal",
                    },
                }
            }
        }
        
        # Mock Stripe subscription retrieval (no pending_update - immediate upgrade)
        mock_subscription = unittest.mock.MagicMock()
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        mock_subscription.current_period_end = int(future_date.timestamp())
        mock_subscription.pending_update = None
        mock_subscription.status = "active"
        
        # Import handler class
        from api.stripe_webhook import handler
        
        # Create handler instance
        webhook_handler = handler()
        webhook_handler.headers = {}
        webhook_handler.rfile = unittest.mock.MagicMock()
        webhook_handler.wfile = unittest.mock.MagicMock()
        webhook_handler._send_error = unittest.mock.MagicMock()
        
        # Test _handle_stripe_event method directly
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
            result = webhook_handler._handle_stripe_event("checkout.session.completed", event)
        
        # Assert: Check result
        assert result["status"] == "success", f"Expected status=success, got {result.get('status')}"
        assert result["event_type"] == "checkout.session.completed"
        assert result["user_id"] == user_id
        assert result["plan"] == "normal"
        
        # Assert: Check DB state - verify all fields are correctly updated
        user_plan = await get_user_plan(user_id)
        assert user_plan is not None, "User plan should exist"
        
        # Verify plan was upgraded
        assert user_plan.plan == PlanType.NORMAL, f"Expected plan=normal, got {user_plan.plan.value}"
        
        # Verify subscription fields
        assert user_plan.stripe_subscription_id == subscription_id, f"Expected subscription_id={subscription_id}, got {user_plan.stripe_subscription_id}"
        assert user_plan.subscription_status == "active", f"Expected status=active, got {user_plan.subscription_status}"
        
        # Verify upgrade clears scheduled changes
        assert user_plan.next_plan is None, f"Expected next_plan=None after upgrade (upgrade clears scheduled changes), got {user_plan.next_plan}"
        assert user_plan.plan_expires_at is None, f"Expected plan_expires_at=None after upgrade (upgrade clears expiration), got {user_plan.plan_expires_at}"
        
        # ✅ Key assertion: next_update_at should be set (next billing date)
        assert user_plan.next_update_at is not None, "Expected next_update_at to be set, got None"
        
        # Verify next_update_at is in the future
        from backend.utils.time import ensure_utc
        now = datetime.now(timezone.utc)
        next_update_at_dt = ensure_utc(user_plan.next_update_at)
        assert next_update_at_dt > now, f"next_update_at should be in the future, got {next_update_at_dt}, now {now}"
        
        # Verify next_update_at is approximately 30 days from now (within 1 day tolerance)
        expected_date = now + timedelta(days=30)
        time_diff = abs((next_update_at_dt - expected_date).total_seconds())
        assert time_diff < 86400, f"next_update_at should be approximately 30 days from now, got {next_update_at_dt}, expected around {expected_date}"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_stripe_webhook_checkout_completed_with_pending_update():
    """
    Test that api/stripe_webhook.py correctly handles checkout.session.completed
    when Stripe has a pending_update (delayed upgrade scenario)
    
    Scenario:
    - Precondition: DB has user_plan=normal
    - Trigger: POST /api/stripe_webhook with checkout.session.completed event
    - Stripe subscription has pending_update
    - Assert: plan=normal (not upgraded yet), next_plan=high, next_update_at set
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    session_id = f"cs_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with normal plan
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
        }).execute()
        
        # Create Stripe event payload
        event = {
            "id": f"evt_test_{uuid.uuid4().hex[:8]}",
            "type": "checkout.session.completed",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": session_id,
                    "customer": customer_id,
                    "subscription": subscription_id,
                    "metadata": {
                        "user_id": user_id,
                        "plan": "high",
                    },
                }
            }
        }
        
        # Mock Stripe subscription retrieval (with pending_update - delayed upgrade)
        mock_subscription = unittest.mock.MagicMock()
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        mock_subscription.current_period_end = int(future_date.timestamp())
        mock_subscription.status = "active"
        
        # Mock pending_update
        mock_pending_update = unittest.mock.MagicMock()
        effective_at = datetime.now(timezone.utc) + timedelta(days=7)
        mock_pending_update.effective_at = int(effective_at.timestamp())
        mock_pending_update.expires_at = None
        mock_pending_update.subscription_items = unittest.mock.MagicMock()
        mock_pending_update.subscription_items.data = [
            unittest.mock.MagicMock(
                price=unittest.mock.MagicMock(id="price_high_test")
            )
        ]
        mock_subscription.pending_update = mock_pending_update
        
        # Mock STRIPE_PRICE_IDS to match
        with unittest.mock.patch('backend.payment_stripe.STRIPE_PRICE_IDS', {PlanType.HIGH: "price_high_test"}):
            # Import handler class
            from api.stripe_webhook import handler
            
            # Create handler instance
            webhook_handler = handler()
            webhook_handler.headers = {}
            webhook_handler.rfile = unittest.mock.MagicMock()
            webhook_handler.wfile = unittest.mock.MagicMock()
            webhook_handler._send_error = unittest.mock.MagicMock()
            
            # Test _handle_stripe_event method directly
            with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
                result = webhook_handler._handle_stripe_event("checkout.session.completed", event)
            
            # Assert: Check result
            assert result["status"] == "success", f"Expected status=success, got {result.get('status')}"
            
            # Assert: Check DB state - verify delayed upgrade
            user_plan = await get_user_plan(user_id)
            assert user_plan is not None, "User plan should exist"
            assert user_plan.plan == PlanType.NORMAL, f"Expected plan=normal (not upgraded yet), got {user_plan.plan.value}"
            assert user_plan.next_plan == PlanType.HIGH, f"Expected next_plan=high, got {user_plan.next_plan}"
            
            # ✅ Key assertion: next_update_at should be set to pending_update.effective_at
            assert user_plan.next_update_at is not None, "Expected next_update_at to be set, got None"
            
            # Verify next_update_at matches pending_update.effective_at (within 1 second tolerance)
            from backend.utils.time import ensure_utc
            next_update_at_dt = ensure_utc(user_plan.next_update_at)
            expected_dt = ensure_utc(effective_at)
            time_diff = abs((next_update_at_dt - expected_dt).total_seconds())
            assert time_diff < 1, f"next_update_at should match pending_update.effective_at, got {next_update_at_dt}, expected {expected_dt}"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_stripe_webhook_api_full_post_request():
    """
    Test the complete HTTP POST request flow to /api/stripe_webhook endpoint
    This tests the full API initiation including signature verification and do_POST method
    
    Scenario:
    - Precondition: DB has user_plan=start
    - Trigger: Full HTTP POST request with checkout.session.completed event (with valid signature)
    - Assert: HTTP 200 response, plan=normal, next_update_at is set
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    session_id = f"cs_test_{uuid.uuid4().hex[:8]}"
    webhook_secret = "whsec_test_secret_key_for_testing"
    
    try:
        # Setup: Create user with start plan
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "start",
            "stripe_customer_id": customer_id,
        }).execute()
        
        # Create Stripe event payload
        event = {
            "id": f"evt_test_{uuid.uuid4().hex[:8]}",
            "type": "checkout.session.completed",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": session_id,
                    "customer": customer_id,
                    "subscription": subscription_id,
                    "metadata": {
                        "user_id": user_id,
                        "plan": "normal",
                    },
                }
            }
        }
        
        # Create request body
        body_str = json.dumps(event)
        body_bytes = body_str.encode("utf-8")
        
        # Generate valid Stripe webhook signature
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{body_str}"
        signature = hmac.new(
            webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        sig_header = f"t={timestamp},v1={signature}"
        
        # Mock Stripe subscription retrieval (no pending_update - immediate upgrade)
        mock_subscription = unittest.mock.MagicMock()
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        mock_subscription.current_period_end = int(future_date.timestamp())
        mock_subscription.pending_update = None
        mock_subscription.status = "active"
        
        # Import handler class
        from api.stripe_webhook import handler
        from email.message import Message
        
        # Create handler instance
        class TestHandler(handler):
            def __init__(self):
                pass
        
        webhook_handler = TestHandler()
        webhook_handler.command = "POST"
        webhook_handler.path = "/api/stripe_webhook"
        webhook_handler.request_version = "HTTP/1.1"
        webhook_handler.close_connection = True
        
        # Mock request headers
        headers = Message()
        headers["stripe-signature"] = sig_header
        headers["content-type"] = "application/json"
        headers["Content-Length"] = str(len(body_bytes))
        webhook_handler.headers = headers
        
        # Mock request body (rfile)
        webhook_handler.rfile = io.BytesIO(body_bytes)
        
        # Mock response (wfile) to capture response
        response_buffer = io.BytesIO()
        webhook_handler.wfile = response_buffer
        
        # Mock send_response, send_header, end_headers methods
        webhook_handler.response_code = None
        webhook_handler.response_headers = {}
        
        def mock_send_response(code):
            webhook_handler.response_code = code
        
        def mock_send_header(key, value):
            webhook_handler.response_headers[key] = value
        
        def mock_end_headers():
            pass
        
        webhook_handler.send_response = mock_send_response
        webhook_handler.send_header = mock_send_header
        webhook_handler.end_headers = mock_end_headers
        
        # Mock _send_error to avoid actual error responses
        webhook_handler._send_error = unittest.mock.MagicMock()
        
        # Set environment variable for webhook secret
        import os
        original_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        os.environ["STRIPE_WEBHOOK_SECRET"] = webhook_secret
        
        try:
            # Test do_POST method with mocked Stripe subscription retrieval
            with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
                webhook_handler.do_POST()
            
            # Assert: Check HTTP response
            assert webhook_handler.response_code == 200, f"Expected HTTP 200, got {webhook_handler.response_code}"
            
            # Parse response body
            response_buffer.seek(0)
            response_body = response_buffer.read().decode("utf-8")
            response_data = json.loads(response_body)
            
            assert response_data["status"] == "success", f"Expected status=success, got {response_data.get('status')}"
            assert response_data["event_type"] == "checkout.session.completed"
            assert response_data["user_id"] == user_id
            assert response_data["plan"] == "normal"
            
            # Assert: Check DB state - verify all fields are correctly updated
            user_plan = await get_user_plan(user_id)
            assert user_plan is not None, "User plan should exist"
            
            # Verify plan was upgraded
            assert user_plan.plan == PlanType.NORMAL, f"Expected plan=normal, got {user_plan.plan.value}"
            
            # Verify subscription fields
            assert user_plan.stripe_subscription_id == subscription_id, f"Expected subscription_id={subscription_id}, got {user_plan.stripe_subscription_id}"
            assert user_plan.subscription_status == "active", f"Expected status=active, got {user_plan.subscription_status}"
            
            # Verify upgrade clears scheduled changes
            assert user_plan.next_plan is None, f"Expected next_plan=None after upgrade (upgrade clears scheduled changes), got {user_plan.next_plan}"
            assert user_plan.plan_expires_at is None, f"Expected plan_expires_at=None after upgrade (upgrade clears expiration), got {user_plan.plan_expires_at}"
            
            # ✅ Key assertion: next_update_at should be set (next billing date)
            assert user_plan.next_update_at is not None, "Expected next_update_at to be set, got None"
            
            # Verify next_update_at is in the future
            from backend.utils.time import ensure_utc
            now = datetime.now(timezone.utc)
            next_update_at_dt = ensure_utc(user_plan.next_update_at)
            assert next_update_at_dt > now, f"next_update_at should be in the future, got {next_update_at_dt}, now {now}"
            
            # Verify next_update_at is approximately 30 days from now (within 1 day tolerance)
            expected_date = now + timedelta(days=30)
            time_diff = abs((next_update_at_dt - expected_date).total_seconds())
            assert time_diff < 86400, f"next_update_at should be approximately 30 days from now, got {next_update_at_dt}, expected around {expected_date}"
            
        finally:
            # Restore original webhook secret
            if original_secret is not None:
                os.environ["STRIPE_WEBHOOK_SECRET"] = original_secret
            elif "STRIPE_WEBHOOK_SECRET" in os.environ:
                del os.environ["STRIPE_WEBHOOK_SECRET"]
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_stripe_webhook_subscription_updated():
    """
    Test that api/stripe_webhook.py correctly calls handle_subscription_updated
    when processing customer.subscription.updated event
    
    Scenario:
    - Precondition: DB has user_plan=normal with active subscription
    - Trigger: POST /api/stripe_webhook with customer.subscription.updated event
    - Assert: subscription_status updated, next_update_at synced from Stripe
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    webhook_secret = "whsec_test_secret_key_for_testing"
    
    try:
        # Setup: Create user with normal plan and active subscription
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
        }).execute()
        
        # Create Stripe event payload
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        event = {
            "id": f"evt_test_{uuid.uuid4().hex[:8]}",
            "type": "customer.subscription.updated",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": subscription_id,
                    "customer": customer_id,
                    "status": "active",
                    "current_period_end": int(future_date.timestamp()),
                    "cancel_at_period_end": False,
                }
            }
        }
        
        # Create request body
        body_str = json.dumps(event)
        body_bytes = body_str.encode("utf-8")
        
        # Generate valid Stripe webhook signature
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{body_str}"
        signature = hmac.new(
            webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        sig_header = f"t={timestamp},v1={signature}"
        
        # Import handler class
        from api.stripe_webhook import handler
        from email.message import Message
        
        # Create handler instance
        class TestHandler(handler):
            def __init__(self):
                pass
        
        webhook_handler = TestHandler()
        webhook_handler.command = "POST"
        webhook_handler.path = "/api/stripe_webhook"
        webhook_handler.request_version = "HTTP/1.1"
        webhook_handler.close_connection = True
        
        # Mock request headers
        headers = Message()
        headers["stripe-signature"] = sig_header
        headers["content-type"] = "application/json"
        headers["Content-Length"] = str(len(body_bytes))
        webhook_handler.headers = headers
        
        # Mock request body
        webhook_handler.rfile = io.BytesIO(body_bytes)
        
        # Mock response
        response_buffer = io.BytesIO()
        webhook_handler.wfile = response_buffer
        
        # Mock HTTP methods
        webhook_handler.response_code = None
        webhook_handler.response_headers = {}
        
        def mock_send_response(code):
            webhook_handler.response_code = code
        
        def mock_send_header(key, value):
            webhook_handler.response_headers[key] = value
        
        def mock_end_headers():
            pass
        
        webhook_handler.send_response = mock_send_response
        webhook_handler.send_header = mock_send_header
        webhook_handler.end_headers = mock_end_headers
        webhook_handler._send_error = unittest.mock.MagicMock()
        
        # Set environment variable for webhook secret
        import os
        original_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        os.environ["STRIPE_WEBHOOK_SECRET"] = webhook_secret
        
        try:
            # Test do_POST method
            webhook_handler.do_POST()
            
            # Assert: Check HTTP response
            assert webhook_handler.response_code == 200, f"Expected HTTP 200, got {webhook_handler.response_code}"
            
            # Parse response body
            response_buffer.seek(0)
            response_body = response_buffer.read().decode("utf-8")
            response_data = json.loads(response_body)
            
            assert response_data["status"] == "success", f"Expected status=success, got {response_data.get('status')}"
            assert response_data["event_type"] == "customer.subscription.updated"
            
            # Assert: Check DB state - verify subscription status and next_update_at are synced
            user_plan = await get_user_plan(user_id)
            assert user_plan is not None, "User plan should exist"
            assert user_plan.subscription_status == "active", f"Expected status=active, got {user_plan.subscription_status}"
            
            # ✅ Key assertion: next_update_at should be synced from Stripe subscription
            assert user_plan.next_update_at is not None, "Expected next_update_at to be synced from Stripe subscription"
            
            # Verify next_update_at matches subscription.current_period_end (within 1 second tolerance)
            from backend.utils.time import ensure_utc
            next_update_at_dt = ensure_utc(user_plan.next_update_at)
            expected_dt = ensure_utc(future_date)
            time_diff = abs((next_update_at_dt - expected_dt).total_seconds())
            assert time_diff < 1, f"next_update_at should match subscription.current_period_end, got {next_update_at_dt}, expected {expected_dt}"
            
        finally:
            # Restore original webhook secret
            if original_secret is not None:
                os.environ["STRIPE_WEBHOOK_SECRET"] = original_secret
            elif "STRIPE_WEBHOOK_SECRET" in os.environ:
                del os.environ["STRIPE_WEBHOOK_SECRET"]
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_stripe_webhook_subscription_deleted():
    """
    Test that api/stripe_webhook.py correctly calls handle_subscription_deleted
    when processing customer.subscription.deleted event
    
    Scenario:
    - Precondition: DB has user_plan=normal with active subscription
    - Trigger: POST /api/stripe_webhook with customer.subscription.deleted event
    - Assert: plan downgraded to start, subscription_status=canceled, all schedules cleared
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    webhook_secret = "whsec_test_secret_key_for_testing"
    
    try:
        # Setup: Create user with normal plan and active subscription
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
        }).execute()
        
        # Create Stripe event payload
        event = {
            "id": f"evt_test_{uuid.uuid4().hex[:8]}",
            "type": "customer.subscription.deleted",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": subscription_id,
                    "customer": customer_id,
                }
            }
        }
        
        # Create request body
        body_str = json.dumps(event)
        body_bytes = body_str.encode("utf-8")
        
        # Generate valid Stripe webhook signature
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{body_str}"
        signature = hmac.new(
            webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        sig_header = f"t={timestamp},v1={signature}"
        
        # Import handler class
        from api.stripe_webhook import handler
        from email.message import Message
        
        # Create handler instance
        class TestHandler(handler):
            def __init__(self):
                pass
        
        webhook_handler = TestHandler()
        webhook_handler.command = "POST"
        webhook_handler.path = "/api/stripe_webhook"
        webhook_handler.request_version = "HTTP/1.1"
        webhook_handler.close_connection = True
        
        # Mock request headers
        headers = Message()
        headers["stripe-signature"] = sig_header
        headers["content-type"] = "application/json"
        headers["Content-Length"] = str(len(body_bytes))
        webhook_handler.headers = headers
        
        # Mock request body
        webhook_handler.rfile = io.BytesIO(body_bytes)
        
        # Mock response
        response_buffer = io.BytesIO()
        webhook_handler.wfile = response_buffer
        
        # Mock HTTP methods
        webhook_handler.response_code = None
        webhook_handler.response_headers = {}
        
        def mock_send_response(code):
            webhook_handler.response_code = code
        
        def mock_send_header(key, value):
            webhook_handler.response_headers[key] = value
        
        def mock_end_headers():
            pass
        
        webhook_handler.send_response = mock_send_response
        webhook_handler.send_header = mock_send_header
        webhook_handler.end_headers = mock_end_headers
        webhook_handler._send_error = unittest.mock.MagicMock()
        
        # Set environment variable for webhook secret
        import os
        original_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        os.environ["STRIPE_WEBHOOK_SECRET"] = webhook_secret
        
        try:
            # Test do_POST method
            webhook_handler.do_POST()
            
            # Assert: Check HTTP response
            assert webhook_handler.response_code == 200, f"Expected HTTP 200, got {webhook_handler.response_code}"
            
            # Parse response body
            response_buffer.seek(0)
            response_body = response_buffer.read().decode("utf-8")
            response_data = json.loads(response_body)
            
            assert response_data["status"] == "success", f"Expected status=success, got {response_data.get('status')}"
            assert response_data["event_type"] == "customer.subscription.deleted"
            
            # Assert: Check DB state - verify plan downgraded and schedules cleared
            user_plan = await get_user_plan(user_id)
            assert user_plan is not None, "User plan should exist"
            
            # ✅ Key assertions: plan downgraded to start, status canceled, schedules cleared
            assert user_plan.plan == PlanType.START, f"Expected plan=start after deletion, got {user_plan.plan.value}"
            assert user_plan.subscription_status == "canceled", f"Expected status=canceled, got {user_plan.subscription_status}"
            assert user_plan.next_plan is None, f"Expected next_plan=None (cleared), got {user_plan.next_plan}"
            assert user_plan.plan_expires_at is None, f"Expected plan_expires_at=None (cleared), got {user_plan.plan_expires_at}"
            assert user_plan.next_update_at is None, f"Expected next_update_at=None (cleared), got {user_plan.next_update_at}"
            assert user_plan.stripe_subscription_id is None, f"Expected stripe_subscription_id=None (cleared), got {user_plan.stripe_subscription_id}"
            
        finally:
            # Restore original webhook secret
            if original_secret is not None:
                os.environ["STRIPE_WEBHOOK_SECRET"] = original_secret
            elif "STRIPE_WEBHOOK_SECRET" in os.environ:
                del os.environ["STRIPE_WEBHOOK_SECRET"]
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_stripe_webhook_subscription_created():
    """
    Test that api/stripe_webhook.py correctly handles customer.subscription.created event
    
    Scenario:
    - Precondition: DB has user_plan=normal (from checkout.session.completed)
    - Trigger: POST /api/stripe_webhook with customer.subscription.created event
    - Assert: stripe_subscription_id and subscription_status updated (minimal update)
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    webhook_secret = "whsec_test_secret_key_for_testing"
    
    try:
        # Setup: Create user with normal plan (simulating checkout.session.completed already ran)
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
            "subscription_status": "active",
            # Note: stripe_subscription_id might not be set yet (customer.subscription.created arrives after checkout)
        }).execute()
        
        # Create Stripe event payload
        event = {
            "id": f"evt_test_{uuid.uuid4().hex[:8]}",
            "type": "customer.subscription.created",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": subscription_id,
                    "customer": customer_id,
                    "status": "active",
                }
            }
        }
        
        # Create request body
        body_str = json.dumps(event)
        body_bytes = body_str.encode("utf-8")
        
        # Generate valid Stripe webhook signature
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{body_str}"
        signature = hmac.new(
            webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        sig_header = f"t={timestamp},v1={signature}"
        
        # Import handler class
        from api.stripe_webhook import handler
        from email.message import Message
        
        # Create handler instance
        class TestHandler(handler):
            def __init__(self):
                pass
        
        webhook_handler = TestHandler()
        webhook_handler.command = "POST"
        webhook_handler.path = "/api/stripe_webhook"
        webhook_handler.request_version = "HTTP/1.1"
        webhook_handler.close_connection = True
        
        # Mock request headers
        headers = Message()
        headers["stripe-signature"] = sig_header
        headers["content-type"] = "application/json"
        headers["Content-Length"] = str(len(body_bytes))
        webhook_handler.headers = headers
        
        # Mock request body
        webhook_handler.rfile = io.BytesIO(body_bytes)
        
        # Mock response
        response_buffer = io.BytesIO()
        webhook_handler.wfile = response_buffer
        
        # Mock HTTP methods
        webhook_handler.response_code = None
        webhook_handler.response_headers = {}
        
        def mock_send_response(code):
            webhook_handler.response_code = code
        
        def mock_send_header(key, value):
            webhook_handler.response_headers[key] = value
        
        def mock_end_headers():
            pass
        
        webhook_handler.send_response = mock_send_response
        webhook_handler.send_header = mock_send_header
        webhook_handler.end_headers = mock_end_headers
        webhook_handler._send_error = unittest.mock.MagicMock()
        
        # Set environment variable for webhook secret
        import os
        original_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        os.environ["STRIPE_WEBHOOK_SECRET"] = webhook_secret
        
        try:
            # Test do_POST method
            webhook_handler.do_POST()
            
            # Assert: Check HTTP response
            assert webhook_handler.response_code == 200, f"Expected HTTP 200, got {webhook_handler.response_code}"
            
            # Parse response body
            response_buffer.seek(0)
            response_body = response_buffer.read().decode("utf-8")
            response_data = json.loads(response_body)
            
            assert response_data["status"] == "success", f"Expected status=success, got {response_data.get('status')}"
            assert response_data["event_type"] == "customer.subscription.created"
            
            # Assert: Check DB state - verify subscription_id and status updated, but plan unchanged
            user_plan = await get_user_plan(user_id)
            assert user_plan is not None, "User plan should exist"
            
            # ✅ Key assertions: subscription_id and status updated, but plan and other fields unchanged
            assert user_plan.stripe_subscription_id == subscription_id, f"Expected subscription_id={subscription_id}, got {user_plan.stripe_subscription_id}"
            assert user_plan.subscription_status == "active", f"Expected status=active, got {user_plan.subscription_status}"
            
            # Verify plan and other fields are unchanged (this event doesn't modify them)
            assert user_plan.plan == PlanType.NORMAL, f"Expected plan=normal (unchanged), got {user_plan.plan.value}"
            
        finally:
            # Restore original webhook secret
            if original_secret is not None:
                os.environ["STRIPE_WEBHOOK_SECRET"] = original_secret
            elif "STRIPE_WEBHOOK_SECRET" in os.environ:
                del os.environ["STRIPE_WEBHOOK_SECRET"]
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass
