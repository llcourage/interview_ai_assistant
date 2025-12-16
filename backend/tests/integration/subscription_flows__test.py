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


@pytest.mark.asyncio
async def test_downgrade_immediate_application_bug():
    """
    Test: Reproduce the bug where downgrade from normal to start is applied immediately
    
    Bug scenario:
    - User downgrades from normal to start
    - downgrade_subscription sets next_plan=start and plan_expires_at=future_time
    - BUT it does NOT set next_update_at
    - When get_user_plan is called, if next_update_at is NULL, it falls back to plan_expires_at
    - If plan_expires_at is NULL or has some issue, the downgrade might be applied immediately
    
    Expected behavior:
    - plan should remain normal
    - next_plan should be start
    - plan_expires_at should be set to future time
    - next_update_at should be set (but currently it's not, which is the bug)
    - The downgrade should NOT be applied immediately
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with normal plan and active subscription
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
        }).execute()
        
        # Mock Stripe subscription retrieval
        mock_subscription = unittest.mock.MagicMock()
        mock_subscription.current_period_end = int(period_end.timestamp())
        mock_subscription.status = "active"
        
        # Trigger: downgrade_subscription from normal to start
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
            result = await downgrade_subscription(user_id, PlanType.START)
        
        assert result is True, "downgrade_subscription should return True"
        
        # Check raw DB state after downgrade_subscription
        # This is BEFORE calling get_user_plan (which might trigger immediate application)
        raw_response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
        raw_data = raw_response.data[0]
        
        print(f"\n🔍 Raw DB state after downgrade_subscription:")
        print(f"  plan: {raw_data.get('plan')}")
        print(f"  next_plan: {raw_data.get('next_plan')}")
        print(f"  plan_expires_at: {raw_data.get('plan_expires_at')}")
        print(f"  next_update_at: {raw_data.get('next_update_at')}")
        
        # Assert: Raw DB should have next_plan set, but plan should still be normal
        assert raw_data.get("plan") == "normal", f"Expected plan=normal in DB, got {raw_data.get('plan')}"
        assert raw_data.get("next_plan") == "start", f"Expected next_plan=start in DB, got {raw_data.get('next_plan')}"
        assert raw_data.get("plan_expires_at") is not None, "Expected plan_expires_at to be set in DB"
        
        # BUG: next_update_at is NOT set by downgrade_subscription
        # This is the root cause - get_user_plan will fall back to plan_expires_at
        next_update_at_raw = raw_data.get("next_update_at")
        print(f"  ⚠️ next_update_at in DB: {next_update_at_raw} (should be set but currently NULL)")
        
        # Now call get_user_plan - this is where the bug might manifest
        # If next_update_at is NULL and plan_expires_at has issues, it might apply immediately
        user_plan = await get_user_plan(user_id)
        
        print(f"\n🔍 State after get_user_plan:")
        print(f"  plan: {user_plan.plan.value}")
        print(f"  next_plan: {user_plan.next_plan.value if user_plan.next_plan else None}")
        print(f"  plan_expires_at: {user_plan.plan_expires_at}")
        print(f"  next_update_at: {user_plan.next_update_at}")
        
        # Verify the fix: next_update_at is now set (bug is fixed)
        assert next_update_at_raw is not None, "FIX VERIFIED: next_update_at should now be set by downgrade_subscription"
        assert next_update_at_raw == raw_data.get("plan_expires_at"), \
            "next_update_at should equal plan_expires_at"
        
        # Verify that the downgrade is scheduled correctly (not immediately applied)
        assert user_plan.plan == PlanType.NORMAL, \
            f"Expected plan=normal (scheduled), got {user_plan.plan.value}"
        assert user_plan.next_plan == PlanType.START, \
            f"Expected next_plan=start, got {user_plan.next_plan.value if user_plan.next_plan else None}"
        assert user_plan.next_update_at is not None, "Expected next_update_at to be set"
        assert user_plan.next_update_at > datetime.now(timezone.utc), \
            "next_update_at should be in the future"
        
        # Test that even if plan_expires_at is set to past time, 
        # get_user_plan will use next_update_at (which is future) and NOT apply immediately
        past_time = datetime.now(timezone.utc) - timedelta(days=1)
        supabase.table("user_plans").update({
            "plan_expires_at": past_time.isoformat(),
            "next_plan": "start",  # Make sure next_plan is still set
            "next_update_at": next_update_at_raw  # Keep next_update_at as future time
        }).eq("user_id", user_id).execute()
        
        # Now call get_user_plan - this should NOT trigger immediate application
        # because next_update_at (future) takes priority over plan_expires_at (past)
        user_plan_after_past = await get_user_plan(user_id)
        
        print(f"\n🔍 State after setting plan_expires_at to past time (but next_update_at is future):")
        print(f"  plan: {user_plan_after_past.plan.value}")
        print(f"  next_plan: {user_plan_after_past.next_plan.value if user_plan_after_past.next_plan else None}")
        print(f"  plan_expires_at: {user_plan_after_past.plan_expires_at}")
        print(f"  next_update_at: {user_plan_after_past.next_update_at}")
        
        # FIX VERIFIED: Even with plan_expires_at in the past, 
        # get_user_plan uses next_update_at (future) as effective_at,
        # so the downgrade is NOT applied immediately
        assert user_plan_after_past.plan == PlanType.NORMAL, \
            f"✅ FIX VERIFIED: Expected plan=normal (scheduled), got {user_plan_after_past.plan.value}. " \
            f"Even with plan_expires_at in the past, next_update_at (future) prevents immediate application."
        
        assert user_plan_after_past.next_plan == PlanType.START, \
            f"Expected next_plan=start, got {user_plan_after_past.next_plan.value if user_plan_after_past.next_plan else None}"
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_downgrade_rejects_past_period_end():
    """
    Test: Verify that downgrade_subscription rejects past current_period_end from Stripe
    
    After fix:
    - When Stripe subscription current_period_end is in the past (expired subscription)
    - downgrade_subscription should raise ValueError instead of scheduling with past time
    - This prevents immediate downgrade application when next_update_at is NULL
    
    This test verifies the fix for the production bug.
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with normal plan and active subscription
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
        }).execute()
        
        # Simulate production scenario: Stripe subscription has expired (current_period_end is in the past)
        # This happens when subscription expires or is canceled but still exists in Stripe
        past_period_end = datetime.now(timezone.utc) - timedelta(days=1)  # 1 day ago
        
        # Mock Stripe subscription retrieval - return expired subscription
        mock_subscription = unittest.mock.MagicMock()
        mock_subscription.current_period_end = int(past_period_end.timestamp())
        mock_subscription.status = "active"  # Still active in Stripe, but period has ended
        
        # Trigger: downgrade_subscription from normal to start
        # After fix: This should raise ValueError instead of scheduling with past time
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
            with unittest.mock.patch('backend.payment_stripe.STRIPE_PRICE_IDS', {PlanType.NORMAL: "price_normal_test"}):
                with pytest.raises(ValueError) as exc_info:
                    await downgrade_subscription(user_id, PlanType.START)
        
        # Verify the error message indicates the problem
        error_message = str(exc_info.value)
        assert "current_period_end" in error_message.lower() or "past" in error_message.lower(), \
            f"Expected error message about past current_period_end, got: {error_message}"
        
        print(f"\n✅ FIX VERIFIED: downgrade_subscription correctly rejects past current_period_end")
        print(f"   Error message: {error_message}")
        
        # Verify database state was NOT changed (downgrade was not scheduled)
        raw_response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
        raw_data = raw_response.data[0]
        
        assert raw_data.get("plan") == "normal", "plan should remain normal (downgrade was rejected)"
        assert raw_data.get("next_plan") is None, "next_plan should be None (downgrade was rejected)"
        assert raw_data.get("plan_expires_at") is None, "plan_expires_at should be None (downgrade was rejected)"
        
        print(f"   Database state unchanged: plan={raw_data.get('plan')}, next_plan={raw_data.get('next_plan')}")
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_upgrade_from_start_to_normal_then_downgrade():
    """
    Test: Complete flow from start -> normal (upgrade) -> start (downgrade)
    
    Scenario:
    - Precondition: user_plan=start (free plan)
    - Step 1: checkout.session.completed with plan=normal (upgrade)
    - Step 2: downgrade_subscription from normal to start
    - Assert: 
      - After upgrade: plan=normal, next_plan=None, subscription is active
      - After downgrade: plan=normal, next_plan=start, plan_expires_at and next_update_at set to future
      - get_user_plan should show scheduled downgrade (not immediately applied)
    
    This test verifies the complete upgrade-downgrade flow matches integration test behavior.
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with start plan (free plan)
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "start",
            "stripe_customer_id": customer_id,
        }).execute()
        
        # Verify initial state
        initial_plan = await get_user_plan(user_id)
        assert initial_plan.plan == PlanType.START, f"Expected initial plan=start, got {initial_plan.plan.value}"
        print(f"\n✅ Initial state: plan={initial_plan.plan.value}")
        
        # Step 1: Upgrade from start to normal via checkout
        future_period_end = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days from now
        session = {
            "id": f"cs_test_{uuid.uuid4().hex[:8]}",
            "customer": customer_id,
            "subscription": subscription_id,
            "metadata": {
                "user_id": user_id,
                "plan": "normal",
            },
        }
        
        # Mock Stripe subscription retrieval (no pending_update - immediate upgrade)
        mock_subscription = unittest.mock.MagicMock()
        mock_subscription.current_period_end = int(future_period_end.timestamp())
        mock_subscription.pending_update = None
        mock_subscription.status = "active"
        
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
            with unittest.mock.patch('backend.payment_stripe.STRIPE_PRICE_IDS', {PlanType.NORMAL: "price_normal_test"}):
                await handle_checkout_completed(session)
        
        # Assert: After upgrade, plan should be normal
        user_plan_after_upgrade = await get_user_plan(user_id)
        print(f"\n🔍 State after upgrade (start -> normal):")
        print(f"  plan: {user_plan_after_upgrade.plan.value}")
        print(f"  next_plan: {user_plan_after_upgrade.next_plan.value if user_plan_after_upgrade.next_plan else None}")
        print(f"  stripe_subscription_id: {user_plan_after_upgrade.stripe_subscription_id}")
        print(f"  subscription_status: {user_plan_after_upgrade.subscription_status}")
        print(f"  plan_expires_at: {user_plan_after_upgrade.plan_expires_at}")
        print(f"  next_update_at: {user_plan_after_upgrade.next_update_at}")
        
        assert user_plan_after_upgrade.plan == PlanType.NORMAL, \
            f"Expected plan=normal after upgrade, got {user_plan_after_upgrade.plan.value}"
        assert user_plan_after_upgrade.next_plan is None, \
            f"Expected next_plan=None after upgrade, got {user_plan_after_upgrade.next_plan}"
        assert user_plan_after_upgrade.stripe_subscription_id == subscription_id, \
            f"Expected subscription_id={subscription_id}, got {user_plan_after_upgrade.stripe_subscription_id}"
        assert user_plan_after_upgrade.subscription_status == "active", \
            f"Expected status=active, got {user_plan_after_upgrade.subscription_status}"
        # ✅ Verify plan_expires_at is cleared (upgrade overrides expiration)
        assert user_plan_after_upgrade.plan_expires_at is None, \
            f"Expected plan_expires_at=None after upgrade (upgrade clears expiration), got {user_plan_after_upgrade.plan_expires_at}"
        # ✅ Verify next_update_at is set to next billing date
        assert user_plan_after_upgrade.next_update_at is not None, \
            "Expected next_update_at to be set (next billing date)"
        # Verify next_update_at is in the future
        from backend.utils.time import ensure_utc
        now = datetime.now(timezone.utc)
        next_update_at_dt = ensure_utc(user_plan_after_upgrade.next_update_at)
        assert next_update_at_dt > now, \
            f"next_update_at should be in the future, got {next_update_at_dt}, now {now}"
        
        # Step 2: Downgrade from normal to start
        # Mock Stripe subscription retrieval for downgrade (future period_end)
        mock_subscription_for_downgrade = unittest.mock.MagicMock()
        mock_subscription_for_downgrade.current_period_end = int(future_period_end.timestamp())
        mock_subscription_for_downgrade.status = "active"
        
        with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription_for_downgrade):
            with unittest.mock.patch('backend.payment_stripe.STRIPE_PRICE_IDS', {PlanType.NORMAL: "price_normal_test"}):
                result = await downgrade_subscription(user_id, PlanType.START)
        
        assert result is True, "downgrade_subscription should return True"
        
        # Assert: After downgrade, plan should still be normal, but next_plan should be start
        user_plan_after_downgrade = await get_user_plan(user_id)
        print(f"\n🔍 State after downgrade (normal -> start scheduled):")
        print(f"  plan: {user_plan_after_downgrade.plan.value}")
        print(f"  next_plan: {user_plan_after_downgrade.next_plan.value if user_plan_after_downgrade.next_plan else None}")
        print(f"  plan_expires_at: {user_plan_after_downgrade.plan_expires_at}")
        print(f"  next_update_at: {user_plan_after_downgrade.next_update_at}")
        print(f"  cancel_at_period_end: {user_plan_after_downgrade.cancel_at_period_end}")
        
        # Verify downgrade is scheduled (not immediately applied)
        assert user_plan_after_downgrade.plan == PlanType.NORMAL, \
            f"Expected plan=normal (scheduled downgrade), got {user_plan_after_downgrade.plan.value}"
        assert user_plan_after_downgrade.next_plan == PlanType.START, \
            f"Expected next_plan=start, got {user_plan_after_downgrade.next_plan.value if user_plan_after_downgrade.next_plan else None}"
        assert user_plan_after_downgrade.plan_expires_at is not None, \
            "Expected plan_expires_at to be set"
        assert user_plan_after_downgrade.next_update_at is not None, \
            "Expected next_update_at to be set"
        
        # Verify both dates are in the future
        now = datetime.now(timezone.utc)
        from backend.utils.time import ensure_utc
        plan_expires_at_dt = ensure_utc(user_plan_after_downgrade.plan_expires_at)
        next_update_at_dt = ensure_utc(user_plan_after_downgrade.next_update_at)
        
        assert plan_expires_at_dt > now, \
            f"plan_expires_at should be in the future, got {plan_expires_at_dt}, now {now}"
        assert next_update_at_dt > now, \
            f"next_update_at should be in the future, got {next_update_at_dt}, now {now}"
        
        # Verify next_update_at equals plan_expires_at (both should be period_end)
        assert plan_expires_at_dt == next_update_at_dt, \
            f"next_update_at should equal plan_expires_at, got next_update_at={next_update_at_dt}, plan_expires_at={plan_expires_at_dt}"
        
        print(f"\n✅ Complete flow verified:")
        print(f"   - Upgrade: start -> normal (immediate)")
        print(f"   - Downgrade: normal -> start (scheduled at {next_update_at_dt})")
        print(f"   - Downgrade is NOT immediately applied (plan still normal, next_plan=start)")
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

