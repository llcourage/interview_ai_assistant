"""
Stripe payment integration
Provides subscription purchase, Webhook handling and other functions
"""
import os
import stripe
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from backend.db_operations import get_user_plan, update_user_plan
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
        metadata = session.get("metadata", {})
        if not metadata:
            print(f"Warning: Checkout session {session_id} has no metadata, skipping")
            return
        
        user_id = metadata.get("user_id")
        plan_value = metadata.get("plan")
        
        if not user_id or not plan_value:
            print(f"Warning: Checkout session {session_id} missing user_id or plan in metadata")
            return
        
        # Normalize 'starter' to 'start' before converting to PlanType
        if plan_value == 'starter':
            plan_value = 'start'
        plan = PlanType(plan_value)
        
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        
        # Update user Plan
        await update_user_plan(
            user_id=user_id,
            plan=plan,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            subscription_status="active",
            plan_expires_at=None  # In subscription mode, expiration time is managed by Stripe
        )
        
        print(f"Success: User {user_id} upgraded to {plan.value} plan")
    except Exception as e:
        error_msg = f"Failed to process checkout completed webhook: {e}"
        print(f"Error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise


async def handle_subscription_updated(subscription: dict):
    """Handle subscription update Webhook
    
    Args:
        subscription: Stripe Subscription object
    """
    try:
        customer_id = subscription["customer"]
        status = subscription["status"]
        subscription_id = subscription.get("id")
        
        print(f"🔍 Processing subscription update: subscription_id={subscription_id}, customer_id={customer_id}, status={status}")
        
        # Find user from database using admin client (bypass RLS)
        from backend.db_supabase import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Use direct query instead of maybe_single() to avoid 406 errors
        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"⚠️ User not found with stripe_customer_id={customer_id}")
            return
        
        user_id = response.data[0]["user_id"]
        current_plan = response.data[0].get("plan")
        print(f"🔍 Found user: user_id={user_id}, current_plan={current_plan}")
        
        # Update subscription status
        if status == "active":
            # Subscription activated - need to get plan from subscription price_id
            plan = None
            price_id = None
            
            # Get price_id from subscription items
            items = subscription.get("items", {}).get("data", [])
            if items and len(items) > 0:
                price_id = items[0].get("price", {}).get("id")
                
                if price_id:
                    # Map price_id to plan
                    # Reverse lookup: find plan by price_id
                    for plan_type, plan_price_id in STRIPE_PRICE_IDS.items():
                        if plan_price_id == price_id:
                            plan = plan_type
                            break
                    
                    if plan:
                        print(f"🔍 Subscription {subscription_id}: price_id={price_id}, mapped to plan={plan.value}")
                    else:
                        print(f"⚠️ Unknown price_id: {price_id} for subscription {subscription_id}")
                        print(f"   Available price_ids: {list(STRIPE_PRICE_IDS.values())}")
                else:
                    print(f"⚠️ No price_id found in subscription {subscription_id} items")
            else:
                print(f"⚠️ No items found in subscription {subscription_id}")
            
            # Update user plan with correct plan type
            if plan:
                await update_user_plan(
                    user_id=user_id,
                    plan=plan,
                    subscription_status="active",
                    stripe_subscription_id=subscription_id
                )
                print(f"✅ User {user_id} subscription activated, plan updated from '{current_plan}' to '{plan.value}'")
            else:
                # If can't determine plan, log warning but still update status
                print(f"⚠️ Cannot determine plan from price_id, keeping current plan '{current_plan}'")
                await update_user_plan(
                    user_id=user_id,
                    subscription_status="active",
                    stripe_subscription_id=subscription_id
                )
                print(f"✅ User {user_id} subscription activated (plan not updated, price_id={price_id} not found in mapping)")
                
        elif status in ["canceled", "past_due", "unpaid"]:
            # Subscription canceled or overdue, downgrade to start plan
            await update_user_plan(
                user_id=user_id,
                plan=PlanType.START,
                subscription_status=status
            )
            print(f"⚠️ User {user_id} subscription canceled/overdue, downgraded to start plan")
        else:
            # Other statuses - just update status, don't change plan
            await update_user_plan(
                user_id=user_id,
                subscription_status=status
            )
            print(f"ℹ️ User {user_id} subscription status updated to {status}")
            
    except Exception as e:
        print(f"❌ Failed to handle subscription update Webhook: {e}")
        import traceback
        traceback.print_exc()
        raise


async def handle_subscription_deleted(subscription: dict):
    """Handle subscription deletion Webhook
    
    Args:
        subscription: Stripe Subscription object
    """
    try:
        customer_id = subscription["customer"]
        
        # Find user from database
        from backend.db_supabase import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).maybe_single().execute()
        
        if not response.data:
            print(f"⚠️ User not found with stripe_customer_id={customer_id}")
            return
        
        user_id = response.data["user_id"]
        
        # Downgrade to start plan
        await update_user_plan(
            user_id=user_id,
            plan=PlanType.START,
            subscription_status="canceled"
        )
        
        print(f"⚠️ User {user_id} subscription deleted, downgraded to start plan")
    except Exception as e:
        print(f"❌ Failed to handle subscription deletion Webhook: {e}")
        raise


async def cancel_subscription(user_id: str) -> bool:
    """Cancel user subscription
    
    Args:
        user_id: User ID
    
    Returns:
        bool: Whether successful
    """
    try:
        user_plan = await get_user_plan(user_id)
        
        if not user_plan.stripe_subscription_id:
            raise ValueError("User has no active subscription")
        
        # Cancel subscription (at period end)
        stripe.Subscription.modify(
            user_plan.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        print(f"✅ User {user_id} subscription will be cancelled at period end")
        return True
    except Exception as e:
        print(f"❌ Failed to cancel subscription: {e}")
        return False


async def get_subscription_info(user_id: str) -> Optional[dict]:
    """Get user subscription information
    
    Args:
        user_id: User ID
    
    Returns:
        dict: Subscription information
    """
    try:
        user_plan = await get_user_plan(user_id)
        
        if not user_plan.stripe_subscription_id:
            return None
        
        subscription = stripe.Subscription.retrieve(user_plan.stripe_subscription_id)
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
            "cancel_at_period_end": subscription.cancel_at_period_end
        }
    except Exception as e:
        print(f"❌ Failed to get subscription information: {e}")
        return None

