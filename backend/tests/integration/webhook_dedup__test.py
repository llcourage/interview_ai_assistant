"""
Integration test for webhook event deduplication and out-of-order handling
"""
import pytest
import uuid
import asyncio
from backend.payment_stripe import handle_subscription_updated
from backend.db_supabase import get_supabase_admin
from backend.db_operations import get_user_plan


@pytest.mark.asyncio
async def test_subscription_updated_event_deduplication():
    """
    Test that older events (lower event_created timestamp) do not overwrite
    newer state in the database.
    
    Scenario:
    1. Send subscription.updated event with created=200, update status to "active"
    2. Verify stripe_event_ts=200 and status="active" in DB
    3. Send subscription.updated event with created=100 (older), try to update status to "canceled"
    4. Verify stripe_event_ts still=200 and status still="active" (not overwritten)
    """
    supabase = get_supabase_admin()
    user_id = str(uuid.uuid4())
    customer_id = f"cus_test_{uuid.uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Setup: Create initial user plan record
        supabase.table("user_plans").upsert({
            "user_id": user_id,
            "plan": "start",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "trialing",
            "stripe_event_ts": None,  # Initially no event timestamp
        }).execute()
        
        # Step 1: Send newer event (created=200) with status="active"
        subscription_newer = {
            "id": subscription_id,
            "customer": customer_id,
            "status": "active",
            "current_period_end": 1735689600,  # Some future timestamp
            "cancel_at_period_end": False,
        }
        
        await handle_subscription_updated(
            subscription=subscription_newer,
            event_created=200,
            event_id="evt_newer_200"
        )
        
        # Verify: Check DB state after newer event
        user_plan_after_newer = await get_user_plan(user_id)
        assert user_plan_after_newer is not None, "User plan should exist"
        assert user_plan_after_newer.stripe_event_ts == 200, f"Expected stripe_event_ts=200, got {user_plan_after_newer.stripe_event_ts}"
        assert user_plan_after_newer.subscription_status == "active", f"Expected status='active', got {user_plan_after_newer.subscription_status}"
        
        # Step 2: Send older event (created=100) with status="canceled"
        # This should be ignored because db_ts (200) >= event_ts (100)
        subscription_older = {
            "id": subscription_id,
            "customer": customer_id,
            "status": "canceled",  # Different status to test it doesn't overwrite
            "current_period_end": 1735689600,
            "cancel_at_period_end": True,
        }
        
        await handle_subscription_updated(
            subscription=subscription_older,
            event_created=100,  # Older timestamp
            event_id="evt_older_100"
        )
        
        # Verify: Check DB state after older event (should be unchanged)
        user_plan_after_older = await get_user_plan(user_id)
        assert user_plan_after_older is not None, "User plan should still exist"
        
        # Critical assertions: Old event should NOT overwrite newer state
        assert user_plan_after_older.stripe_event_ts == 200, \
            f"stripe_event_ts should remain 200 (not overwritten by older event 100), got {user_plan_after_older.stripe_event_ts}"
        assert user_plan_after_older.subscription_status == "active", \
            f"status should remain 'active' (not overwritten to 'canceled'), got {user_plan_after_older.subscription_status}"
        assert user_plan_after_older.cancel_at_period_end == False, \
            f"cancel_at_period_end should remain False (not overwritten by older event), got {user_plan_after_older.cancel_at_period_end}"
        
    finally:
        # Cleanup: Remove test data
        try:
            supabase.table("user_plans").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

