"""
Integration tests for subscription upgrade and downgrade flows
Tests the 4 core scenarios: immediate upgrade, delayed upgrade, scheduled downgrade, and deletion cleanup
"""
import pytest
import uuid
import unittest.mock
from datetime import datetime, timezone, timedelta
from backend.payment_stripe import (
    handle_checkout_completed,
    handle_subscription_pending_update_applied,
    downgrade_subscription,
    handle_subscription_deleted,
)
from backend.db_supabase import get_supabase_admin
from backend.db_operations import get_user_plan
from backend.db_models import PlanType


@pytest.mark.asyncio
async def test_immediate_upgrade_no_pending_update():
    """
    Test 1: Immediate upgrade (no pending_update)
    
    Scenario:
    - Precondition: DB has user_plan=normal
    - Trigger: checkout.session.completed with plan=high, no pending_update
    - Assert: plan=high, next_plan is null, stripe_subscription_id set, subscription_status=active
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with normal plan
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
        }).execute()
        
        # Trigger: checkout.session.completed (no pending_update - immediate upgrade)
        session = {
            "id": f"cs_test_{uuid.uuid4().hex[:8]}",
            "customer": customer_id,
            "subscription": subscription_id,
            "metadata": {
                "user_id": user_id,
                "plan": "high",
            },
        }
        
        # Mock Stripe subscription retrieval (no pending_update)
        mock_subscription = unittest.mock.MagicMock()
        mock_subscription.current_period_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        mock_subscription.pending_update = None
        mock_subscription.status = "active"  # Must be a string, not MagicMock
        
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
            await handle_checkout_completed(session)
        
        # Assert: Check DB state
        user_plan = await get_user_plan(user_id)
        assert user_plan is not None, "User plan should exist"
        assert user_plan.plan == PlanType.HIGH, f"Expected plan=high, got {user_plan.plan.value}"
        assert user_plan.next_plan is None, f"Expected next_plan=None, got {user_plan.next_plan}"
        assert user_plan.stripe_subscription_id == subscription_id, f"Expected subscription_id={subscription_id}, got {user_plan.stripe_subscription_id}"
        assert user_plan.subscription_status == "active", f"Expected status=active, got {user_plan.subscription_status}"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_delayed_upgrade_with_pending_update():
    """
    Test 2: Delayed upgrade (with pending_update)
    
    Scenario:
    - Precondition: user_plan=normal
    - Trigger 1: checkout completed but Stripe has pending_update (writes next_plan/next_update_at)
    - Trigger 2: customer.subscription.pending_update_applied
    - Assert: After trigger 1: plan=normal, next_plan=high; After trigger 2: plan=high, next_plan cleared
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with normal plan
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
        }).execute()
        
        # Trigger 1: checkout.session.completed with pending_update
        session = {
            "id": f"cs_test_{uuid.uuid4().hex[:8]}",
            "customer": customer_id,
            "subscription": subscription_id,
            "metadata": {
                "user_id": user_id,
                "plan": "high",
            },
        }
        
        # Mock Stripe subscription with pending_update
        effective_at = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        mock_pending_update = unittest.mock.MagicMock()
        mock_pending_update.effective_at = effective_at
        # Create proper structure for _extract_price_id_from_pending_update
        mock_price = unittest.mock.MagicMock()
        mock_price.id = "price_high_test"
        mock_item = unittest.mock.MagicMock()
        mock_item.price = mock_price
        mock_pending_update.items = unittest.mock.MagicMock()
        mock_pending_update.items.data = [mock_item]
        
        mock_subscription = unittest.mock.MagicMock()
        mock_subscription.current_period_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        mock_subscription.pending_update = mock_pending_update
        mock_subscription.status = "active"  # Must be a string, not MagicMock
        
        # Mock STRIPE_PRICE_IDS to return matching price_id
        import backend.payment_stripe as payment_stripe_module
        original_price_ids = payment_stripe_module.STRIPE_PRICE_IDS.copy()
        payment_stripe_module.STRIPE_PRICE_IDS[PlanType.HIGH] = "price_high_test"
        
        try:
            with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
                await handle_checkout_completed(session)
        finally:
            # Restore original
            payment_stripe_module.STRIPE_PRICE_IDS = original_price_ids
        
        # Assert: After trigger 1 - plan unchanged, next_plan set
        user_plan_after_checkout = await get_user_plan(user_id)
        assert user_plan_after_checkout.plan == PlanType.NORMAL, f"Expected plan=normal (unchanged), got {user_plan_after_checkout.plan.value}"
        assert user_plan_after_checkout.next_plan == PlanType.HIGH, f"Expected next_plan=high, got {user_plan_after_checkout.next_plan.value if user_plan_after_checkout.next_plan else None}"
        assert user_plan_after_checkout.next_update_at is not None, "Expected next_update_at to be set"
        
        # Trigger 2: pending_update_applied
        subscription = {
            "id": subscription_id,
            "customer": customer_id,
            "status": "active",
            "current_period_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
            "cancel_at_period_end": False,
        }
        
        await handle_subscription_pending_update_applied(
            subscription=subscription,
            event_created=200,
            event_id="evt_pending_applied"
        )
        
        # Assert: After trigger 2 - plan upgraded, next_plan cleared
        user_plan_after_applied = await get_user_plan(user_id)
        assert user_plan_after_applied.plan == PlanType.HIGH, f"Expected plan=high, got {user_plan_after_applied.plan.value}"
        assert user_plan_after_applied.next_plan is None, f"Expected next_plan=None (cleared), got {user_plan_after_applied.next_plan}"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_scheduled_downgrade():
    """
    Test 3: Scheduled downgrade (plan remains until period end)
    
    Scenario:
    - Precondition: user_plan=high
    - Trigger: downgrade_subscription(target=normal)
    - Assert: plan still=high, next_plan=normal, plan_expires_at set, does not downgrade immediately
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with high plan and active subscription
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "high",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
        }).execute()
        
        # Mock Stripe subscription retrieval
        mock_subscription = unittest.mock.MagicMock()
        mock_subscription.current_period_end = int(period_end.timestamp())
        mock_subscription.status = "active"
        
        # Trigger: downgrade_subscription
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
            result = await downgrade_subscription(user_id, PlanType.NORMAL)
        
        assert result is True, "downgrade_subscription should return True"
        
        # Assert: Plan unchanged, next_plan set, plan_expires_at set
        user_plan = await get_user_plan(user_id)
        assert user_plan.plan == PlanType.HIGH, f"Expected plan=high (unchanged), got {user_plan.plan.value}"
        assert user_plan.next_plan == PlanType.NORMAL, f"Expected next_plan=normal, got {user_plan.next_plan.value if user_plan.next_plan else None}"
        assert user_plan.plan_expires_at is not None, "Expected plan_expires_at to be set"
        # Verify plan_expires_at is in the future (approximately period_end)
        assert user_plan.plan_expires_at > datetime.now(timezone.utc), "plan_expires_at should be in the future"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_subscription_deleted_clears_downgrade_schedule():
    """
    Test 4: subscription.deleted clears downgrade schedule
    
    Scenario:
    - Precondition: user_plan=high, next_plan=normal, next_update_at has value
    - Trigger: customer.subscription.deleted
    - Assert: plan=START, next_plan cleared, next_update_at cleared, plan_expires_at cleared, cancel_at_period_end cleared, stripe_subscription_id cleared
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with high plan and scheduled downgrade
        # Note: plan_expires_at is set to None or past time to trigger full cleanup
        # If plan_expires_at is in the future, handle_subscription_deleted will only update status
        next_update = datetime.now(timezone.utc) + timedelta(days=7)
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "high",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
            "next_plan": "normal",
            "next_update_at": next_update.isoformat(),
            "plan_expires_at": None,  # Set to None to trigger full cleanup (not just status update)
            "cancel_at_period_end": True,
        }).execute()
        
        # Trigger: subscription.deleted
        subscription = {
            "id": subscription_id,
            "customer": customer_id,
        }
        
        await handle_subscription_deleted(subscription)
        
        # Assert: All fields cleared, plan=START
        user_plan = await get_user_plan(user_id)
        assert user_plan.plan == PlanType.START, f"Expected plan=start, got {user_plan.plan.value}"
        assert user_plan.next_plan is None, f"Expected next_plan=None (cleared), got {user_plan.next_plan}"
        assert user_plan.next_update_at is None, f"Expected next_update_at=None (cleared), got {user_plan.next_update_at}"
        assert user_plan.plan_expires_at is None, f"Expected plan_expires_at=None (cleared), got {user_plan.plan_expires_at}"
        # cancel_at_period_end is cleared to None (NULL in DB), which is falsy
        assert user_plan.cancel_at_period_end is None or user_plan.cancel_at_period_end == False, \
            f"Expected cancel_at_period_end=None or False (cleared), got {user_plan.cancel_at_period_end}"
        assert user_plan.stripe_subscription_id is None, f"Expected stripe_subscription_id=None (cleared), got {user_plan.stripe_subscription_id}"
        assert user_plan.subscription_status == "canceled", f"Expected status=canceled, got {user_plan.subscription_status}"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

