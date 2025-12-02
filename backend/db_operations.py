"""
数据库操作
提供用户Plan、API Keys、Usage的CRUD操作
"""
import os
from typing import Optional
from datetime import datetime, timedelta
from db_supabase import get_supabase
from db_models import UserPlan, UsageLog, UsageQuota, PlanType, PLAN_LIMITS

# 已移除加密相关代码 - 所有用户使用服务器 API Key


# ========== User Plan Operations ==========

async def get_user_plan(user_id: str) -> UserPlan:
    """获取用户的Plan"""
    try:
        supabase = get_supabase()
        response = supabase.table("user_plans").select("*").eq("user_id", user_id).single().execute()
        
        if response.data:
            return UserPlan(**response.data)
        else:
            # 如果没有记录，创建默认的 starter plan
            return await create_user_plan(user_id)
    except Exception as e:
        print(f"⚠️ 获取用户Plan失败: {e}")
        # 返回默认的 starter plan
        return UserPlan(
            user_id=user_id,
            plan=PlanType.STARTER,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )


async def create_user_plan(user_id: str, plan: PlanType = PlanType.STARTER) -> UserPlan:
    """创建用户Plan"""
    try:
        supabase = get_supabase()
        now = datetime.now()
        
        plan_data = {
            "user_id": user_id,
            "plan": plan.value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        response = supabase.table("user_plans").insert(plan_data).execute()
        
        if response.data:
            return UserPlan(**response.data[0])
        else:
            raise Exception("创建Plan失败")
    except Exception as e:
        print(f"❌ 创建用户Plan失败: {e}")
        raise


async def update_user_plan(
    user_id: str,
    plan: Optional[PlanType] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    subscription_status: Optional[str] = None,
    plan_expires_at: Optional[datetime] = None
) -> UserPlan:
    """更新用户Plan"""
    try:
        supabase = get_supabase()
        
        update_data = {
            "updated_at": datetime.now().isoformat()
        }
        
        if plan is not None:
            update_data["plan"] = plan.value
        if stripe_customer_id is not None:
            update_data["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id is not None:
            update_data["stripe_subscription_id"] = stripe_subscription_id
        if subscription_status is not None:
            update_data["subscription_status"] = subscription_status
        if plan_expires_at is not None:
            update_data["plan_expires_at"] = plan_expires_at.isoformat()
        
        response = supabase.table("user_plans").update(update_data).eq("user_id", user_id).execute()
        
        if response.data:
            return UserPlan(**response.data[0])
        else:
            raise Exception("更新Plan失败")
    except Exception as e:
        print(f"❌ 更新用户Plan失败: {e}")
        raise


# ========== User API Key Operations 已移除 ==========
# 所有用户都使用服务器的 API Key，不需要存储用户的 Key


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
    """记录API使用"""
    try:
        from db_models import MODEL_PRICING
        
        # 计算成本
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
            raise Exception("记录Usage失败")
    except Exception as e:
        print(f"❌ 记录Usage失败: {e}")
        raise


# ========== Usage Quota Management ==========

async def get_user_quota(user_id: str) -> UsageQuota:
    """获取用户配额"""
    try:
        supabase = get_supabase()
        response = supabase.table("usage_quotas").select("*").eq("user_id", user_id).single().execute()
        
        if response.data:
            quota = UsageQuota(**response.data)
            
            # 检查是否需要重置配额
            now = datetime.now()
            if quota.quota_reset_date < now:
                # 重置配额
                quota = await reset_user_quota(user_id)
            
            return quota
        else:
            # 创建新配额
            return await create_user_quota(user_id)
    except Exception as e:
        print(f"⚠️ 获取用户配额失败: {e}")
        # 返回默认配额
        user_plan = await get_user_plan(user_id)
        limits = PLAN_LIMITS[user_plan.plan]
        
        return UsageQuota(
            user_id=user_id,
            plan=user_plan.plan,
            daily_requests=0,
            monthly_requests=0,
            daily_limit=limits["daily_limit"],
            monthly_limit=limits["monthly_limit"],
            quota_reset_date=datetime.now() + timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )


async def create_user_quota(user_id: str) -> UsageQuota:
    """创建用户配额"""
    try:
        supabase = get_supabase()
        
        user_plan = await get_user_plan(user_id)
        limits = PLAN_LIMITS[user_plan.plan]
        
        now = datetime.now()
        next_reset = now + timedelta(days=1)
        
        quota_data = {
            "user_id": user_id,
            "plan": user_plan.plan.value,
            "daily_requests": 0,
            "monthly_requests": 0,
            "daily_limit": limits["daily_limit"],
            "monthly_limit": limits["monthly_limit"],
            "quota_reset_date": next_reset.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        response = supabase.table("usage_quotas").insert(quota_data).execute()
        
        if response.data:
            return UsageQuota(**response.data[0])
        else:
            raise Exception("创建配额失败")
    except Exception as e:
        print(f"❌ 创建用户配额失败: {e}")
        raise


async def increment_user_quota(user_id: str) -> UsageQuota:
    """增加用户配额使用次数"""
    try:
        quota = await get_user_quota(user_id)
        
        supabase = get_supabase()
        
        update_data = {
            "daily_requests": quota.daily_requests + 1,
            "monthly_requests": quota.monthly_requests + 1,
            "last_request_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
        
        if response.data:
            return UsageQuota(**response.data[0])
        else:
            raise Exception("更新配额失败")
    except Exception as e:
        print(f"❌ 增加用户配额失败: {e}")
        raise


async def reset_user_quota(user_id: str) -> UsageQuota:
    """重置用户配额（每日重置）"""
    try:
        supabase = get_supabase()
        
        now = datetime.now()
        next_reset = now + timedelta(days=1)
        
        update_data = {
            "daily_requests": 0,
            "quota_reset_date": next_reset.isoformat(),
            "updated_at": now.isoformat()
        }
        
        response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
        
        if response.data:
            return UsageQuota(**response.data[0])
        else:
            raise Exception("重置配额失败")
    except Exception as e:
        print(f"❌ 重置用户配额失败: {e}")
        raise


async def check_rate_limit(user_id: str) -> tuple[bool, str]:
    """检查用户是否超过限流
    
    Returns:
        (bool, str): (是否允许, 错误信息)
    """
    try:
        quota = await get_user_quota(user_id)
        
        # High plan 无限制
        if quota.daily_limit == -1:
            return True, ""
        
        # 检查每日限制
        if quota.daily_requests >= quota.daily_limit:
            return False, f"已达到每日请求限制 ({quota.daily_limit} 次)。请明天再试或升级Plan。"
        
        # 检查每月限制
        if quota.monthly_requests >= quota.monthly_limit:
            return False, f"已达到每月请求限制 ({quota.monthly_limit} 次)。请下月再试或升级Plan。"
        
        return True, ""
    except Exception as e:
        print(f"❌ 检查限流失败: {e}")
        # 出错时允许请求，避免阻塞
        return True, ""

