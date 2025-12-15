"""
Smoke test for Supabase integration
Tests basic database read/write operations
"""
import pytest
import uuid


def test_supabase_admin_can_write_user_plans():
    """Smoke test: Verify write and read operations on user_plans table"""
    from backend.db_supabase import get_supabase_admin

    supabase = get_supabase_admin()
    # Use UUID format for user_id (PostgreSQL UUID type)
    user_id = str(uuid.uuid4())

    # Write
    result = supabase.table("user_plans").upsert({
        "user_id": user_id,
        "plan": "start",
        "stripe_customer_id": "cus_test_1",
    }).execute()

    # Read and verify
    r = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
    
    assert r.data, "Should have data"
    assert len(r.data) > 0, "Should return at least one record"
    assert r.data[0]["stripe_customer_id"] == "cus_test_1"
    assert r.data[0]["plan"] == "start"
    
    # Cleanup test data
    supabase.table("user_plans").delete().eq("user_id", user_id).execute()


