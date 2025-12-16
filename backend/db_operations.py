"""
Database operations
Provides CRUD operations for user Plan, API Keys, Usage
"""
import os
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta, timezone
from backend.utils.time import utcnow, ensure_utc
from backend.db_supabase import get_supabase, get_supabase_admin
from backend.db_models import UserPlan, UsageLog, UsageQuota, PlanType, PLAN_LIMITS

# Sentinel value for explicitly clearing fields in update_user_plan
# Use this instead of None when you want to clear a field (set to NULL in DB)
# None means "don't update this field", _CLEAR_FIELD means "set this field to NULL"
_CLEAR_FIELD = object()

# Import postgrest exceptions at module level to avoid UnboundLocalError
try:
    from postgrest.exceptions import APIError
except ImportError:
    # Fallback if postgrest is not available (e.g., in test environment)
    APIError = Exception

# Encryption related code removed - all users use server API Key


def normalize_plan_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compatible with old data: normalize plan/next_plan, ensure both weekly and monthly fields exist"""
    if not isinstance(data, dict):
        return data

    data = data.copy()

    # Normalize plan
    if data.get("plan") == "starter":
        data["plan"] = "start"

    # Normalize next_plan
    if data.get("next_plan") == "starter":
        data["next_plan"] = "start"

    if "next_plan" in data:
        v = data.get("next_plan")
        if v is None or v == "":
            data["next_plan"] = None
        else:
            try:
                valid_plans = {p.value for p in PlanType}
                if v not in valid_plans:
                    print(f"⚠️ Invalid next_plan value '{v}', setting to None")
                    data["next_plan"] = None
            except Exception:
                # Be conservative in unusual test envs (avoid crashing normalize)
                pass

    # Backward compatibility fields
    if "weekly_tokens_used" not in data:
        data["weekly_tokens_used"] = 0
    if "monthly_tokens_used" not in data:
        data["monthly_tokens_used"] = 0

    return data


# ========== User Plan Operations ==========

async def _fetch_user_plan_from_db(user_id: str) -> Optional[UserPlan]:
    """Internal helper to fetch user plan from DB without recursion.
    Used after applying plan changes to get updated state."""
    try:
        supabase = get_supabase_admin()
        response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()

        if response and response.data and len(response.data) > 0:
            plan_data = normalize_plan_data(response.data[0])
            return UserPlan(**plan_data)
        return None
    except Exception as e:
        print(f"⚠️ Failed to fetch user plan from DB: {e}")
        return None


async def clear_scheduled_plan_change_if_matches(
    user_id: str,
    expected_next_plan: str,
    expected_next_update_at: Optional[datetime],
) -> None:
    """Clear next_plan/next_update_at only if current DB values still match expected ones (CAS)."""
    supabase = get_supabase_admin()  # Use admin client to avoid RLS issues

    def _base_query():
        return (
            supabase
            .table("user_plans")
            .update({
                "next_plan": None,
                "next_update_at": None,
                "updated_at": utcnow().isoformat(),
            })
            .eq("user_id", user_id)
            .eq("next_plan", expected_next_plan)
        )

    # 1) Strong CAS (with next_update_at) if we have it
    if expected_next_update_at is not None:
        expected_next_update_at_utc = ensure_utc(expected_next_update_at)
        r1 = _base_query().eq("next_update_at", expected_next_update_at_utc.isoformat()).execute()
        # Check if update succeeded (has data returned)
        if r1 and hasattr(r1, "data") and r1.data:
            return  # Successfully cleared with strong CAS

    # 2) Fallback CAS (without next_update_at) to tolerate string format differences
    # This handles cases where DB format (Z) doesn't match isoformat() output (+00:00)
    _base_query().execute()


async def get_user_plan(user_id: str) -> UserPlan:
    """Get user Plan"""
    try:
        # Use admin client to ensure we can read all data (bypass RLS)
        # This is important because regular client might be blocked by RLS policies
        supabase = get_supabase_admin()
        # Use direct query (not maybe_single) to avoid 406 errors when no record exists
        # 406 happens when maybe_single() expects exactly 1 row but finds 0
        response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
        
        print(f"🔍 DEBUG get_user_plan: user_id={user_id}")
        print(f"🔍 DEBUG get_user_plan: response={response}, response type={type(response)}")
        
        # Check if response is None (shouldn't happen with direct query, but handle it)
        if response is None:
            print(f"⚠️ get_user_plan: response is None, this shouldn't happen with direct query")
            # Try to create default plan
            return await create_user_plan(user_id)
        
        print(f"🔍 DEBUG get_user_plan: response.data={response.data}, response.data type={type(response.data)}")
        
        # Check if we have data
        if response.data and len(response.data) > 0:
            print(f"🔍 DEBUG get_user_plan: Found plan record, plan={response.data[0].get('plan')}")
            plan_data = normalize_plan_data(response.data[0])
            print(f"🔍 DEBUG get_user_plan: After normalize_plan_data: {plan_data}")
            print(f"🔍 DEBUG get_user_plan: plan_data['plan']={plan_data.get('plan')}")
            
            user_plan = UserPlan(**plan_data)
            
            # Check if plan change is scheduled (next_plan) or plan has expired
            now = utcnow()

            # Priority 1: Apply scheduled plan change (next_plan)
            if user_plan.next_plan is not None:
                effective_at = None

                if user_plan.next_update_at:
                    effective_at = ensure_utc(user_plan.next_update_at)
                elif user_plan.plan_expires_at:
                    # fallback for legacy data that used plan_expires_at as trigger
                    effective_at = ensure_utc(user_plan.plan_expires_at)

                if effective_at and effective_at <= now:
                    old_next_plan = user_plan.next_plan  # PlanType
                    old_next_update_at = ensure_utc(user_plan.next_update_at) if user_plan.next_update_at else None

                    print(
                        f"⏰ User {user_id} scheduled plan change reached at {effective_at}, "
                        f"switching from '{user_plan.plan.value}' to '{old_next_plan.value}'"
                    )

                    # 1) Update plan (do NOT clear plan_expires_at here)
                    user_plan = await update_user_plan(
                        user_id=user_id,
                        plan=old_next_plan,
                    )

                    # 2) Clear schedule idempotently (CAS)
                    try:
                        await clear_scheduled_plan_change_if_matches(
                            user_id=user_id,
                            expected_next_plan=old_next_plan.value,
                            expected_next_update_at=old_next_update_at,
                        )
                    except Exception as e:
                        # Not fatal: if CAS clear fails due to race, next call will handle it
                        print(f"⚠️ Failed to clear scheduled plan change for user {user_id}: {e}")

                    # Make returned object consistent even if CAS/refresh fails
                    # Clear schedule fields in memory to avoid returning stale data
                    try:
                        user_plan.next_plan = None
                        user_plan.next_update_at = None
                    except Exception:
                        pass

                    # 3) Re-fetch from DB to ensure returned user_plan reflects cleared fields
                    # Use internal helper to avoid recursion
                    refreshed_plan = await _fetch_user_plan_from_db(user_id)
                    if refreshed_plan:
                        user_plan = refreshed_plan
                    # If fetch fails, user_plan still has the updated plan (but schedule fields are cleared in memory)

                else:
                    # Not due yet
                    if user_plan.next_update_at:
                        print(
                            f"⏰ User {user_id} has scheduled plan change to '{user_plan.next_plan.value}' "
                            f"at {ensure_utc(user_plan.next_update_at)}, keeping '{user_plan.plan.value}'"
                        )
                    elif user_plan.plan_expires_at:
                        print(
                            f"⏰ User {user_id} has scheduled plan change to '{user_plan.next_plan.value}' "
                            f"at {ensure_utc(user_plan.plan_expires_at)}, keeping '{user_plan.plan.value}'"
                        )

            # Priority 2: Backward compatibility - no next_plan but plan_expires_at elapsed -> downgrade to start
            elif user_plan.plan_expires_at and user_plan.plan != PlanType.START:
                plan_expires_at = ensure_utc(user_plan.plan_expires_at)
                if plan_expires_at and plan_expires_at <= now:
                    print(
                        f"⏰ User {user_id} plan expired at {plan_expires_at}, "
                        f"downgrading from '{user_plan.plan.value}' to 'start'"
                    )
                    user_plan = await update_user_plan(
                        user_id=user_id,
                        plan=PlanType.START,
                        plan_expires_at=_CLEAR_FIELD,  # ✅ Use sentinel to explicitly clear field
                    )
                else:
                    print(
                        f"⏰ User {user_id} plan expires at {plan_expires_at}, "
                        f"keeping '{user_plan.plan.value}'"
                    )
            
            print(f"🔍 DEBUG get_user_plan: UserPlan object created, plan={user_plan.plan}, plan type={type(user_plan.plan)}, plan value={user_plan.plan.value if hasattr(user_plan.plan, 'value') else 'N/A'}")
            return user_plan
        else:
            # No plan record found, create default START plan using admin client
            print(f"⚠️ User {user_id} has no plan record, creating default START plan")
            return await create_user_plan(user_id)
    except Exception as e:
        print(f"⚠️ Failed to get user Plan: {e}")
        import traceback
        print(f"🔍 DEBUG get_user_plan: Exception traceback:\n{traceback.format_exc()}")
        # Try to create default plan one more time
        try:
            return await create_user_plan(user_id)
        except Exception as create_error:
            print(f"❌ Failed to create user Plan: {create_error}")
            # Re-raise the exception instead of returning fake plan object
            raise Exception(f"Failed to get or create user plan for user {user_id}: {str(create_error)}")


async def create_user_plan(user_id: str, plan: PlanType = PlanType.START) -> UserPlan:
    """Create user Plan using admin client (SERVICE_ROLE_KEY) to bypass RLS
    
    Uses upsert to prevent duplicate inserts if plan already exists
    If record exists, preserves existing fields (stripe_subscription_id, etc.)
    """
    try:
        # Use admin client (SERVICE_ROLE_KEY) to bypass RLS
        supabase_admin = get_supabase_admin()
        now = utcnow()
        
        # First, try to get existing plan
        existing_response = supabase_admin.table("user_plans").select("*").eq("user_id", user_id).execute()
        existing_data = None
        if existing_response and existing_response.data and len(existing_response.data) > 0:
            existing_data = existing_response.data[0]
            print(f"🔍 DEBUG create_user_plan: Found existing plan record, returning existing plan: plan={existing_data.get('plan')}, stripe_customer_id={existing_data.get('stripe_customer_id')}, stripe_subscription_id={existing_data.get('stripe_subscription_id')}")
            # If record already exists, return it instead of overwriting
            plan_data = normalize_plan_data(existing_data)
            return UserPlan(**plan_data)
        
        # No existing record, create new one
        # Ensure plan value is normalized (convert 'starter' to 'start' if somehow present)
        plan_value = plan.value
        if plan_value == 'starter':
            plan_value = 'start'
        
        plan_data = {
            "user_id": user_id,
            "plan": plan_value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Use upsert with on_conflict to handle race conditions
        # If user_id already exists, update the plan; otherwise insert
        print(f"🔍 DEBUG create_user_plan: Creating new plan for user {user_id}, plan={plan_value}")
        response = supabase_admin.table("user_plans").upsert(
            plan_data,
            on_conflict="user_id"
        ).execute()
        
        # Defensive check: ensure response and response.data exist
        if response is None:
            print(f"❌ Supabase upsert returned None")
            raise Exception("Failed to create Plan: Database operation returned empty response")
        
        if not hasattr(response, 'data') or not response.data:
            print(f"❌ Supabase upsert returned empty response.data: {response}")
            raise Exception("Failed to create Plan: Database operation did not return data")
        
        # Ensure data is list and not empty
        if isinstance(response.data, list) and len(response.data) > 0:
            plan_data = normalize_plan_data(response.data[0])
            return UserPlan(**plan_data)
        elif not isinstance(response.data, list) and response.data:
            plan_data = normalize_plan_data(response.data)
            return UserPlan(**plan_data)
        else:
            print(f"❌ Supabase insert returned unexpected data format: {response.data}")
            raise Exception("Failed to create Plan: Returned data format incorrect")
    except Exception as e:
        print(f"❌ Failed to create user Plan: {e}")
        import traceback
        traceback.print_exc()
        raise


async def update_user_plan(
    user_id: str,
    plan: Optional[PlanType] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[Union[str, type(_CLEAR_FIELD)]] = None,
    subscription_status: Optional[Union[str, type(_CLEAR_FIELD)]] = None,
    plan_expires_at: Optional[Union[datetime, type(_CLEAR_FIELD)]] = None,
    next_update_at: Optional[Union[datetime, type(_CLEAR_FIELD)]] = None,
    next_plan: Optional[Union[PlanType, type(_CLEAR_FIELD)]] = None,
    cancel_at_period_end: Optional[Union[bool, type(_CLEAR_FIELD)]] = None,
    stripe_event_ts: Optional[int] = None  # Stripe event.created (Unix timestamp in seconds)
) -> UserPlan:
    """Update user Plan (create if record doesn't exist) - use upsert to avoid 204 error
    
    Args:
        user_id: User ID
        plan: Current plan type (PlanType enum, converted to string internally)
        stripe_customer_id: Stripe customer ID
        stripe_subscription_id: Stripe subscription ID
                             Use _CLEAR_FIELD to explicitly clear this field (set to NULL)
        subscription_status: Subscription status (active, canceled, etc.)
                             Use _CLEAR_FIELD to explicitly clear this field (set to NULL)
        plan_expires_at: When plan will expire (datetime, converted to ISO format)
                        Use _CLEAR_FIELD to explicitly clear this field (set to NULL)
        next_update_at: Next billing/renewal date (datetime, converted to ISO format)
                        Use _CLEAR_FIELD to explicitly clear this field (set to NULL)
        next_plan: Next plan to switch to (PlanType enum, converted to string internally)
                   Use _CLEAR_FIELD to explicitly clear this field (set to NULL)
        cancel_at_period_end: Whether subscription will cancel at period end (boolean)
                             Use _CLEAR_FIELD to explicitly clear this field (set to NULL)
        stripe_event_ts: Stripe event.created Unix timestamp (int) for webhook deduplication
    
    Returns:
        UserPlan: Updated user plan object
    
    Note:
        - If upgrading from start plan to other plan, will automatically reset quota
        - All plan-related parameters use PlanType enum and are converted to strings internally
        - None means "don't update this field", _CLEAR_FIELD means "set this field to NULL"
        - Only non-None values are updated (partial updates supported)
    """
    try:
        supabase = get_supabase()
        
        # If plan is to be updated, check if quota needs to be reset (upgrading from start to other plan)
        # or adjusted (downgrading to start plan)
        should_reset_quota = False
        should_adjust_quota_for_start = False
        old_plan = None
        if plan is not None:
            # Get old plan
            try:
                old_plan_response = supabase.table("user_plans").select("plan").eq("user_id", user_id).maybe_single().execute()
                if old_plan_response.data:
                    old_plan_value = old_plan_response.data.get("plan")
                    if old_plan_value:
                        # Normalize 'starter' to 'start' before converting to PlanType
                        if old_plan_value == 'starter':
                            old_plan_value = 'start'
                        old_plan = PlanType(old_plan_value)
                        # If upgrading from start plan to normal/high plan, need to reset quota
                        if old_plan == PlanType.START and plan != PlanType.START:
                            should_reset_quota = True
                            print(f"🔄 User {user_id} upgrading from start plan to {plan.value} plan, will reset quota")
                        # If downgrading to start plan, need to adjust quota (cap at lifetime limit)
                        elif old_plan != PlanType.START and plan == PlanType.START:
                            should_adjust_quota_for_start = True
                            print(f"🔄 User {user_id} downgrading to start plan, will adjust quota to lifetime limit")
            except Exception as e:
                print(f"⚠️ Failed to check old plan (may be new user): {e}")
        
        # Build data dictionary
        now = utcnow()
        data = {
            "user_id": user_id,
            "updated_at": now.isoformat()
        }
        
        # Helper function to convert PlanType to normalized string value
        def plan_type_to_string(plan_type: PlanType) -> str:
            """Convert PlanType enum to normalized string value for database storage"""
            plan_value = plan_type.value
            # Normalize 'starter' to 'start' for backward compatibility
            if plan_value == 'starter':
                plan_value = 'start'
            return plan_value
        
        # Only add non-None values to data (avoid overwriting existing values with NULL)
        # Note: If creating new record (via webhook), plan will always be passed
        # If partial update (plan is None), only update other fields
        
        # Plan field: Convert PlanType to string for database storage
        if plan is not None:
            data["plan"] = plan_type_to_string(plan)
        
        # Stripe-related fields
        if stripe_customer_id is not None:
            data["stripe_customer_id"] = stripe_customer_id
        
        # stripe_subscription_id: Support explicit clearing with _CLEAR_FIELD sentinel
        if stripe_subscription_id is _CLEAR_FIELD:
            data["stripe_subscription_id"] = None  # Explicitly clear field -> DB NULL
        elif stripe_subscription_id is not None:
            data["stripe_subscription_id"] = stripe_subscription_id  # Normal update
        # else: None means "don't update this field"
        
        # subscription_status: Support explicit clearing with _CLEAR_FIELD sentinel
        if subscription_status is _CLEAR_FIELD:
            data["subscription_status"] = None  # Explicitly clear field -> DB NULL
        elif subscription_status is not None:
            data["subscription_status"] = subscription_status  # Normal update
        # else: None means "don't update this field"
        
        # Date/time fields: Convert datetime to ISO format string (ensure UTC aware)
        # Support explicit clearing with _CLEAR_FIELD sentinel
        if plan_expires_at is _CLEAR_FIELD:
            data["plan_expires_at"] = None  # Explicitly clear field
        elif plan_expires_at is not None:
            plan_expires_at = ensure_utc(plan_expires_at)
            data["plan_expires_at"] = plan_expires_at.isoformat()
        
        # Debug: Log next_update_at value before processing
        print(f"DEBUG update_user_plan: next_update_at={next_update_at}, type={type(next_update_at)}, is _CLEAR_FIELD={next_update_at is _CLEAR_FIELD}")
        
        if next_update_at is _CLEAR_FIELD:
            data["next_update_at"] = None  # Explicitly clear field
        elif next_update_at is not None:
            next_update_at = ensure_utc(next_update_at)
            data["next_update_at"] = next_update_at.isoformat()
        
        # New fields for plan changes and webhook tracking
        # next_plan: Convert PlanType to string for database storage
        # Support explicit clearing with _CLEAR_FIELD sentinel
        if next_plan is _CLEAR_FIELD:
            data["next_plan"] = None  # Explicitly clear field
        elif next_plan is not None:
            data["next_plan"] = plan_type_to_string(next_plan)
        
        # cancel_at_period_end: Boolean flag indicating if subscription will cancel at period end
        # Support explicit clearing with _CLEAR_FIELD sentinel
        if cancel_at_period_end is _CLEAR_FIELD:
            data["cancel_at_period_end"] = None  # Explicitly clear field
        elif cancel_at_period_end is not None:
            data["cancel_at_period_end"] = cancel_at_period_end
        
        # stripe_event_ts: Unix timestamp (int) from Stripe event.created for webhook deduplication
        if stripe_event_ts is not None:
            data["stripe_event_ts"] = stripe_event_ts
        
        # Before upsert, ALWAYS check if existing record has 'starter' value and fix it
        # This is critical because if plan is None (partial update), data won't include plan field
        # and the 'starter' value would remain in database, causing constraint violations
        existing_plan_value = None
        try:
            existing_response = supabase.table("user_plans").select("plan").eq("user_id", user_id).maybe_single().execute()
            if existing_response.data:
                existing_plan_value = existing_response.data.get("plan")
                if existing_plan_value == 'starter':
                    # Fix existing 'starter' value to 'start' before upsert
                    # This must be done BEFORE upsert to avoid constraint violations
                    # Add condition to only update if plan is still 'starter' (prevent race condition)
                    fix_response = supabase.table("user_plans").update({"plan": "start"}).eq("user_id", user_id).eq("plan", "starter").execute()
                    if fix_response.data:
                        print(f"✅ Fixed existing 'starter' plan value for user {user_id}")
                        existing_plan_value = 'start'  # Update local variable
                    else:
                        print(f"⚠️ Fix update returned no data for user {user_id}")
        except Exception as fix_error:
            # If fix fails, log error but continue with upsert
            # If this is a new user, the fix will fail (no record exists), which is OK
            print(f"⚠️ Could not fix existing plan (may be new user): {fix_error}")
            import traceback
            traceback.print_exc()
        
        # CRITICAL FIX: If plan is None (partial update), we must include 'plan' in data
        # to prevent database from using default value 'starter' (which violates constraint)
        # This is especially important for new users (no existing record)
        # Only add plan for new users (when no existing record), not for partial updates
        if plan is None and 'plan' not in data:
            # Only set plan to 'start' if this is a new user (no existing record)
            # For existing users, we don't want to overwrite their current plan
            if existing_plan_value is None:
                # New user: set plan to 'start' to prevent database default 'starter'
                print(f"⚠️ Plan is None and no existing record, adding 'plan': 'start' to data to prevent database default 'starter'")
                data["plan"] = "start"
            # If existing_plan_value exists, don't add plan to data (partial update)
        
        # Use upsert, with user_id as unique key
        # Insert if record doesn't exist, update if exists
        try:
            # Log data being upserted for debugging
            print(f"🔄 Upserting user_plans for user {user_id}: {data}")
            
            # Try standard upsert
            response = supabase.table("user_plans").upsert(data).execute()
            
        except Exception as upsert_error:
            # Log detailed error information
            error_msg = str(upsert_error)
            print(f"❌ Standard upsert failed: {error_msg}")
            print(f"   Data being upserted: {data}")
            
            # Check if error is related to 'starter' plan value
            if "'starter'" in error_msg or '"starter"' in error_msg:
                print(f"⚠️ Error contains 'starter' value - attempting to fix database before retry")
                # Try to fix all 'starter' values in database for this user
                try:
                    fix_response = supabase.table("user_plans").update({"plan": "start"}).eq("user_id", user_id).eq("plan", "starter").execute()
                    print(f"✅ Fixed 'starter' values: {fix_response.data}")
                except Exception as fix_err:
                    print(f"⚠️ Could not fix 'starter' values: {fix_err}")
            
            # If standard upsert fails, try specifying on_conflict
            try:
                print(f"🔄 Retrying upsert with on_conflict='user_id'")
                response = supabase.table("user_plans").upsert(
                    data,
                    on_conflict="user_id"
                ).execute()
            except Exception as e2:
                print(f"❌ Retry upsert also failed: {e2}")
                import traceback
                traceback.print_exc()
                raise
        
        # Defensive check: ensure response and response.data exist
        if response is None:
            print(f"Supabase upsert returned None")
            raise Exception("Update plan failed: Database operation returned empty response")
        
        if not hasattr(response, 'data') or not response.data:
            print(f"Supabase upsert returned empty response.data: {response}")
            raise Exception("Update plan failed: Database operation did not return data")
        
        # Process returned data
        if isinstance(response.data, list) and len(response.data) > 0:
            plan_data = normalize_plan_data(response.data[0])
            result = UserPlan(**plan_data)
        elif not isinstance(response.data, list) and response.data:
            plan_data = normalize_plan_data(response.data)
            result = UserPlan(**plan_data)
        else:
            raise Exception("Update plan failed: Unexpected response format")
        
        # If need to reset quota (upgrading from start to other plan)
        if should_reset_quota and plan is not None:
            try:
                now = utcnow()
                quota_update_data = {
                    "weekly_tokens_used": 0,
                    "quota_reset_date": now.isoformat(),
                    "plan": plan.value,  # Also update plan in quota
                    "updated_at": now.isoformat()
                }
                quota_response = supabase.table("usage_quotas").update(quota_update_data).eq("user_id", user_id).execute()
                if quota_response.data:
                    print(f"✅ Reset user {user_id} quota (upgraded from start plan to {plan.value})")
                else:
                    # Quota record may not exist, try to create
                    try:
                        await create_user_quota(user_id)
                        print(f"✅ Created new quota record for user {user_id}")
                    except Exception as create_error:
                        print(f"⚠️ Failed to create quota record: {create_error}")
            except Exception as quota_error:
                print(f"⚠️ Error resetting quota: {quota_error}")
                # Don't raise exception, because plan update already succeeded
        
        # If downgrading to start plan, adjust quota to lifetime limit
        if should_adjust_quota_for_start and plan == PlanType.START:
            try:
                # Get current quota
                quota = await get_user_quota(user_id)
                current_tokens_used = getattr(quota, 'weekly_tokens_used', 0)
                
                # Get START plan lifetime limit
                limits = PLAN_LIMITS[PlanType.START]
                lifetime_token_limit = limits.get("lifetime_token_limit", 100_000)
                
                # Cap at lifetime limit (if user already used more than lifetime limit, set to limit)
                adjusted_tokens = min(current_tokens_used, lifetime_token_limit)
                
                now = utcnow()
                quota_update_data = {
                    "weekly_tokens_used": adjusted_tokens,
                    "plan": plan.value,  # Update plan in quota
                    "updated_at": now.isoformat()
                }
                
                quota_response = supabase.table("usage_quotas").update(quota_update_data).eq("user_id", user_id).execute()
                if quota_response.data:
                    if adjusted_tokens < current_tokens_used:
                        print(f"✅ Adjusted user {user_id} quota from {current_tokens_used:,} to {adjusted_tokens:,} (downgraded to start plan, capped at lifetime limit)")
                    else:
                        print(f"✅ Updated user {user_id} quota plan to start (tokens used: {adjusted_tokens:,}/{lifetime_token_limit:,})")
                else:
                    # Quota record may not exist, try to create
                    try:
                        await create_user_quota(user_id)
                        print(f"✅ Created new quota record for user {user_id}")
                    except Exception as create_error:
                        print(f"⚠️ Failed to create quota record: {create_error}")
            except Exception as quota_error:
                print(f"⚠️ Error adjusting quota for start plan: {quota_error}")
                # Don't raise exception, because plan update already succeeded
        
        return result
            
    except APIError as e:
        print(f"Supabase upsert APIError: {e}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"Update user plan failed: {e}")
        import traceback
        traceback.print_exc()
        raise


# ========== User API Key Operations removed ==========
# All users use server API Key, no need to store user keys


# ========== Usage Logging ==========

async def log_usage(
    user_id: str,
    plan: PlanType,
    api_endpoint: str,
    model_used: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    success: bool = True,
    error_message: Optional[str] = None
) -> UsageLog:
    """Log API usage"""
    try:
        from backend.db_models import MODEL_PRICING
        
        # Calculate cost
        pricing = MODEL_PRICING.get(model_used, {"input": 0, "output": 0})
        cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
        
        supabase = get_supabase()
        
        log_data = {
            "user_id": user_id,
            "plan": plan.value,
            "api_endpoint": api_endpoint,
            "model_used": model_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "success": success,
            "error_message": error_message,
            "created_at": utcnow().isoformat()
        }
        
        response = supabase.table("usage_logs").insert(log_data).execute()
        
        if response.data and len(response.data) > 0:
            return UsageLog(**response.data[0])
        else:
            raise Exception("Failed to log Usage")
    except Exception as e:
        print(f"❌ Failed to log Usage: {e}")
        raise


# ========== Usage Quota Management ==========

async def get_user_quota(user_id: str) -> UsageQuota:
    """Get user quota"""
    try:
        supabase = get_supabase()
        # Use direct query (not maybe_single) to avoid 406 errors when no record exists
        # 406 happens when maybe_single() expects exactly 1 row but finds 0
        response = supabase.table("usage_quotas").select("*").eq("user_id", user_id).execute()
        
        # Check if we have data
        if response and response.data and len(response.data) > 0:
            # Save original plan value to check if database needs updating
            original_plan = response.data[0].get('plan')
            
            quota_data = normalize_plan_data(response.data[0])
            # Ensure weekly_tokens_used and monthly_tokens_used fields exist (compatible with old data)
            if 'weekly_tokens_used' not in quota_data:
                quota_data['weekly_tokens_used'] = 0
            if 'monthly_tokens_used' not in quota_data:
                quota_data['monthly_tokens_used'] = 0
            quota = UsageQuota(**quota_data)
            
            # If converted from 'starter', update database
            if original_plan == 'starter':
                try:
                    supabase = get_supabase()
                    supabase.table("usage_quotas").update({"plan": "start"}).eq("user_id", user_id).execute()
                    print(f"✅ Updated user {user_id} quota plan from 'starter' to 'start'")
                except Exception as update_error:
                    print(f"⚠️ Failed to update quota plan: {update_error}")
            
            # Check if quota needs to be reset based on plan type
            # For lifetime quota (start plan), skip reset
            user_plan = await get_user_plan(user_id)
            limits = PLAN_LIMITS.get(user_plan.plan, {})
            is_lifetime = limits.get("is_lifetime", False)
            is_unlimited = limits.get("is_unlimited", False)
            
            now = utcnow()
            should_reset_weekly = False
            should_reset_monthly = False
            
            # Lifetime and unlimited quotas don't reset
            if not is_lifetime and not is_unlimited:
                weekly_token_limit = limits.get("weekly_token_limit")
                monthly_token_limit = limits.get("monthly_token_limit")
                
                if quota.quota_reset_date:
                    reset_date = ensure_utc(quota.quota_reset_date)
                    if reset_date:
                        # Check weekly reset (for weekly plans)
                        if weekly_token_limit is not None:
                            now_year, now_week, _ = now.isocalendar()
                            reset_year, reset_week, _ = reset_date.isocalendar()
                            should_reset_weekly = (now_year != reset_year) or (now_week != reset_week)
                        
                        # Check monthly reset (for monthly plans)
                        if monthly_token_limit is not None:
                            should_reset_monthly = (now.year != reset_date.year) or (now.month != reset_date.month)
                else:
                    # If no reset date, treat as need to reset
                    if weekly_token_limit is not None:
                        should_reset_weekly = True
                    if monthly_token_limit is not None:
                        should_reset_monthly = True
            
            if should_reset_weekly or should_reset_monthly:
                # Reset directly here to avoid calling reset_user_quota causing recursion
                update_data = {
                    "quota_reset_date": now.isoformat(),  # Set to current time (last reset time)
                    "updated_at": now.isoformat()
                }
                
                if should_reset_weekly:
                    update_data["weekly_tokens_used"] = 0
                if should_reset_monthly:
                    update_data["monthly_tokens_used"] = 0
                
                supabase = get_supabase()
                response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
                
                if response.data and len(response.data) > 0:
                    quota_data = normalize_plan_data(response.data[0])
                    quota = UsageQuota(**quota_data)
                    if should_reset_weekly:
                        print(f"📅 Reset user {user_id} weekly token quota (reset by week)")
                    if should_reset_monthly:
                        print(f"📅 Reset user {user_id} monthly token quota (reset by calendar month)")
                else:
                    # If update fails, at least update in-memory object
                    if should_reset_weekly:
                        quota.weekly_tokens_used = 0
                    if should_reset_monthly:
                        quota.monthly_tokens_used = 0
                    quota.quota_reset_date = now
            
            return quota
        else:
            # If no record, create new quota
            print(f"📝 User {user_id} has no quota record, creating new quota")
            return await create_user_quota(user_id)
    except Exception as e:
        print(f"⚠️ Failed to get user quota: {e}")
        import traceback
        traceback.print_exc()
        # Return default quota
        try:
            user_plan = await get_user_plan(user_id)
            limits = PLAN_LIMITS[user_plan.plan]
            
            now = utcnow()
            # quota_reset_date is "last reset time", set to current time
            return UsageQuota(
                user_id=user_id,
                plan=user_plan.plan,
                weekly_tokens_used=0,
                monthly_tokens_used=0,
                quota_reset_date=now,  # Last reset time = current time
                created_at=now,
                updated_at=now
            )
        except Exception as fallback_error:
            print(f"❌ Failed to create default quota: {fallback_error}")
            # Finally return a basic quota object
            # Fallback to NORMAL plan limits
            now = utcnow()
            # quota_reset_date is "last reset time", set to current time
            return UsageQuota(
                user_id=user_id,
                plan=PlanType.NORMAL,
                weekly_tokens_used=0,
                monthly_tokens_used=0,
                quota_reset_date=now,  # Last reset time = current time
                created_at=now,
                updated_at=now
            )


async def create_user_quota(user_id: str) -> UsageQuota:
    """Create user quota using admin client (SERVICE_ROLE_KEY) to bypass RLS
    
    Uses upsert to prevent duplicate inserts if quota already exists
    """
    try:
        # Use admin client (SERVICE_ROLE_KEY) to bypass RLS
        supabase_admin = get_supabase_admin()
        
        user_plan = await get_user_plan(user_id)
        
        now = utcnow()
        # quota_reset_date is "last reset time", set to current time
        quota_data = {
            "user_id": user_id,
            "plan": user_plan.plan.value,
            "weekly_tokens_used": 0,
            "monthly_tokens_used": 0,
            "quota_reset_date": now.isoformat(),  # Last reset time = current time
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Use upsert with on_conflict to handle race conditions
        # If user_id already exists, update the quota; otherwise insert
        print(f"🔍 DEBUG create_user_quota: Upserting quota for user {user_id}")
        response = supabase_admin.table("usage_quotas").upsert(
            quota_data,
            on_conflict="user_id"
        ).execute()
        
        if response is None:
            print(f"❌ Supabase upsert returned None")
            raise Exception("Failed to create quota: Database operation returned empty response")
        
        if not hasattr(response, 'data') or not response.data:
            print(f"❌ Supabase upsert returned empty response.data: {response}")
            raise Exception("Failed to create quota: Database operation did not return data")
        
        if not isinstance(response.data, list) or len(response.data) == 0:
            print(f"❌ Supabase upsert returned empty response.data list: {response.data}")
            raise Exception("Failed to create quota: Database operation returned empty data list")
        
        quota_data = normalize_plan_data(response.data[0])
        return UsageQuota(**quota_data)
    except Exception as e:
        print(f"❌ Failed to create user quota: {e}")
        raise


async def increment_user_quota(user_id: str, tokens_used: int = 0) -> UsageQuota:
    """Increment user token usage
    
    Args:
        user_id: User ID
        tokens_used: Number of tokens used in this request (must be provided, default 0)
    """
    try:
        quota = await get_user_quota(user_id)
        
        supabase = get_supabase()
        
        update_data = {
            "updated_at": utcnow().isoformat()
        }
        
        # Add token usage based on plan type
        if tokens_used > 0:
            user_plan = await get_user_plan(user_id)
            limits = PLAN_LIMITS[user_plan.plan]
            
            # Check if plan uses weekly or monthly quota
            weekly_token_limit = limits.get("weekly_token_limit")
            monthly_token_limit = limits.get("monthly_token_limit")
            
            if weekly_token_limit is not None:
                # Weekly plan: increment weekly_tokens_used
                current_tokens = getattr(quota, 'weekly_tokens_used', 0)
                update_data["weekly_tokens_used"] = current_tokens + tokens_used
            elif monthly_token_limit is not None:
                # Monthly plan: increment monthly_tokens_used
                current_tokens = getattr(quota, 'monthly_tokens_used', 0)
                update_data["monthly_tokens_used"] = current_tokens + tokens_used
            else:
                # Lifetime plan or unlimited: increment weekly_tokens_used (for tracking)
                current_tokens = getattr(quota, 'weekly_tokens_used', 0)
                update_data["weekly_tokens_used"] = current_tokens + tokens_used
        
        response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            quota_data = normalize_plan_data(response.data[0])
            return UsageQuota(**quota_data)
        else:
            raise Exception("Update quota failed")
    except Exception as e:
        print(f"Increment user quota failed: {e}")
        import traceback
        traceback.print_exc()
        raise


async def reset_user_quota(user_id: str) -> UsageQuota:
    """Reset user quota based on plan type (weekly or monthly)
    
    Note: quota_reset_date is defined as "last reset time" (last_reset_at), not "next reset time"
    - Weekly plans: reset by ISO week
    - Monthly plans: reset by calendar month
    """
    try:
        supabase = get_supabase()
        user_plan = await get_user_plan(user_id)
        limits = PLAN_LIMITS[user_plan.plan]
        
        # Query database directly to avoid calling get_user_quota causing recursion
        response = supabase.table("usage_quotas").select("*").eq("user_id", user_id).maybe_single().execute()
        
        now = utcnow()
        
        if not response or not response.data:
            # If no record, create one
            quota_data = {
                "user_id": user_id,
                "plan": user_plan.plan.value,
                "weekly_tokens_used": 0,
                "monthly_tokens_used": 0,
                "quota_reset_date": now.isoformat(),  # Last reset time = current time
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            insert_response = supabase.table("usage_quotas").insert(quota_data).execute()
            if insert_response.data and len(insert_response.data) > 0:
                quota_data = normalize_plan_data(insert_response.data[0])
                return UsageQuota(**quota_data)
            else:
                raise Exception("Failed to create quota")
        
        # Parse existing quota
        if not response.data or len(response.data) == 0:
            raise Exception("Failed to get quota: No data returned")
        quota_raw = normalize_plan_data(response.data[0])
        quota = UsageQuota(**quota_raw)
        
        # Determine reset type based on plan
        weekly_token_limit = limits.get("weekly_token_limit")
        monthly_token_limit = limits.get("monthly_token_limit")
        is_lifetime = limits.get("is_lifetime", False)
        
        should_reset_weekly = False
        should_reset_monthly = False
        
        if quota.quota_reset_date:
            reset_date = ensure_utc(quota.quota_reset_date)
            if reset_date:
                # Check weekly reset (for weekly plans)
                if weekly_token_limit is not None and not is_lifetime:
                    now_year, now_week, _ = now.isocalendar()
                    reset_year, reset_week, _ = reset_date.isocalendar()
                    should_reset_weekly = (now_year != reset_year) or (now_week != reset_week)
                
                # Check monthly reset (for monthly plans)
                if monthly_token_limit is not None:
                    should_reset_monthly = (now.year != reset_date.year) or (now.month != reset_date.month)
        else:
            # If no reset date, treat as need to reset
            if weekly_token_limit is not None and not is_lifetime:
                should_reset_weekly = True
            if monthly_token_limit is not None:
                should_reset_monthly = True
        
        update_data = {
            "updated_at": now.isoformat()
        }
        
        # Reset based on plan type
        if should_reset_weekly:
            update_data["weekly_tokens_used"] = 0
            update_data["quota_reset_date"] = now.isoformat()
            print(f"📅 Reset user {user_id} weekly token quota (reset by week)")
        
        if should_reset_monthly:
            update_data["monthly_tokens_used"] = 0
            update_data["quota_reset_date"] = now.isoformat()
            print(f"📅 Reset user {user_id} monthly token quota (reset by calendar month)")
        
        # Only update if reset is needed
        if should_reset_weekly or should_reset_monthly:
            update_response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
            
            if update_response.data and len(update_response.data) > 0:
                quota_data = normalize_plan_data(update_response.data[0])
                return UsageQuota(**quota_data)
            else:
                raise Exception("Failed to reset quota")
        else:
            # No reset needed, return existing quota
            return quota
            
    except Exception as e:
        print(f"❌ Failed to reset user quota: {e}")
        raise


async def check_rate_limit(user_id: str, estimated_tokens: int = 0) -> tuple[bool, str]:
    """Check if user exceeds token quota limit
    
    Args:
        user_id: User ID
        estimated_tokens: Estimated number of tokens that will be used for this request (optional, for pre-check)
    
    Returns:
        (bool, str): (whether allowed, error message)
    """
    try:
        user_plan = await get_user_plan(user_id)
        quota = await get_user_quota(user_id)
        limits = PLAN_LIMITS[user_plan.plan]
        
        # Internal Plan: unlimited quota, always allow
        is_unlimited = limits.get("is_unlimited", False)
        if is_unlimited:
            return True, ""
        
        # Check token limit (considering estimated tokens)
        # Support three quota types: weekly, monthly, and lifetime
        weekly_token_limit = limits.get("weekly_token_limit")
        monthly_token_limit = limits.get("monthly_token_limit")
        lifetime_token_limit = limits.get("lifetime_token_limit")
        is_lifetime = limits.get("is_lifetime", False)
        
        weekly_tokens_used = getattr(quota, 'weekly_tokens_used', 0)
        monthly_tokens_used = getattr(quota, 'monthly_tokens_used', 0)
        
        # Check lifetime quota (start plan)
        if is_lifetime and lifetime_token_limit is not None:
            if weekly_tokens_used + estimated_tokens > lifetime_token_limit:
                remaining = lifetime_token_limit - weekly_tokens_used
                if remaining <= 0:
                    return False, f"Lifetime tokens exhausted: {weekly_tokens_used:,}/{lifetime_token_limit:,}. Please upgrade Plan."
                else:
                    return False, f"Insufficient lifetime tokens quota: Used {weekly_tokens_used:,}/{lifetime_token_limit:,}, remaining {remaining:,}, but estimated need {estimated_tokens:,}. Please upgrade Plan."
        
        # Check weekly quota (normal plan)
        if weekly_token_limit is not None:
            if weekly_tokens_used + estimated_tokens > weekly_token_limit:
                remaining = weekly_token_limit - weekly_tokens_used
                if remaining <= 0:
                    return False, f"This week's tokens exhausted: {weekly_tokens_used:,}/{weekly_token_limit:,}. Please try again next week or upgrade Plan."
                else:
                    return False, f"Insufficient weekly tokens quota: Used {weekly_tokens_used:,}/{weekly_token_limit:,}, remaining {remaining:,}, but estimated need {estimated_tokens:,}. Please try again next week or upgrade Plan."
        
        # Check monthly quota (high/ultra plan)
        if monthly_token_limit is not None:
            if monthly_tokens_used + estimated_tokens > monthly_token_limit:
                remaining = monthly_token_limit - monthly_tokens_used
                if remaining <= 0:
                    return False, f"This month's tokens exhausted: {monthly_tokens_used:,}/{monthly_token_limit:,}. Please try again next month or upgrade Plan."
                else:
                    return False, f"Insufficient monthly tokens quota: Used {monthly_tokens_used:,}/{monthly_token_limit:,}, remaining {remaining:,}, but estimated need {estimated_tokens:,}. Please try again next month or upgrade Plan."
        
        return True, ""
    except Exception as e:
        print(f"Check rate limit failed: {e}")
        import traceback
        traceback.print_exc()
        # On error, allow request to avoid blocking
        return True, ""

