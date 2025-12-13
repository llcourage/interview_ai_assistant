"""
Database operations
Provides CRUD operations for user Plan, API Keys, Usage
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from backend.db_supabase import get_supabase
from backend.db_models import UserPlan, UsageLog, UsageQuota, PlanType, PLAN_LIMITS

# Encryption related code removed - all users use server API Key


def normalize_plan_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compatible with old data: convert 'starter' plan to 'start', ensure both weekly and monthly fields exist"""
    if isinstance(data, dict):
        data = data.copy()  # Create copy to avoid modifying original data
        if data.get('plan') == 'starter':
            data['plan'] = 'start'
        # Ensure both weekly and monthly fields exist for backward compatibility
        if 'weekly_tokens_used' not in data:
            data['weekly_tokens_used'] = 0
        if 'monthly_tokens_used' not in data:
            data['monthly_tokens_used'] = 0
    return data


# ========== User Plan Operations ==========

async def get_user_plan(user_id: str) -> UserPlan:
    """Get user Plan"""
    try:
        supabase = get_supabase()
        # Use maybe_single() instead of single() to avoid exceptions when no record exists
        response = supabase.table("user_plans").select("*").eq("user_id", user_id).maybe_single().execute()
        
        if response.data:
            plan_data = normalize_plan_data(response.data)
            return UserPlan(**plan_data)
        else:
            # If no record, try direct query first (without maybe_single)
            direct_response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
            
            if direct_response.data and len(direct_response.data) > 0:
                plan_data = normalize_plan_data(direct_response.data[0])
                return UserPlan(**plan_data)
            
            # If no plan record found, create default START plan
            print(f"User {user_id} has no plan record, creating default START plan")
            return await create_user_plan(user_id)
    except Exception as e:
        print(f"⚠️ Failed to get user Plan: {e}")
        # If creation fails, try returning in-memory object (but this is not persistent)
        try:
            return await create_user_plan(user_id)
        except Exception as create_error:
            print(f"❌ Failed to create user Plan: {create_error}")
            # Finally return a temporary object (not recommended, but at least won't crash)
            return UserPlan(
                user_id=user_id,
                plan=PlanType.START,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )


async def create_user_plan(user_id: str, plan: PlanType = PlanType.START) -> UserPlan:
    """Create user Plan"""
    try:
        supabase = get_supabase()
        now = datetime.now()
        
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
        
        response = supabase.table("user_plans").insert(plan_data).execute()
        
        # Defensive check: ensure response and response.data exist
        if response is None:
            print(f"❌ Supabase insert returned None")
            raise Exception("Failed to create Plan: Database operation returned empty response")
        
        if not hasattr(response, 'data') or not response.data:
            print(f"❌ Supabase insert returned empty response.data: {response}")
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
    stripe_subscription_id: Optional[str] = None,
    subscription_status: Optional[str] = None,
    plan_expires_at: Optional[datetime] = None
) -> UserPlan:
    """Update user Plan (create if record doesn't exist) - use upsert to avoid 204 error
    
    If upgrading from start plan to other plan, will automatically reset quota
    """
    try:
        from postgrest.exceptions import APIError
        
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
        now = datetime.now()
        data = {
            "user_id": user_id,
            "updated_at": now.isoformat()
        }
        
        # Only add non-None values to data (avoid overwriting existing values with NULL)
        # Note: If creating new record (via webhook), plan will always be passed
        # If partial update (plan is None), only update other fields
        if plan is not None:
            # Ensure plan value is normalized (convert 'starter' to 'start' if somehow present)
            plan_value = plan.value
            if plan_value == 'starter':
                plan_value = 'start'
            data["plan"] = plan_value
        
        # These fields are only updated when they have values
        if stripe_customer_id is not None:
            data["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id is not None:
            data["stripe_subscription_id"] = stripe_subscription_id
        if subscription_status is not None:
            data["subscription_status"] = subscription_status
        if plan_expires_at is not None:
            data["plan_expires_at"] = plan_expires_at.isoformat()
        
        # Before upsert, ALWAYS check if existing record has 'starter' value and fix it
        # This is critical because if plan is None (partial update), data won't include plan field
        # and the 'starter' value would remain in database, causing constraint violations
        try:
            existing_response = supabase.table("user_plans").select("plan").eq("user_id", user_id).maybe_single().execute()
            if existing_response.data and existing_response.data.get("plan") == 'starter':
                # Fix existing 'starter' value to 'start' before upsert
                # This must be done BEFORE upsert to avoid constraint violations
                fix_response = supabase.table("user_plans").update({"plan": "start"}).eq("user_id", user_id).execute()
                if fix_response.data:
                    print(f"✅ Fixed existing 'starter' plan value for user {user_id}")
                else:
                    print(f"⚠️ Fix update returned no data for user {user_id}")
        except Exception as fix_error:
            # If fix fails, log error but continue with upsert
            # If this is a new user, the fix will fail (no record exists), which is OK
            print(f"⚠️ Could not fix existing plan (may be new user): {fix_error}")
            import traceback
            traceback.print_exc()
        
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
                now = datetime.now()
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
                
                now = datetime.now()
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
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("usage_logs").insert(log_data).execute()
        
        if response.data:
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
        # Use maybe_single() instead of single() to avoid exceptions when no record exists
        response = supabase.table("usage_quotas").select("*").eq("user_id", user_id).maybe_single().execute()
        
        if response and response.data:
            # Save original plan value to check if database needs updating
            original_plan = response.data.get('plan')
            
            quota_data = normalize_plan_data(response.data)
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
            
            now = datetime.now()
            should_reset_weekly = False
            should_reset_monthly = False
            
            # Lifetime and unlimited quotas don't reset
            if not is_lifetime and not is_unlimited:
                weekly_token_limit = limits.get("weekly_token_limit")
                monthly_token_limit = limits.get("monthly_token_limit")
                
                if quota.quota_reset_date:
                    reset_date = quota.quota_reset_date
                    if isinstance(reset_date, str):
                        reset_date = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
                    
                    reset_date_no_tz = reset_date.replace(tzinfo=None) if reset_date.tzinfo else reset_date
                    
                    # Check weekly reset (for weekly plans)
                    if weekly_token_limit is not None:
                        now_year, now_week, _ = now.isocalendar()
                        reset_year, reset_week, _ = reset_date_no_tz.isocalendar()
                        should_reset_weekly = (now_year != reset_year) or (now_week != reset_week)
                    
                    # Check monthly reset (for monthly plans)
                    if monthly_token_limit is not None:
                        should_reset_monthly = (now.year != reset_date_no_tz.year) or (now.month != reset_date_no_tz.month)
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
                
                if response.data:
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
            
            now = datetime.now()
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
            now = datetime.now()
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
    """Create user quota"""
    try:
        supabase = get_supabase()
        
        user_plan = await get_user_plan(user_id)
        
        now = datetime.now()
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
        
        response = supabase.table("usage_quotas").insert(quota_data).execute()
        
        if response.data:
            quota_data = normalize_plan_data(response.data[0])
            return UsageQuota(**quota_data)
        else:
            raise Exception("Failed to create quota")
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
            "updated_at": datetime.now().isoformat()
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
        
        if response.data:
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
        
        now = datetime.now()
        
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
            if insert_response.data:
                quota_data = normalize_plan_data(insert_response.data[0])
                return UsageQuota(**quota_data)
            else:
                raise Exception("Failed to create quota")
        
        # Parse existing quota
        quota_raw = normalize_plan_data(response.data[0])
        quota = UsageQuota(**quota_raw)
        
        # Determine reset type based on plan
        weekly_token_limit = limits.get("weekly_token_limit")
        monthly_token_limit = limits.get("monthly_token_limit")
        is_lifetime = limits.get("is_lifetime", False)
        
        should_reset_weekly = False
        should_reset_monthly = False
        
        if quota.quota_reset_date:
            reset_date = quota.quota_reset_date
            if isinstance(reset_date, str):
                reset_date = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
            
            reset_date_no_tz = reset_date.replace(tzinfo=None) if reset_date.tzinfo else reset_date
            
            # Check weekly reset (for weekly plans)
            if weekly_token_limit is not None and not is_lifetime:
                now_year, now_week, _ = now.isocalendar()
                reset_year, reset_week, _ = reset_date_no_tz.isocalendar()
                should_reset_weekly = (now_year != reset_year) or (now_week != reset_week)
            
            # Check monthly reset (for monthly plans)
            if monthly_token_limit is not None:
                should_reset_monthly = (now.year != reset_date_no_tz.year) or (now.month != reset_date_no_tz.month)
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
            
            if update_response.data:
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

