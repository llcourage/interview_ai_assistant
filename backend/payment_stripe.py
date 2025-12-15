"""
Stripe payment integration
Provides subscription purchase, Webhook handling and other functions
"""
import os
import stripe
from datetime import datetime, timedelta, timezone
from backend.utils.time import utcnow, ensure_utc
from typing import Optional
from dotenv import load_dotenv
from backend.db_operations import get_user_plan, update_user_plan, _CLEAR_FIELD
from backend.db_models import PlanType

load_dotenv()

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs corresponding to Plans
STRIPE_PRICE_IDS = {
    PlanType.NORMAL: os.getenv("STRIPE_PRICE_NORMAL", "price_xxx"),
    PlanType.HIGH: os.getenv("STRIPE_PRICE_HIGH", "price_yyy"),
    PlanType.ULTRA: os.getenv("STRIPE_PRICE_ULTRA", "price_zzz"),
    PlanType.PREMIUM: os.getenv("STRIPE_PRICE_PREMIUM", "price_premium")
}


async def create_checkout_session(user_id: str, plan: PlanType, success_url: str, cancel_url: str, user_email: Optional[str] = None) -> dict:
    """Create Stripe Checkout Session
    
    Args:
        user_id: User ID
        plan: Subscription plan
        success_url: Redirect URL after successful payment
        cancel_url: Redirect URL after cancelled payment
        user_email: User email (optional, if provided will pre-fill in Checkout)
    
    Returns:
        dict: Dictionary containing checkout_url
    """
    try:
        # Prevent Internal Plan from being purchased
        if plan == PlanType.INTERNAL:
            raise ValueError("Internal Plan cannot be purchased through checkout. It can only be manually assigned in Supabase.")
        
        # Check Stripe API Key
        if not stripe.api_key or stripe.api_key == "":
            raise ValueError("STRIPE_SECRET_KEY not configured, please set in environment variables")
        
        price_id = STRIPE_PRICE_IDS.get(plan)
        if not price_id or price_id in ["price_xxx", "price_yyy", "price_zzz", "price_premium"]:
            raise ValueError(
                f"Stripe Price ID not found for {plan}. "
                f"Current value: {price_id}. "
                f"Please set STRIPE_PRICE_{plan.value.upper()} in Vercel environment variables"
            )
        
        # Get or create Stripe Customer
        user_plan_data = await get_user_plan(user_id)
        
        if user_plan_data.stripe_customer_id:
            customer_id = user_plan_data.stripe_customer_id
            # If email provided, update Customer email
            if user_email:
                try:
                    stripe.Customer.modify(
                        customer_id,
                        email=user_email
                    )
                    print(f"✅ Updated Stripe Customer {customer_id} email to {user_email}")
                except Exception as e:
                    print(f"⚠️ Failed to update Customer email: {e}")
            
            # Always create a new Checkout Session to ensure payment is processed
            # Even if user has existing subscription, they must complete payment through Stripe
            # Stripe will handle subscription updates and proration automatically via webhook
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=True,  # Enable promotion code input
                metadata={
                    "user_id": user_id,
                    "plan": plan.value
                }
            )
        else:
            # Create new customer
            customer_data = {
                "metadata": {"user_id": user_id}
            }
            if user_email:
                customer_data["email"] = user_email
            
            customer = stripe.Customer.create(**customer_data)
            customer_id = customer.id
            
            print(f"✅ Created Stripe Customer {customer_id}, email: {user_email}")
            
            # Save to database
            await update_user_plan(user_id, stripe_customer_id=customer_id)
            
            # Create Checkout Session (using customer_id)
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=True,  # Enable promotion code input
                metadata={
                    "user_id": user_id,
                    "plan": plan.value
                }
            )
        
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        print(f"❌ Failed to create Stripe Checkout Session: {e}")
        raise


async def handle_checkout_completed(session: dict):
    """Handle successful payment Webhook
    
    Args:
        session: Stripe Checkout Session object
    """
    try:
        session_id = session.get('id')
        
        # Check if metadata exists
        metadata = session.get("metadata") or {}
        if not metadata:
            print(f"Warning: Checkout session {session_id} has no metadata, skipping")
            return
        
        user_id = metadata.get("user_id")
        plan_value = metadata.get("plan")
        
        if not user_id or not plan_value:
            print(f"Warning: Checkout session {session_id} missing user_id or plan in metadata")
            return
        
        # Idempotency check: prevent duplicate processing
        # Note: We rely on Stripe's webhook deduplication and the fact that
        # checkout sessions are typically only completed once per session_id.
        # For stronger idempotency, consider adding last_checkout_session_id field to user_plans table.
        
        # Normalize 'starter' to 'start' before converting to PlanType
        if plan_value == 'starter':
            plan_value = 'start'
        
        # ✅ Defensive: Validate plan_value before converting to PlanType
        try:
            new_plan = PlanType(plan_value)
        except Exception:
            print(f"⚠️ Invalid plan in checkout metadata: plan={plan_value}, session_id={session_id}, user_id={user_id}. Skipping.")
            return
        
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        
        # Get current user plan to detect upgrade
        current_user_plan = await get_user_plan(user_id)
        current_plan = current_user_plan.plan
        
        # Check if this is an upgrade
        is_upgrade = _is_upgrade(current_plan, new_plan)
        
        # ✅ Gate: Reject START plan via checkout (START should be free default/cancellation fallback, not purchased)
        if new_plan == PlanType.START:
            print(f"⚠️ Checkout attempted to set plan=start; ignoring. START plan should not be purchased via checkout.")
            return
        
        # ✅ Gate: Reject downgrades via checkout (must use downgrade_subscription API)
        is_downgrade = _is_downgrade(current_plan, new_plan)
        if is_downgrade:
            print(f"⚠️ Checkout attempted downgrade {current_plan.value}->{new_plan.value}; ignoring. Use downgrade_subscription API instead.")
            return
        
        # Get subscription details and check for pending_update
        subscription = None
        pending_update = None
        next_update_at = None
        retrieve_failed = False  # Track if we failed to retrieve subscription
        pending_update_is_relevant = False  # Track if pending_update is related to current checkout
        
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                
                # Check for pending_update (scheduled changes that haven't taken effect yet)
                pending_update = getattr(subscription, "pending_update", None)
                
                if pending_update:
                    # Check if pending_update is related to current checkout by comparing price_id
                    # This is more reliable than time-based heuristics
                    
                    # Get the target price_id for the new plan
                    # Try both PlanType enum and string value (defensive)
                    target_price_id = STRIPE_PRICE_IDS.get(new_plan) or STRIPE_PRICE_IDS.get(new_plan.value)
                    
                    # Try to extract price_id from pending_update using helper function
                    pending_price_id = _extract_price_id_from_pending_update(pending_update)
                    
                    # Compare price_ids to determine relevance
                    if target_price_id and pending_price_id:
                        if pending_price_id == target_price_id:
                            # pending_update is relevant - it will update to the same plan user just purchased
                            pending_update_is_relevant = True
                            
                            # Get effective_at for scheduling
                            # Important: next_update_at must be the effective_at (not period_end) when next_plan is set
                            if hasattr(pending_update, "effective_at") and pending_update.effective_at:
                                next_update_at = ensure_utc(
                                    datetime.fromtimestamp(pending_update.effective_at, tz=timezone.utc)
                                )
                                print(f"⚠️ Subscription {subscription_id} has pending_update for same plan ({new_plan.value}), scheduled for {next_update_at}, upgrade will be delayed")
                            else:
                                # No effective_at - we don't know when it will take effect
                                # For checkout.session.completed, default to immediate upgrade (user has paid)
                                # Don't fallback to current_period_end as that's billing date, not effective_at
                                pending_update = None
                                pending_update_is_relevant = False
                                print(f"⚠️ Subscription {subscription_id} has pending_update for same plan ({new_plan.value}) but no effective_at, defaulting to immediate upgrade (checkout completed)")
                        else:
                            # pending_update is for a different plan, not relevant to this checkout
                            pending_update = None
                            pending_update_is_relevant = False
                            print(f"⚠️ Subscription {subscription_id} has pending_update for different plan (pending_price_id={pending_price_id}, target_price_id={target_price_id}), ignoring it for immediate upgrade")
                    else:
                        # Can't extract price_id or target_price_id not found
                        # For checkout.session.completed, default to immediate upgrade (user has paid)
                        pending_update = None
                        pending_update_is_relevant = False
                        if not target_price_id:
                            print(f"⚠️ Subscription {subscription_id} has pending_update but target_price_id not found for {new_plan.value}, defaulting to immediate upgrade")
                        else:
                            print(f"⚠️ Subscription {subscription_id} has pending_update but couldn't extract pending_price_id, defaulting to immediate upgrade (user has paid)")
                    
                    # If we still have pending_update, ensure next_update_at is set
                    # Note: next_update_at must be effective_at (not period_end) when next_plan is set
                    if pending_update and pending_update_is_relevant and next_update_at is None:
                        # This shouldn't happen if logic above is correct, but handle defensively
                        # If we don't have effective_at, we already set pending_update_is_relevant=False above
                        # So this branch should rarely execute
                        print(f"⚠️ Subscription {subscription_id} has pending_update but next_update_at is None, defaulting to immediate upgrade")
                        pending_update = None
                        pending_update_is_relevant = False
                else:
                    # No pending_update, use current_period_end for next billing date
                    if subscription.current_period_end:
                        next_update_at = ensure_utc(
                            datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
                        )
                        print(f"🔍 Subscription {subscription_id}: next billing date = {next_update_at}")
            except Exception as e:
                retrieve_failed = True
                print(f"⚠️ Failed to get subscription details for {subscription_id}: {e}")
                print(f"⚠️ Cannot determine if pending_update exists, will immediately upgrade (checkout completed)")
        
        # Update user Plan based on whether there's a pending_update
        # For checkout.session.completed, default to immediate upgrade (user has paid)
        if retrieve_failed:
            # Case 3: Failed to retrieve subscription
            # For checkout.session.completed, immediately upgrade (user has paid)
            await update_user_plan(
                user_id=user_id,
                # For checkout.session.completed, immediately upgrade (user has paid)
                plan=new_plan,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                subscription_status="active",  # Use default since we can't retrieve subscription
                plan_expires_at=_CLEAR_FIELD,
                # Don't update next_update_at - keep existing value to avoid overwriting correct data
                next_plan=_CLEAR_FIELD,  # Clear any scheduled changes
                cancel_at_period_end=False,
            )
            print(f"✅ User {user_id} upgraded to {new_plan.value} (Stripe retrieve failed, but checkout completed)")
        elif pending_update and pending_update_is_relevant:
            # Case 2: Stripe has pending_update that is relevant to current checkout
            # Don't change plan immediately, schedule it via next_plan
            await update_user_plan(
                user_id=user_id,
                # plan is not updated (keep current plan until pending_update takes effect)
                next_plan=new_plan,  # Schedule upgrade for when pending_update takes effect
                next_update_at=next_update_at,  # Use pending_update.effective_at
                plan_expires_at=_CLEAR_FIELD,  # Clear expiration (upgrade overrides cancellation/expiration)
                cancel_at_period_end=False,  # Clear cancel flag (upgrade overrides cancellation)
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                subscription_status=subscription.status if subscription else "active",
            )
            print(f"✅ User {user_id} upgrade to {new_plan.value} scheduled for {next_update_at} (pending_update in Stripe)")
        else:
            # Case 1: No pending_update or pending_update is not relevant
            # For checkout.session.completed, immediately upgrade (user has paid)
            await update_user_plan(
                user_id=user_id,
                plan=new_plan,  # Immediately upgrade
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                subscription_status=subscription.status if subscription else "active",
                plan_expires_at=_CLEAR_FIELD,  # Clear expiration (upgrade overrides cancellation/expiration)
                next_update_at=next_update_at,  # Keep as billing date (only meaningful when next_plan=None)
                # Clear all scheduled changes (upgrade overrides any existing downgrade/cancellation)
                next_plan=_CLEAR_FIELD,
                cancel_at_period_end=False,  # Clear cancel flag
            )
            if is_upgrade:
                print(f"✅ User {user_id} upgraded from {current_plan.value} to {new_plan.value}, next billing: {next_update_at}")
            else:
                print(f"✅ User {user_id} subscribed to {new_plan.value} plan, next billing: {next_update_at}")
    except Exception as e:
        error_msg = f"Failed to process checkout completed webhook: {e}"
        print(f"Error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise


async def _fetch_user_plan_row_admin(user_id: str) -> Optional[dict]:
    """Fetch user plan row from DB as raw dict (read-only, no side effects).
    
    Used for webhook deduplication to avoid triggering state machine logic.
    
    Note: Currently not used in handle_subscription_updated (we use response.data[0] directly
    to reduce DB calls). Kept for future use when we need to fetch only specific fields.
    
    Args:
        user_id: User ID
    
    Returns:
        Optional[dict]: Raw user plan row from database, or None if not found
    """
    try:
        from backend.db_supabase import get_supabase_admin
        supabase = get_supabase_admin()
        response = supabase.table("user_plans").select(
            "user_id, plan, next_plan, next_update_at, plan_expires_at, stripe_event_ts, cancel_at_period_end"
        ).eq("user_id", user_id).execute()
        
        if response and response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"⚠️ _fetch_user_plan_row_admin failed for user {user_id}: {e}")
        return None


def _parse_dt_maybe(v):
    """Parse datetime from various formats (string, datetime, None).
    
    Args:
        v: datetime string, datetime object, or None
    
    Returns:
        UTC-aware datetime or None
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        return ensure_utc(v)
    if isinstance(v, str):
        # Handle ISO format strings: '2025-12-13T01:49:11.678945+00:00' or '...Z'
        return ensure_utc(datetime.fromisoformat(v.replace("Z", "+00:00")))
    # Last resort: try ensure_utc
    return ensure_utc(v)


async def handle_subscription_updated(
    subscription: dict,
    event_created: Optional[int] = None,
    event_id: Optional[str] = None,
) -> None:
    """Handle subscription update Webhook
    
    Args:
        subscription: Stripe Subscription object
        event_created: Stripe event.created Unix timestamp (for deduplication)
        event_id: Stripe event.id (for logging/debugging)
    """
    try:
        # ✅ Fix 1: Handle customer_id as dict or string
        customer = subscription.get("customer")
        customer_id = customer.get("id") if isinstance(customer, dict) else customer
        if not customer_id:
            print(f"⚠️ Missing customer_id in subscription: {subscription.get('id')}")
            return
        
        # ✅ Fix A1: Use get + guard for status
        status = subscription.get("status")
        subscription_id = subscription.get("id")
        if not status:
            print(f"⚠️ Missing status in subscription: subscription_id={subscription_id}, customer_id={customer_id}, event_id={event_id}")
            return
        
        # ✅ Fix 2: Log event_created for debugging
        print(f"🔍 Processing subscription update: subscription_id={subscription_id}, customer_id={customer_id}, status={status}, event_id={event_id}, event_created={event_created}")
        
        # Find user from database using admin client (bypass RLS)
        from backend.db_supabase import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Use direct query instead of maybe_single() to avoid 406 errors
        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"⚠️ User not found with stripe_customer_id={customer_id}")
            return
        
        # ✅ Use response.data[0] directly (single DB call, no additional fetches)
        user_row = response.data[0]
        user_id = user_row["user_id"]
        current_plan = user_row.get("plan")
        
        # ✅ Event deduplication: Check stripe_event_ts using already-fetched data
        # ✅ Fix A2: Use is not None instead of truthy check
        if event_created is not None:
            db_ts = user_row.get("stripe_event_ts")
            if db_ts is not None:
                db_ts = int(db_ts)
                event_ts = int(event_created)
                if db_ts >= event_ts:
                    print(f"⚠️ Ignore old subscription.updated event: db_ts={db_ts} >= event_ts={event_ts} (event_id={event_id})")
                    return
        
        print(f"🔍 Found user: user_id={user_id}, current_plan={current_plan}")
        
        # ✅ Sync cancel_at_period_end from Stripe
        cancel_at_period_end = bool(subscription.get("cancel_at_period_end", False))
        
        # Get next billing date from subscription
        next_update_at = None
        if subscription.get("current_period_end"):
            next_update_at = ensure_utc(
                datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc)
            )
            print(f"🔍 Subscription {subscription_id}: next billing date = {next_update_at}")
        
        # ✅ Check if there's a scheduled change using already-fetched data
        has_scheduled_change = user_row.get("next_plan") is not None
        
        # Update subscription status
        if status == "active":
            # Stage 1: Only sync status fields, don't update plan (to avoid conflicts with handle_checkout_completed)
            # Plan updates should be handled by handle_checkout_completed or downgrade_subscription
            
            # ✅ Build kwargs conditionally (only pass fields that need updating)
            kwargs = {
                "user_id": user_id,
                "subscription_status": "active",
                "cancel_at_period_end": cancel_at_period_end,
            }
            
            # ✅ Protection: Only sync critical fields if we have event_created (dedup protection)
            # Without event_created, we can't dedup, so avoid overwriting with potentially stale data
            if event_created is not None:
                kwargs["stripe_event_ts"] = event_created
                kwargs["stripe_subscription_id"] = subscription_id
                if not has_scheduled_change and next_update_at is not None:
                    kwargs["next_update_at"] = next_update_at
            else:
                print(f"⚠️ active status update without event_created - skipping critical fields (stripe_subscription_id, next_update_at) to avoid stale data overwrite")
            
            await update_user_plan(**kwargs)
            print(f"✅ User {user_id} subscription status synced: status=active, cancel_at_period_end={cancel_at_period_end}, event_ts={event_created}")
                
        elif status in ["canceled", "past_due", "unpaid"]:
            # Subscription canceled or overdue
            # Note: For "canceled" status, we only sync status/cancel flag/event_ts
            # Don't actively change plan here (let get_user_plan state machine handle it)
            
            plan_expires_at_raw = user_row.get("plan_expires_at")
            
            if status == "canceled":
                # ✅ For canceled: Only sync status, don't change plan
                # The plan change should be handled by get_user_plan state machine based on plan_expires_at
                kwargs = {
                    "user_id": user_id,
                    "subscription_status": status,
                    "cancel_at_period_end": cancel_at_period_end,
                }
                if event_created is not None:
                    kwargs["stripe_event_ts"] = event_created
                
                await update_user_plan(**kwargs)
                print(f"ℹ️ User {user_id} subscription canceled, status synced (plan change handled by state machine)")
                
            elif status in ["past_due", "unpaid"]:
                # ✅ Fix 4: Protection - Don't downgrade if user has scheduled change
                if has_scheduled_change:
                    print(f"⚠️ {status} but user has scheduled change next_plan={user_row.get('next_plan')}; only syncing status.")
                    # Only sync status, don't change plan
                    kwargs = {
                        "user_id": user_id,
                        "subscription_status": status,
                        "cancel_at_period_end": cancel_at_period_end,
                    }
                    if event_created is not None:
                        kwargs["stripe_event_ts"] = event_created
                    
                    await update_user_plan(**kwargs)
                    print(f"ℹ️ User {user_id} subscription {status}, status synced (scheduled change preserved)")
                    return
                
                # For past_due/unpaid: Check if plan_expires_at exists and is in the future
                if plan_expires_at_raw:
                    # ✅ Fix 3: Use _parse_dt_maybe for robust datetime parsing
                    plan_expires_at = _parse_dt_maybe(plan_expires_at_raw)
                    if plan_expires_at and plan_expires_at > utcnow():
                        # Plan hasn't expired yet, keep current plan but update status
                        print(f"ℹ️ User {user_id} subscription {status} but plan expires at {plan_expires_at}, keeping current plan until then")
                        kwargs = {
                            "user_id": user_id,
                            "subscription_status": status,
                            "cancel_at_period_end": cancel_at_period_end,
                        }
                        if event_created is not None:
                            kwargs["stripe_event_ts"] = event_created
                        
                        await update_user_plan(**kwargs)
                    else:
                        # Plan has expired, downgrade to start
                        # ✅ Fix A3: Use _CLEAR_FIELD to explicitly clear plan_expires_at
                        kwargs = {
                            "user_id": user_id,
                            "plan": PlanType.START,
                            "subscription_status": status,
                            "plan_expires_at": _CLEAR_FIELD,  # ✅ Use sentinel to explicitly clear field
                            "cancel_at_period_end": cancel_at_period_end,
                        }
                        if event_created is not None:
                            kwargs["stripe_event_ts"] = event_created
                        
                        await update_user_plan(**kwargs)
                        print(f"⚠️ User {user_id} subscription {status} and plan expired, downgraded to start plan")
                else:
                    # No plan_expires_at set, downgrade immediately (unpaid/past_due)
                    kwargs = {
                        "user_id": user_id,
                        "plan": PlanType.START,
                        "subscription_status": status,
                        "cancel_at_period_end": cancel_at_period_end,
                    }
                    if event_created is not None:
                        kwargs["stripe_event_ts"] = event_created
                    
                    await update_user_plan(**kwargs)
                    print(f"⚠️ User {user_id} subscription {status}, downgraded to start plan immediately")
        else:
            # Other statuses - just update status, don't change plan
            kwargs = {
                "user_id": user_id,
                "subscription_status": status,
                "cancel_at_period_end": cancel_at_period_end,
            }
            if event_created is not None:
                kwargs["stripe_event_ts"] = event_created
            
            await update_user_plan(**kwargs)
            print(f"ℹ️ User {user_id} subscription status updated to {status}, cancel_at_period_end={cancel_at_period_end}")
            
    except Exception as e:
        print(f"❌ Failed to handle subscription update Webhook: {e}")
        import traceback
        traceback.print_exc()
        raise


async def handle_subscription_pending_update_applied(
    subscription: dict,
    event_created: Optional[int] = None,
    event_id: Optional[str] = None,
) -> None:
    """Handle customer.subscription.pending_update_applied webhook.

    When Stripe applies a pending_update, immediately apply the scheduled plan change
    in our DB (next_plan -> plan) for timeliness and accuracy.

    Idempotent:
    - If next_plan is already cleared / plan already updated, no-op.
    - Uses stripe_event_ts to prevent out-of-order events overwriting newer state.

    Args:
        subscription: Stripe Subscription object
        event_created: Stripe event.created Unix timestamp (for deduplication)
        event_id: Stripe event.id (for logging/debugging)
    """
    try:
        # customer can be str or dict
        customer = subscription.get("customer")
        customer_id = customer.get("id") if isinstance(customer, dict) else customer
        subscription_id = subscription.get("id")

        if not customer_id:
            print(f"⚠️ Missing customer_id in pending_update_applied: subscription_id={subscription_id}, event_id={event_id}")
            return

        status = subscription.get("status") or "active"
        cancel_at_period_end = bool(subscription.get("cancel_at_period_end", False))

        print(
            f"🔍 Processing pending_update_applied: subscription_id={subscription_id}, "
            f"customer_id={customer_id}, status={status}, event_id={event_id}, event_created={event_created}"
        )

        # Find user row by stripe_customer_id (admin client)
        from backend.db_supabase import get_supabase_admin
        supabase = get_supabase_admin()

        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).execute()
        if not response.data:
            print(f"⚠️ User not found with stripe_customer_id={customer_id} (pending_update_applied)")
            return

        user_row = response.data[0]
        user_id = user_row["user_id"]

        # Dedup / ordering protection
        if event_created is not None:
            db_ts = user_row.get("stripe_event_ts")
            if db_ts is not None and int(db_ts) >= int(event_created):
                print(
                    f"⚠️ Ignore old pending_update_applied event: db_ts={int(db_ts)} >= event_ts={int(event_created)} "
                    f"(user_id={user_id}, event_id={event_id})"
                )
                return

        current_plan_raw = user_row.get("plan")
        next_plan_raw = user_row.get("next_plan")

        if not next_plan_raw:
            # Nothing scheduled on our side; just sync status fields (safe/no side effects)
            kwargs = {
                "user_id": user_id,
                "subscription_status": status,
                "cancel_at_period_end": cancel_at_period_end,
                "stripe_subscription_id": subscription_id,
            }
            if event_created is not None:
                kwargs["stripe_event_ts"] = event_created

            await update_user_plan(**kwargs)
            print(f"ℹ️ pending_update_applied but no next_plan in DB; status synced only (user_id={user_id})")
            return

        # Parse PlanType safely
        try:
            next_plan = PlanType(next_plan_raw) if not isinstance(next_plan_raw, PlanType) else next_plan_raw
        except Exception:
            print(f"⚠️ Invalid next_plan in DB: next_plan={next_plan_raw} (user_id={user_id}); not applying")
            return

        try:
            current_plan = PlanType(current_plan_raw) if current_plan_raw and not isinstance(current_plan_raw, PlanType) else current_plan_raw
        except Exception:
            current_plan = None

        # Safety gate: only apply upgrades here
        # (downgrades should be handled by downgrade_subscription; checkout is gated already)
        if current_plan and not _is_upgrade(current_plan, next_plan):
            print(
                f"⚠️ pending_update_applied but next_plan is not an upgrade: {current_plan_raw}->{next_plan.value} "
                f"(user_id={user_id}); syncing status only"
            )
            kwargs = {
                "user_id": user_id,
                "subscription_status": status,
                "cancel_at_period_end": cancel_at_period_end,
                "stripe_subscription_id": subscription_id,
            }
            if event_created is not None:
                kwargs["stripe_event_ts"] = event_created
            await update_user_plan(**kwargs)
            return

        # Next billing date (after applied) – now next_plan will be cleared, so this becomes meaningful again
        next_update_at = None
        if subscription.get("current_period_end"):
            next_update_at = ensure_utc(datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc))

        # Apply the plan change immediately, clear schedule fields
        kwargs = {
            "user_id": user_id,
            "plan": next_plan,
            "next_plan": _CLEAR_FIELD,
            "plan_expires_at": _CLEAR_FIELD,          # upgrade overrides cancellation/expiration
            "cancel_at_period_end": cancel_at_period_end,
            "subscription_status": status,
            "stripe_subscription_id": subscription_id,
        }
        # Only sync next_update_at if we have it
        if next_update_at is not None:
            kwargs["next_update_at"] = next_update_at
        if event_created is not None:
            kwargs["stripe_event_ts"] = event_created

        await update_user_plan(**kwargs)
        print(
            f"✅ Applied pending_update: user_id={user_id}, plan={next_plan.value}, "
            f"next_billing={next_update_at}, cancel_at_period_end={cancel_at_period_end}, event_id={event_id}"
        )

    except Exception as e:
        print(f"❌ Failed to handle pending_update_applied webhook: {e}")
        import traceback
        traceback.print_exc()
        raise


async def handle_subscription_deleted(subscription: dict):
    """Handle subscription deletion Webhook
    
    Args:
        subscription: Stripe Subscription object
    """
    try:
        # ✅ Fix C1: Handle customer_id as dict or string (same as handle_subscription_updated)
        customer = subscription.get("customer")
        customer_id = customer.get("id") if isinstance(customer, dict) else customer
        if not customer_id:
            print(f"⚠️ Missing customer_id in subscription.deleted: {subscription.get('id')}")
            return
        
        # Find user from database using admin client
        from backend.db_supabase import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Use direct query instead of maybe_single() to avoid 406 errors
        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"⚠️ User not found with stripe_customer_id={customer_id}")
            return
        
        user_id = response.data[0]["user_id"]
        current_plan_data = response.data[0]
        plan_expires_at = current_plan_data.get("plan_expires_at")
        
        # Check if plan_expires_at is set and in the future
        if plan_expires_at:
            # ✅ Fix C2: Use _parse_dt_maybe for robust datetime parsing (consistent with handle_subscription_updated)
            plan_expires_at = _parse_dt_maybe(plan_expires_at)
            if plan_expires_at and plan_expires_at > utcnow():
                # Plan hasn't expired yet, keep current plan
                print(f"ℹ️ User {user_id} subscription deleted but plan expires at {plan_expires_at}, keeping current plan until then")
                await update_user_plan(
                    user_id=user_id,
                    subscription_status="canceled"
                )
                return
        
        # Plan has expired or no plan_expires_at -> subscription is gone, revert to START and clear schedules
        # Note: We do NOT apply next_plan here because subscription.deleted means the subscription is gone.
        # Applying next_plan (which might be an upgrade) would be semantically incorrect.
        await update_user_plan(
            user_id=user_id,
            plan=PlanType.START,
            subscription_status="canceled",
            next_plan=_CLEAR_FIELD,             # ✅ clear schedule (do not apply next_plan on deletion)
            next_update_at=_CLEAR_FIELD,        # ✅ clear effective_at/period_end (avoid stale timestamp)
            plan_expires_at=_CLEAR_FIELD,       # ✅ clear expiration marker
            cancel_at_period_end=_CLEAR_FIELD,  # ✅ clear cancel flag
            stripe_subscription_id=_CLEAR_FIELD  # ✅ clear subscription_id (subscription no longer exists)
        )
        
        print(f"⚠️ User {user_id} subscription deleted, downgraded to start plan (all schedules cleared)")
    except Exception as e:
        print(f"❌ Failed to handle subscription deletion Webhook: {e}")
        import traceback
        traceback.print_exc()
        raise


async def cancel_subscription(user_id: str) -> bool:
    """Cancel user subscription (will downgrade to start plan at period end)
    
    Args:
        user_id: User ID
    
    Returns:
        bool: Whether successful
    """
    try:
        user_plan = await get_user_plan(user_id)
        
        if not user_plan.stripe_subscription_id:
            raise ValueError("User has no active subscription")
        
        # 1) Read Stripe period end (UTC-aware)
        subscription = stripe.Subscription.retrieve(user_plan.stripe_subscription_id)
        if not getattr(subscription, "current_period_end", None):
            raise ValueError("Subscription has no current_period_end")
        
        plan_expires_at = ensure_utc(
            datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
        )
        
        # 2) Write DB state machine first (source of truth for your app logic)
        # Cancel should override any existing scheduled downgrade
        await update_user_plan(
            user_id=user_id,
            plan_expires_at=plan_expires_at,
            next_plan=PlanType.START,        # Schedule downgrade to START
            cancel_at_period_end=True,        # Mark cancel at period end
            next_update_at=_CLEAR_FIELD,      # Explicitly clear scheduled plan change trigger (override any existing downgrade)
        )
        
        # 3) Then tell Stripe to cancel at period end (no immediate cancel)
        stripe.Subscription.modify(
            user_plan.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        print(f"✅ User {user_id} subscription will cancel at period end: {plan_expires_at}")
        return True
    except Exception as e:
        print(f"❌ Failed to cancel subscription: {e}")
        import traceback
        traceback.print_exc()
        return False


async def get_subscription_info(user_id: str) -> Optional[dict]:
    """Get user subscription information
    
    Uses DB as source of truth for cancel_at_period_end.
    Stripe is only used for fields not cached in DB (status, current_period_end).
    
    Args:
        user_id: User ID
    
    Returns:
        dict: Subscription information
    """
    try:
        user_plan = await get_user_plan(user_id)
        
        if not user_plan.stripe_subscription_id:
            return None
        
        # ✅ Use DB as source of truth for cancel_at_period_end
        # DB field has default=False, so it should never be None in practice
        # Using bool() directly to expose any unexpected None values
        cancel_at_period_end = bool(user_plan.cancel_at_period_end)
        
        # ✅ Stripe only for fields not cached in DB
        subscription = stripe.Subscription.retrieve(user_plan.stripe_subscription_id)
        
        # ✅ Defensive: Handle missing current_period_end (edge cases)
        current_period_end = None
        if subscription.current_period_end:
            current_period_end = ensure_utc(
                datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
            )
        else:
            print(f"⚠️ Subscription {subscription.id} has no current_period_end")
            # Return None if critical field is missing
            return None
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,  # Not cached in DB
            "current_period_end": current_period_end,  # ✅ Using ensure_utc for consistency
            "cancel_at_period_end": cancel_at_period_end  # ✅ From DB (source of truth)
        }
    except Exception as e:
        print(f"❌ Failed to get subscription information: {e}")
        return None


# Plan hierarchy for comparison (lower index = lower tier)
PLAN_HIERARCHY = {
    PlanType.START: 0,
    PlanType.NORMAL: 1,
    PlanType.HIGH: 2,
    PlanType.ULTRA: 3,
    PlanType.PREMIUM: 4,
    PlanType.INTERNAL: 5
}


def _is_downgrade(current_plan: PlanType, target_plan: PlanType) -> bool:
    """Check if target_plan is a downgrade from current_plan
    
    Args:
        current_plan: Current plan type
        target_plan: Target plan type
    
    Returns:
        bool: True if target_plan < current_plan (downgrade)
    """
    return PLAN_HIERARCHY.get(target_plan, 0) < PLAN_HIERARCHY.get(current_plan, 0)


def _is_upgrade(current_plan: PlanType, target_plan: PlanType) -> bool:
    """Check if target_plan is an upgrade from current_plan
    
    Args:
        current_plan: Current plan type
        target_plan: Target plan type
    
    Returns:
        bool: True if target_plan > current_plan (upgrade)
    """
    return PLAN_HIERARCHY.get(target_plan, 0) > PLAN_HIERARCHY.get(current_plan, 0)


def _extract_price_id_from_pending_update(pending_update) -> Optional[str]:
    """Extract price_id from pending_update object
    
    Handles various Stripe SDK structures:
    - pending_update.items.data[0].price.id (list object with .data)
    - pending_update.items[0].price.id (direct list)
    - pending_update.items["data"][0]["price"]["id"] (dict structure)
    - pending_update.subscription_items (alternative field)
    
    Args:
        pending_update: Stripe pending_update object
    
    Returns:
        Optional[str]: price_id if found, None otherwise
    """
    try:
        # Try items field first
        if hasattr(pending_update, "items"):
            items = pending_update.items
            
            # Handle dict structure (common in some SDK versions)
            if isinstance(items, dict):
                data = items.get("data")
                if isinstance(data, list) and data:
                    price = data[0].get("price")
                    if isinstance(price, dict):
                        return price.get("id")
                    elif hasattr(price, "id"):
                        return price.id
            
            # Handle list object with .data attribute
            elif hasattr(items, "data") and items.data:
                if len(items.data) > 0 and hasattr(items.data[0], "price"):
                    price = items.data[0].price
                    return price.id if hasattr(price, "id") else None
            
            # Handle direct list
            elif isinstance(items, list) and len(items) > 0:
                if hasattr(items[0], "price"):
                    price = items[0].price
                    return price.id if hasattr(price, "id") else None
            
            # Handle iterable (generator, etc.)
            elif hasattr(items, "__iter__") and not isinstance(items, (str, bytes)):
                first_item = next(iter(items), None)
                if first_item:
                    if isinstance(first_item, dict):
                        price = first_item.get("price")
                        if isinstance(price, dict):
                            return price.get("id")
                        elif hasattr(price, "id"):
                            return price.id
                    elif hasattr(first_item, "price"):
                        price = first_item.price
                        return price.id if hasattr(price, "id") else None
        
        # Try subscription_items as alternative field
        if hasattr(pending_update, "subscription_items"):
            sub_items = pending_update.subscription_items
            if isinstance(sub_items, list) and sub_items:
                item = sub_items[0]
                if isinstance(item, dict):
                    price = item.get("price")
                    if isinstance(price, dict):
                        return price.get("id")
                    elif hasattr(price, "id"):
                        return price.id
                elif hasattr(item, "price"):
                    price = item.price
                    return price.id if hasattr(price, "id") else None
        
    except Exception as e:
        print(f"⚠️ Error extracting price_id from pending_update: {e}")
    
    return None


async def downgrade_subscription(user_id: str, target_plan: PlanType) -> bool:
    """Downgrade user subscription to a lower tier plan
    
    This function schedules a downgrade at the end of the current billing period.
    It does NOT immediately modify the Stripe subscription - the downgrade will
    be applied when the current period ends.
    
    Args:
        user_id: User ID
        target_plan: Target plan to downgrade to (must be lower tier than current plan)
    
    Returns:
        bool: Whether successful
    
    Raises:
        ValueError: If target_plan is not a downgrade, or user has no active subscription
    """
    try:
        # Get current user plan
        user_plan = await get_user_plan(user_id)
        current_plan = user_plan.plan
        
        # Validate that target_plan is a downgrade
        if not _is_downgrade(current_plan, target_plan):
            raise ValueError(
                f"Cannot downgrade: target plan '{target_plan.value}' is not lower than current plan '{current_plan.value}'"
            )
        
        # Validate subscription status - must be active or trialing
        if not user_plan.stripe_subscription_id:
            raise ValueError("User has no active subscription to downgrade")
        
        # Check subscription status (prefer DB value, but validate if needed)
        valid_statuses = {"active", "trialing"}
        if user_plan.subscription_status and user_plan.subscription_status not in valid_statuses:
            raise ValueError(
                f"Cannot downgrade: subscription status is '{user_plan.subscription_status}', "
                f"must be one of {valid_statuses}"
            )
        
        # Determine effective_at (when downgrade will take effect)
        # Priority 1: Use existing plan_expires_at if it exists and is in the future
        # This is the "source of truth" from our DB
        plan_expires_at = None
        if user_plan.plan_expires_at:
            plan_expires_at_utc = ensure_utc(user_plan.plan_expires_at)
            now = utcnow()
            if plan_expires_at_utc > now:
                # Use existing plan_expires_at if it's in the future
                plan_expires_at = plan_expires_at_utc
                print(f"🔍 Using existing plan_expires_at from DB: {plan_expires_at}")
        
        # Priority 2: If no valid plan_expires_at, get from Stripe (only when necessary)
        if plan_expires_at is None:
            try:
                subscription = stripe.Subscription.retrieve(user_plan.stripe_subscription_id)
                
                if not subscription.current_period_end:
                    raise ValueError("Subscription has no current_period_end date")
                
                plan_expires_at = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
                print(f"🔍 Retrieved current_period_end from Stripe: {plan_expires_at}")
                
                # Optional: Verify subscription status from Stripe matches our expectation
                if subscription.status not in valid_statuses:
                    raise ValueError(
                        f"Cannot downgrade: Stripe subscription status is '{subscription.status}', "
                        f"must be one of {valid_statuses}"
                    )
            except stripe.error.StripeError as e:
                print(f"⚠️ Failed to retrieve subscription from Stripe: {e}")
                raise ValueError(f"Failed to get subscription period end date: {e}")
        
        # Idempotency check: If already scheduled the same downgrade, return success
        if user_plan.next_plan == target_plan and user_plan.plan_expires_at:
            existing_expires_at = ensure_utc(user_plan.plan_expires_at)
            # If existing plan_expires_at is same or later, consider it already scheduled
            if existing_expires_at >= plan_expires_at:
                print(
                    f"✅ User {user_id} already has downgrade scheduled to {target_plan.value} "
                    f"at {existing_expires_at} (same or later than requested {plan_expires_at})"
                )
                return True
        
        # If there's a different next_plan scheduled, decide behavior:
        # Option: Allow overriding (user can change their downgrade target)
        # Alternative: Reject and require canceling existing downgrade first
        if user_plan.next_plan is not None and user_plan.next_plan != target_plan:
            print(
                f"⚠️ User {user_id} already has a different downgrade scheduled: "
                f"from {current_plan.value} to {user_plan.next_plan.value}. "
                f"Overriding to {target_plan.value}."
            )
            # Proceed with override (you can change this to raise ValueError if you prefer to reject)
        
        # Update database: set next_plan, plan_expires_at, next_update_at, cancel_at_period_end=False
        # Note: We set cancel_at_period_end=False because this is a downgrade, not a cancellation
        # The subscription will continue, but at a lower tier
        # Important: next_update_at must be set to ensure get_user_plan uses it (not plan_expires_at) 
        # to determine effective_at, preventing immediate application when plan_expires_at is NULL or past
        await update_user_plan(
            user_id=user_id,
            next_plan=target_plan,
            plan_expires_at=plan_expires_at,
            next_update_at=plan_expires_at,  # Set next_update_at to ensure proper scheduling
            cancel_at_period_end=False
        )
        
        print(
            f"✅ User {user_id} scheduled downgrade from {current_plan.value} to {target_plan.value} "
            f"at {plan_expires_at}"
        )
        return True
        
    except ValueError as e:
        print(f"❌ Validation error in downgrade_subscription: {e}")
        raise
    except Exception as e:
        print(f"❌ Failed to downgrade subscription: {e}")
        import traceback
        traceback.print_exc()
        return False
