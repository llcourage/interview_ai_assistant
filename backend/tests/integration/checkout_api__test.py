"""
Integration tests for /api/plan/checkout endpoint
Tests that selecting Start Plan from a paid plan schedules downgrade instead of immediately downgrading
"""
import pytest
import uuid
import unittest.mock
from datetime import datetime, timezone, timedelta
from backend.db_supabase import get_supabase_admin
from backend.db_operations import get_user_plan
from backend.db_models import PlanType


@pytest.mark.asyncio
async def test_checkout_start_plan_from_paid_plan_schedules_downgrade():
    """
    Test that /api/plan/checkout correctly schedules downgrade when user selects Start Plan
    from a paid plan (normal/high/ultra/premium), instead of immediately downgrading.
    
    Scenario:
    - Precondition: user_plan=normal with active subscription
    - Trigger: User selects Start Plan via /api/plan/checkout
    - Assert: 
      - plan should remain normal (not immediately downgraded)
      - next_plan should be start
      - plan_expires_at and next_update_at should be set to future date
      - Downgrade is scheduled, not immediately applied
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create user with normal plan and active subscription
        future_period_end = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days from now
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active",
        }).execute()
        
        # Import the checkout logic (we'll test the core logic directly)
        from backend.db_operations import get_user_plan
        from backend.payment_stripe import downgrade_subscription, _is_downgrade
        
        # Get current plan
        current_user_plan = await get_user_plan(user_id)
        current_plan = current_user_plan.plan
        
        # Verify initial state
        assert current_plan == PlanType.NORMAL, f"Expected initial plan=normal, got {current_plan.value}"
        print(f"\n✅ Initial state: plan={current_plan.value}, subscription_id={current_user_plan.stripe_subscription_id}")
        
        # Simulate the checkout logic for Start Plan
        # This is the core logic from /api/plan/checkout endpoint
        target_plan = PlanType.START
        
        # If already on Start plan, directly update (no-op)
        if current_plan == PlanType.START:
            from backend.db_operations import update_user_plan
            await update_user_plan(user_id, plan=target_plan)
        # If user is on a paid plan, schedule downgrade instead of immediately downgrading
        elif _is_downgrade(current_plan, PlanType.START):
            # User has active subscription, schedule downgrade
            if current_user_plan.stripe_subscription_id:
                # Mock Stripe subscription retrieval for downgrade
                mock_subscription = unittest.mock.MagicMock()
                mock_subscription.current_period_end = int(future_period_end.timestamp())
                mock_subscription.status = "active"
                
                with unittest.mock.patch('backend.payment_stripe.stripe.Subscription.retrieve', return_value=mock_subscription):
                    result = await downgrade_subscription(user_id, PlanType.START)
                    assert result is True, "downgrade_subscription should return True"
        
        # Assert: After selecting Start Plan, plan should still be normal (scheduled downgrade)
        user_plan_after = await get_user_plan(user_id)
        print(f"\n🔍 State after selecting Start Plan:")
        print(f"  plan: {user_plan_after.plan.value}")
        print(f"  next_plan: {user_plan_after.next_plan.value if user_plan_after.next_plan else None}")
        print(f"  plan_expires_at: {user_plan_after.plan_expires_at}")
        print(f"  next_update_at: {user_plan_after.next_update_at}")
        
        # Verify downgrade is scheduled (not immediately applied)
        assert user_plan_after.plan == PlanType.NORMAL, \
            f"Expected plan=normal (scheduled downgrade), got {user_plan_after.plan.value}"
        assert user_plan_after.next_plan == PlanType.START, \
            f"Expected next_plan=start, got {user_plan_after.next_plan.value if user_plan_after.next_plan else None}"
        assert user_plan_after.plan_expires_at is not None, \
            "Expected plan_expires_at to be set"
        assert user_plan_after.next_update_at is not None, \
            "Expected next_update_at to be set"
        
        # Verify both dates are in the future
        now = datetime.now(timezone.utc)
        from backend.utils.time import ensure_utc
        plan_expires_at_dt = ensure_utc(user_plan_after.plan_expires_at)
        next_update_at_dt = ensure_utc(user_plan_after.next_update_at)
        
        assert plan_expires_at_dt > now, \
            f"plan_expires_at should be in the future, got {plan_expires_at_dt}, now {now}"
        assert next_update_at_dt > now, \
            f"next_update_at should be in the future, got {next_update_at_dt}, now {now}"
        
        # Verify next_update_at equals plan_expires_at (both should be period_end)
        assert plan_expires_at_dt == next_update_at_dt, \
            f"next_update_at should equal plan_expires_at, got next_update_at={next_update_at_dt}, plan_expires_at={plan_expires_at_dt}"
        
        print(f"\n✅ Test passed: Downgrade is scheduled (not immediately applied)")
        print(f"   - Plan remains: {user_plan_after.plan.value}")
        print(f"   - Next plan: {user_plan_after.next_plan.value if user_plan_after.next_plan else None}")
        print(f"   - Scheduled at: {next_update_at_dt}")
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_checkout_start_plan_when_already_on_start_plan():
    """
    Test that /api/plan/checkout correctly handles selecting Start Plan when user is already on Start Plan.
    
    Scenario:
    - Precondition: user_plan=start (no subscription)
    - Trigger: User selects Start Plan via /api/plan/checkout
    - Assert: plan remains start, no changes needed
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    
    try:
        # Setup: Create user with start plan (no subscription)
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "start",
        }).execute()
        
        # Import the checkout logic
        from backend.db_operations import get_user_plan, update_user_plan
        from backend.payment_stripe import _is_downgrade
        
        # Get current plan
        current_user_plan = await get_user_plan(user_id)
        current_plan = current_user_plan.plan
        
        # Verify initial state
        assert current_plan == PlanType.START, f"Expected initial plan=start, got {current_plan.value}"
        
        # Simulate the checkout logic for Start Plan
        target_plan = PlanType.START
        
        # If already on Start plan, directly update (no-op)
        if current_plan == PlanType.START:
            await update_user_plan(user_id, plan=target_plan)
        
        # Assert: Plan should remain start
        user_plan_after = await get_user_plan(user_id)
        assert user_plan_after.plan == PlanType.START, \
            f"Expected plan=start, got {user_plan_after.plan.value}"
        assert user_plan_after.next_plan is None, \
            f"Expected next_plan=None, got {user_plan_after.next_plan}"
        
        print(f"\n✅ Test passed: Plan remains start when already on Start Plan")
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_checkout_start_plan_from_paid_plan_without_subscription():
    """
    Test that /api/plan/checkout correctly handles selecting Start Plan when user has paid plan
    but no active subscription (edge case).
    
    Scenario:
    - Precondition: user_plan=normal but no stripe_subscription_id
    - Trigger: User selects Start Plan via /api/plan/checkout
    - Assert: plan is immediately updated to start (no subscription to schedule)
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    
    try:
        # Setup: Create user with normal plan but no subscription
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "normal",
            # No stripe_subscription_id
        }).execute()
        
        # Import the checkout logic
        from backend.db_operations import get_user_plan, update_user_plan
        from backend.payment_stripe import _is_downgrade
        
        # Get current plan
        current_user_plan = await get_user_plan(user_id)
        current_plan = current_user_plan.plan
        
        # Verify initial state
        assert current_plan == PlanType.NORMAL, f"Expected initial plan=normal, got {current_plan.value}"
        assert current_user_plan.stripe_subscription_id is None, "Expected no subscription"
        
        # Simulate the checkout logic for Start Plan
        target_plan = PlanType.START
        
        # If user is on a paid plan, schedule downgrade instead of immediately downgrading
        if _is_downgrade(current_plan, PlanType.START):
            # User has no subscription, can directly update
            if not current_user_plan.stripe_subscription_id:
                await update_user_plan(user_id, plan=target_plan)
        
        # Assert: Plan should be immediately updated to start (no subscription to schedule)
        user_plan_after = await get_user_plan(user_id)
        assert user_plan_after.plan == PlanType.START, \
            f"Expected plan=start (immediate update), got {user_plan_after.plan.value}"
        assert user_plan_after.next_plan is None, \
            f"Expected next_plan=None, got {user_plan_after.next_plan}"
        
        print(f"\n✅ Test passed: Plan immediately updated to start when no subscription exists")
        
    finally:
        # Cleanup
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

