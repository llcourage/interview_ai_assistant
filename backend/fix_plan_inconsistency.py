"""
修复 plan 数据不一致的脚本
从 Stripe 查询订阅的 price_id，然后更新数据库中的 plan
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import stripe
from backend.db_supabase import get_supabase_admin
from backend.db_operations import update_user_plan
from backend.db_models import PlanType

# 加载环境变量
backend_dir = Path(__file__).parent.resolve()
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

# 配置 Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Stripe Price IDs 到 Plan 的映射（反向）
STRIPE_PRICE_TO_PLAN = {
    os.getenv("STRIPE_PRICE_NORMAL", "price_xxx"): PlanType.NORMAL,
    os.getenv("STRIPE_PRICE_HIGH", "price_yyy"): PlanType.HIGH,
    os.getenv("STRIPE_PRICE_ULTRA", "price_zzz"): PlanType.ULTRA,
    os.getenv("STRIPE_PRICE_PREMIUM", "price_premium"): PlanType.PREMIUM,
}


async def fix_plan_inconsistency():
    """修复 plan 数据不一致的问题"""
    if not stripe.api_key:
        print("❌ STRIPE_SECRET_KEY not configured")
        return
    
    supabase = get_supabase_admin()
    
    # 查找所有有活跃订阅但 plan 是 'start' 的用户
    response = supabase.table("user_plans").select("*").eq("subscription_status", "active").eq("plan", "start").execute()
    
    if not response.data:
        print("✅ No inconsistent data found")
        return
    
    print(f"🔍 Found {len(response.data)} users with inconsistent plan data")
    
    for user_plan in response.data:
        user_id = user_plan["user_id"]
        subscription_id = user_plan.get("stripe_subscription_id")
        
        if not subscription_id:
            print(f"⚠️ User {user_id} has active subscription but no stripe_subscription_id")
            continue
        
        try:
            # 从 Stripe 查询订阅信息
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # 获取 price_id
            if not subscription.items or not subscription.items.data:
                print(f"⚠️ Subscription {subscription_id} has no items")
                continue
            
            price_id = subscription.items.data[0].price.id
            print(f"🔍 User {user_id}: subscription_id={subscription_id}, price_id={price_id}")
            
            # 根据 price_id 映射到 plan
            plan = STRIPE_PRICE_TO_PLAN.get(price_id)
            
            if not plan:
                print(f"⚠️ Unknown price_id: {price_id} for user {user_id}")
                print(f"   Available price_ids: {list(STRIPE_PRICE_TO_PLAN.keys())}")
                continue
            
            # 更新数据库
            await update_user_plan(
                user_id=user_id,
                plan=plan,
                subscription_status="active"
            )
            
            print(f"✅ Updated user {user_id} plan from 'start' to '{plan.value}'")
            
        except stripe.error.StripeError as e:
            print(f"❌ Stripe error for subscription {subscription_id}: {e}")
        except Exception as e:
            print(f"❌ Error processing user {user_id}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(fix_plan_inconsistency())

