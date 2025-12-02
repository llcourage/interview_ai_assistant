"""
Stripe 支付集成
提供订阅购买、Webhook处理等功能
"""
import os
import stripe
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from db_operations import get_user_plan, update_user_plan
from db_models import PlanType

load_dotenv()

# Stripe 配置
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Plan 对应的 Stripe Price IDs
STRIPE_PRICE_IDS = {
    PlanType.NORMAL: os.getenv("STRIPE_PRICE_NORMAL", "price_xxx"),
    PlanType.HIGH: os.getenv("STRIPE_PRICE_HIGH", "price_yyy")
}


async def create_checkout_session(user_id: str, plan: PlanType, success_url: str, cancel_url: str, user_email: Optional[str] = None) -> dict:
    """创建 Stripe Checkout Session
    
    Args:
        user_id: 用户ID
        plan: 订阅计划
        success_url: 支付成功后的跳转URL
        cancel_url: 取消支付后的跳转URL
        user_email: 用户邮箱（可选，如果提供会在 Checkout 中预填）
    
    Returns:
        dict: 包含 checkout_url 的字典
    """
    try:
        # 检查 Stripe API Key
        if not stripe.api_key or stripe.api_key == "":
            raise ValueError("STRIPE_SECRET_KEY 未配置，请在环境变量中设置")
        
        price_id = STRIPE_PRICE_IDS.get(plan)
        if not price_id or price_id in ["price_xxx", "price_yyy"]:
            raise ValueError(
                f"未找到 {plan} 对应的 Stripe Price ID。"
                f"当前值: {price_id}。"
                f"请在 Vercel 环境变量中设置 STRIPE_PRICE_{plan.value.upper()}"
            )
        
        # 获取或创建 Stripe Customer
        user_plan_data = await get_user_plan(user_id)
        
        if user_plan_data.stripe_customer_id:
            customer_id = user_plan_data.stripe_customer_id
            # 如果提供了邮箱，更新 Customer 的邮箱
            if user_email:
                try:
                    stripe.Customer.modify(
                        customer_id,
                        email=user_email
                    )
                    print(f"✅ 更新 Stripe Customer {customer_id} 的邮箱为 {user_email}")
                except Exception as e:
                    print(f"⚠️ 更新 Customer 邮箱失败: {e}")
        else:
            # 创建新客户
            customer_data = {
                "metadata": {"user_id": user_id}
            }
            if user_email:
                customer_data["email"] = user_email
            
            customer = stripe.Customer.create(**customer_data)
            customer_id = customer.id
            
            print(f"✅ 创建 Stripe Customer {customer_id}，邮箱: {user_email}")
            
            # 保存到数据库
            await update_user_plan(user_id, stripe_customer_id=customer_id)
        
        # 创建 Checkout Session
        session_data = {
            "customer": customer_id,
            "payment_method_types": ["card"],
            "line_items": [{
                "price": price_id,
                "quantity": 1,
            }],
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": True,  # 启用优惠码输入框
            "metadata": {
                "user_id": user_id,
                "plan": plan.value
            }
        }
        
        # 如果提供了邮箱，在 Checkout Session 中预填邮箱
        if user_email:
            session_data["customer_email"] = user_email
        
        session = stripe.checkout.Session.create(**session_data)
        
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        print(f"❌ 创建 Stripe Checkout Session 失败: {e}")
        raise


async def handle_checkout_completed(session: dict):
    """处理支付成功的 Webhook
    
    Args:
        session: Stripe Checkout Session 对象
    """
    try:
        user_id = session["metadata"]["user_id"]
        plan_value = session["metadata"]["plan"]
        plan = PlanType(plan_value)
        
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        
        # 更新用户 Plan
        await update_user_plan(
            user_id=user_id,
            plan=plan,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            subscription_status="active",
            plan_expires_at=None  # 订阅模式下，过期时间由 Stripe 管理
        )
        
        print(f"✅ 用户 {user_id} 已升级到 {plan.value} plan")
    except Exception as e:
        print(f"❌ 处理支付成功 Webhook 失败: {e}")
        raise


async def handle_subscription_updated(subscription: dict):
    """处理订阅更新的 Webhook
    
    Args:
        subscription: Stripe Subscription 对象
    """
    try:
        customer_id = subscription["customer"]
        status = subscription["status"]
        
        # 从数据库查找用户
        # 注意：这里需要通过 stripe_customer_id 查找用户
        # 你需要在 db_operations.py 中添加一个函数
        from db_supabase import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).maybe_single().execute()
        
        if not response.data:
            print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
            return
        
        user_id = response.data["user_id"]
        
        # 更新订阅状态
        if status == "active":
            # 订阅激活
            await update_user_plan(
                user_id=user_id,
                subscription_status="active"
            )
            print(f"✅ 用户 {user_id} 订阅已激活")
        elif status in ["canceled", "past_due", "unpaid"]:
            # 订阅取消或逾期，降级为 normal
            await update_user_plan(
                user_id=user_id,
                plan=PlanType.NORMAL,
                subscription_status=status
            )
            print(f"⚠️ 用户 {user_id} 订阅已取消/逾期，降级为 normal")
    except Exception as e:
        print(f"❌ 处理订阅更新 Webhook 失败: {e}")
        raise


async def handle_subscription_deleted(subscription: dict):
    """处理订阅删除的 Webhook
    
    Args:
        subscription: Stripe Subscription 对象
    """
    try:
        customer_id = subscription["customer"]
        
        # 从数据库查找用户
        from db_supabase import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("user_plans").select("*").eq("stripe_customer_id", customer_id).maybe_single().execute()
        
        if not response.data:
            print(f"⚠️ 未找到 stripe_customer_id={customer_id} 的用户")
            return
        
        user_id = response.data["user_id"]
        
        # 降级为 normal
        await update_user_plan(
            user_id=user_id,
            plan=PlanType.NORMAL,
            subscription_status="canceled"
        )
        
        print(f"⚠️ 用户 {user_id} 订阅已删除，降级为 normal")
    except Exception as e:
        print(f"❌ 处理订阅删除 Webhook 失败: {e}")
        raise


async def cancel_subscription(user_id: str) -> bool:
    """取消用户订阅
    
    Args:
        user_id: 用户ID
    
    Returns:
        bool: 是否成功
    """
    try:
        user_plan = await get_user_plan(user_id)
        
        if not user_plan.stripe_subscription_id:
            raise ValueError("用户没有活跃的订阅")
        
        # 取消订阅（在周期结束时）
        stripe.Subscription.modify(
            user_plan.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        print(f"✅ 用户 {user_id} 的订阅将在周期结束时取消")
        return True
    except Exception as e:
        print(f"❌ 取消订阅失败: {e}")
        return False


async def get_subscription_info(user_id: str) -> Optional[dict]:
    """获取用户订阅信息
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 订阅信息
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
        print(f"❌ 获取订阅信息失败: {e}")
        return None

