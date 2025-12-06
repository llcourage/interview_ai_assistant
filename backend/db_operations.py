"""
数据库操作
提供用户Plan、API Keys、Usage的CRUD操作
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from backend.db_supabase import get_supabase
from backend.db_models import UserPlan, UsageLog, UsageQuota, PlanType, PLAN_LIMITS

# 已移除加密相关代码 - 所有用户使用服务器 API Key


def normalize_plan_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """兼容旧数据：将 'starter' plan 转换为 'normal'"""
    if isinstance(data, dict) and data.get('plan') == 'starter':
        data = data.copy()  # 创建副本，避免修改原始数据
        data['plan'] = 'normal'
    return data


# ========== User Plan Operations ==========

async def get_user_plan(user_id: str) -> UserPlan:
    """获取用户的Plan"""
    try:
        supabase = get_supabase()
        # 使用 maybe_single() 而不是 single()，避免在没有记录时抛出异常
        response = supabase.table("user_plans").select("*").eq("user_id", user_id).maybe_single().execute()
        
        if response.data:
            plan_data = normalize_plan_data(response.data)
            return UserPlan(**plan_data)
        else:
            # 如果没有记录，先尝试直接查询（不使用 maybe_single）
            direct_response = supabase.table("user_plans").select("*").eq("user_id", user_id).execute()
            
            if direct_response.data and len(direct_response.data) > 0:
                plan_data = normalize_plan_data(direct_response.data[0])
                return UserPlan(**plan_data)
            
            # If no plan record found, create default NORMAL plan
            print(f"User {user_id} has no plan record, creating default NORMAL plan")
            return await create_user_plan(user_id)
    except Exception as e:
        print(f"⚠️ 获取用户Plan失败: {e}")
        # 如果创建失败，尝试返回内存中的对象（但这不是持久化的）
        try:
            return await create_user_plan(user_id)
        except Exception as create_error:
            print(f"❌ 创建用户Plan也失败: {create_error}")
            # 最后返回一个临时对象（不推荐，但至少不会崩溃）
            return UserPlan(
                user_id=user_id,
                plan=PlanType.NORMAL,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )


async def create_user_plan(user_id: str, plan: PlanType = PlanType.NORMAL) -> UserPlan:
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
        
        # 防御性检查：确保 response 和 response.data 都存在
        if response is None:
            print(f"❌ Supabase insert 返回 None")
            raise Exception("创建Plan失败：数据库操作返回空响应")
        
        if not hasattr(response, 'data') or not response.data:
            print(f"❌ Supabase insert 返回的 response.data 为空: {response}")
            raise Exception("创建Plan失败：数据库操作未返回数据")
        
        # 确保 data 是列表且不为空
        if isinstance(response.data, list) and len(response.data) > 0:
            plan_data = normalize_plan_data(response.data[0])
            return UserPlan(**plan_data)
        elif not isinstance(response.data, list) and response.data:
            plan_data = normalize_plan_data(response.data)
            return UserPlan(**plan_data)
        else:
            print(f"❌ Supabase insert 返回的数据格式异常: {response.data}")
            raise Exception("创建Plan失败：返回的数据格式不正确")
    except Exception as e:
        print(f"❌ 创建用户Plan失败: {e}")
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
    """更新用户Plan（如果记录不存在则创建）- 使用 upsert 避免 204 错误
    
    如果从 start plan 升级到其他 plan，会自动重置 quota
    """
    try:
        from postgrest.exceptions import APIError
        
        supabase = get_supabase()
        
        # 如果 plan 要更新，检查是否需要重置 quota（从 start 升级到其他 plan）
        should_reset_quota = False
        old_plan = None
        if plan is not None:
            # 获取旧的 plan
            try:
                old_plan_response = supabase.table("user_plans").select("plan").eq("user_id", user_id).maybe_single().execute()
                if old_plan_response.data:
                    old_plan_value = old_plan_response.data.get("plan")
                    if old_plan_value:
                        old_plan = PlanType(old_plan_value)
                        # 如果从 start plan 升级到 normal/high plan，需要重置 quota
                        if old_plan == PlanType.START and plan != PlanType.START:
                            should_reset_quota = True
                            print(f"🔄 用户 {user_id} 从 start plan 升级到 {plan.value} plan，将重置 quota")
            except Exception as e:
                print(f"⚠️ 检查旧 plan 失败（可能是新用户）: {e}")
        
        # 构建数据字典
        now = datetime.now()
        data = {
            "user_id": user_id,
            "updated_at": now.isoformat()
        }
        
        # 只有非 None 的值才添加到 data 中（避免覆盖已有值为 NULL）
        # 注意：如果是新记录创建（通过 webhook），plan 总是会被传入
        # 如果是部分更新（plan 为 None），则只更新其他字段
        if plan is not None:
            data["plan"] = plan.value
        
        # 这些字段只在有值时才更新
        if stripe_customer_id is not None:
            data["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id is not None:
            data["stripe_subscription_id"] = stripe_subscription_id
        if subscription_status is not None:
            data["subscription_status"] = subscription_status
        if plan_expires_at is not None:
            data["plan_expires_at"] = plan_expires_at.isoformat()
        
        # 使用 upsert，以 user_id 为唯一键
        # 如果记录不存在则插入，存在则更新
        try:
            # 尝试标准 upsert
            response = supabase.table("user_plans").upsert(data).execute()
            
        except Exception as upsert_error:
            # 如果标准 upsert 失败，尝试指定 on_conflict
            try:
                response = supabase.table("user_plans").upsert(
                    data,
                    on_conflict="user_id"
                ).execute()
            except Exception as e2:
                print(f"Upsert failed: {e2}")
                raise
        
        # 防御性检查：确保 response 和 response.data 都存在
        if response is None:
            print(f"Supabase upsert returned None")
            raise Exception("Update plan failed: Database operation returned empty response")
        
        if not hasattr(response, 'data') or not response.data:
            print(f"Supabase upsert returned empty response.data: {response}")
            raise Exception("Update plan failed: Database operation did not return data")
        
        # 处理返回的数据
        if isinstance(response.data, list) and len(response.data) > 0:
            plan_data = normalize_plan_data(response.data[0])
            result = UserPlan(**plan_data)
        elif not isinstance(response.data, list) and response.data:
            plan_data = normalize_plan_data(response.data)
            result = UserPlan(**plan_data)
        else:
            raise Exception("Update plan failed: Unexpected response format")
        
        # 如果需要重置 quota（从 start 升级到其他 plan）
        if should_reset_quota and plan is not None:
            try:
                now = datetime.now()
                quota_update_data = {
                    "monthly_tokens_used": 0,
                    "quota_reset_date": now.isoformat(),
                    "plan": plan.value,  # 同时更新 quota 中的 plan
                    "updated_at": now.isoformat()
                }
                quota_response = supabase.table("usage_quotas").update(quota_update_data).eq("user_id", user_id).execute()
                if quota_response.data:
                    print(f"✅ 已重置用户 {user_id} 的 quota（从 start plan 升级到 {plan.value}）")
                else:
                    # Quota 记录可能不存在，尝试创建
                    try:
                        await create_user_quota(user_id)
                        print(f"✅ 已创建用户 {user_id} 的新 quota 记录")
                    except Exception as create_error:
                        print(f"⚠️ 创建 quota 记录失败: {create_error}")
            except Exception as quota_error:
                print(f"⚠️ 重置 quota 时出错: {quota_error}")
                # 不抛出异常，因为 plan 更新已经成功了
        
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
        from backend.db_models import MODEL_PRICING
        
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
        # 使用 maybe_single() 而不是 single()，避免在没有记录时抛出异常
        response = supabase.table("usage_quotas").select("*").eq("user_id", user_id).maybe_single().execute()
        
        if response and response.data:
            # 保存原始 plan 值，用于检查是否需要更新数据库
            original_plan = response.data.get('plan')
            
            quota_data = normalize_plan_data(response.data)
            # 确保 monthly_tokens_used 字段存在（兼容旧数据）
            if 'monthly_tokens_used' not in quota_data:
                quota_data['monthly_tokens_used'] = 0
            quota = UsageQuota(**quota_data)
            
            # 如果从 'starter' 转换而来，更新数据库
            if original_plan == 'starter':
                try:
                    supabase = get_supabase()
                    supabase.table("usage_quotas").update({"plan": "normal"}).eq("user_id", user_id).execute()
                    print(f"✅ 已将用户 {user_id} 的 quota plan 从 'starter' 更新为 'normal'")
                except Exception as update_error:
                    print(f"⚠️ 更新 quota plan 失败: {update_error}")
            
            # 检查是否需要重置配额（按自然月重置）
            # 对于终身配额（start plan），跳过重置
            user_plan = await get_user_plan(user_id)
            limits = PLAN_LIMITS.get(user_plan.plan, {})
            is_lifetime = limits.get("is_lifetime", False)
            
            now = datetime.now()
            should_reset_monthly = False
            
            # 终身配额不重置
            if not is_lifetime:
                if quota.quota_reset_date:
                    reset_date = quota.quota_reset_date
                    if isinstance(reset_date, str):
                        reset_date = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
                    
                    # quota_reset_date 是"上次重置时间"，如果当前年月 ≠ 上次重置的年月，则需要重置
                    reset_date_no_tz = reset_date.replace(tzinfo=None) if reset_date.tzinfo else reset_date
                    should_reset_monthly = (now.year != reset_date_no_tz.year) or (now.month != reset_date_no_tz.month)
                else:
                    # 如果没有重置日期，视为需要重置
                    should_reset_monthly = True
            
            if should_reset_monthly:
                # 直接在这里重置，避免调用 reset_user_quota 造成递归
                update_data = {
                    "monthly_tokens_used": 0,
                    "quota_reset_date": now.isoformat(),  # 设置为当前时间（上次重置时间）
                    "updated_at": now.isoformat()
                }
                
                supabase = get_supabase()
                response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
                
                if response.data:
                    quota_data = normalize_plan_data(response.data[0])
                    quota = UsageQuota(**quota_data)
                    print(f"📅 重置用户 {user_id} 的月度 token 配额（自然月重置）")
                else:
                    # 如果更新失败，至少更新内存中的对象
                    quota.monthly_tokens_used = 0
                    quota.quota_reset_date = now
            
            return quota
        else:
            # 如果没有记录，创建新配额
            print(f"📝 用户 {user_id} 没有配额记录，创建新配额")
            return await create_user_quota(user_id)
    except Exception as e:
        print(f"⚠️ 获取用户配额失败: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认配额
        try:
            user_plan = await get_user_plan(user_id)
            limits = PLAN_LIMITS[user_plan.plan]
            
            now = datetime.now()
            # quota_reset_date 是"上次重置时间"，设置为当前时间
            return UsageQuota(
                user_id=user_id,
                plan=user_plan.plan,
                monthly_tokens_used=0,
                quota_reset_date=now,  # 上次重置时间 = 当前时间
                created_at=now,
                updated_at=now
            )
        except Exception as fallback_error:
            print(f"❌ 创建默认配额也失败: {fallback_error}")
            # 最后返回一个基本的配额对象
            # Fallback to NORMAL plan limits
            now = datetime.now()
            # quota_reset_date 是"上次重置时间"，设置为当前时间
            return UsageQuota(
                user_id=user_id,
                plan=PlanType.NORMAL,
                monthly_tokens_used=0,
                quota_reset_date=now,  # 上次重置时间 = 当前时间
                created_at=now,
                updated_at=now
            )


async def create_user_quota(user_id: str) -> UsageQuota:
    """创建用户配额"""
    try:
        supabase = get_supabase()
        
        user_plan = await get_user_plan(user_id)
        
        now = datetime.now()
        # quota_reset_date 是"上次重置时间"，设置为当前时间
        quota_data = {
            "user_id": user_id,
            "plan": user_plan.plan.value,
            "monthly_tokens_used": 0,
            "quota_reset_date": now.isoformat(),  # 上次重置时间 = 当前时间
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        response = supabase.table("usage_quotas").insert(quota_data).execute()
        
        if response.data:
            quota_data = normalize_plan_data(response.data[0])
            return UsageQuota(**quota_data)
        else:
            raise Exception("创建配额失败")
    except Exception as e:
        print(f"❌ 创建用户配额失败: {e}")
        raise


async def increment_user_quota(user_id: str, tokens_used: int = 0) -> UsageQuota:
    """增加用户 token 使用量
    
    Args:
        user_id: 用户ID
        tokens_used: 本次使用的 token 数量（必须提供，默认为0）
    """
    try:
        quota = await get_user_quota(user_id)
        
        supabase = get_supabase()
        
        update_data = {
            "updated_at": datetime.now().isoformat()
        }
        
        # 添加 token 使用量到 monthly_tokens_used
        if tokens_used > 0:
            current_tokens = getattr(quota, 'monthly_tokens_used', 0)
            update_data["monthly_tokens_used"] = current_tokens + tokens_used
        
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
    """重置用户配额（按自然月重置 monthly_tokens_used）
    
    注意：quota_reset_date 定义为"上次重置时间"（last_reset_at），不是"下次重置时间"
    是否重置的判断：当前年月 ≠ quota_reset_date 的年月 → 重置
    """
    try:
        supabase = get_supabase()
        
        # 直接查询数据库，避免调用 get_user_quota 造成递归
        response = supabase.table("usage_quotas").select("*").eq("user_id", user_id).maybe_single().execute()
        
        now = datetime.now()
        
        if not response or not response.data:
            # 没有记录就创建一条
            user_plan = await get_user_plan(user_id)
            quota_data = {
                "user_id": user_id,
                "plan": user_plan.plan.value,
                "monthly_tokens_used": 0,
                "quota_reset_date": now.isoformat(),  # 上次重置时间 = 当前时间
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            insert_response = supabase.table("usage_quotas").insert(quota_data).execute()
            if insert_response.data:
                quota_data = normalize_plan_data(insert_response.data[0])
                return UsageQuota(**quota_data)
            else:
                raise Exception("创建配额失败")
        
        # 解析现有配额
        quota_raw = normalize_plan_data(response.data[0])
        quota = UsageQuota(**quota_raw)
        
        # 检查是否需要每月重置：只按自然月重置
        # quota_reset_date 是"上次重置时间"，如果当前年月 ≠ 上次重置的年月，则需要重置
        should_reset_monthly = False
        
        if quota.quota_reset_date:
            reset_date = quota.quota_reset_date
            if isinstance(reset_date, str):
                reset_date = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
            
            reset_date_no_tz = reset_date.replace(tzinfo=None) if reset_date.tzinfo else reset_date
            should_reset_monthly = (now.year != reset_date_no_tz.year) or (now.month != reset_date_no_tz.month)
        else:
            # 如果没有重置日期，视为需要重置
            should_reset_monthly = True
        
        update_data = {
            "updated_at": now.isoformat()
        }
        
        # 如果需要重置月度配额
        if should_reset_monthly:
            update_data["monthly_tokens_used"] = 0
            update_data["quota_reset_date"] = now.isoformat()  # 更新为当前时间（上次重置时间）
            print(f"📅 重置用户 {user_id} 的月度 token 配额（自然月重置）")
        
        update_response = supabase.table("usage_quotas").update(update_data).eq("user_id", user_id).execute()
        
        if update_response.data:
            quota_data = normalize_plan_data(update_response.data[0])
            return UsageQuota(**quota_data)
        else:
            raise Exception("重置配额失败")
    except Exception as e:
        print(f"❌ 重置用户配额失败: {e}")
        raise


async def check_rate_limit(user_id: str, estimated_tokens: int = 0) -> tuple[bool, str]:
    """检查用户是否超过 token 配额限制
    
    Args:
        user_id: 用户ID
        estimated_tokens: 预估的本次请求将使用的 tokens 数量（可选，用于提前检查）
    
    Returns:
        (bool, str): (是否允许, 错误信息)
    """
    try:
        user_plan = await get_user_plan(user_id)
        quota = await get_user_quota(user_id)
        limits = PLAN_LIMITS[user_plan.plan]
        
        # 检查 token 限制（考虑预估的 tokens）
        # 支持两种配额类型：月度配额（monthly_token_limit）和终身配额（lifetime_token_limit）
        monthly_token_limit = limits.get("monthly_token_limit")
        lifetime_token_limit = limits.get("lifetime_token_limit")
        is_lifetime = limits.get("is_lifetime", False)
        
        monthly_tokens_used = getattr(quota, 'monthly_tokens_used', 0)
        
        # 检查终身配额（start plan）
        if is_lifetime and lifetime_token_limit is not None:
            if monthly_tokens_used + estimated_tokens > lifetime_token_limit:
                remaining = lifetime_token_limit - monthly_tokens_used
                if remaining <= 0:
                    return False, f"终身 tokens 已用完：{monthly_tokens_used:,}/{lifetime_token_limit:,}。请升级Plan。"
                else:
                    return False, f"终身 tokens 配额不足：已使用 {monthly_tokens_used:,}/{lifetime_token_limit:,}，剩余 {remaining:,}，但预估需要 {estimated_tokens:,}。请升级Plan。"
        
        # 检查月度配额（normal/high plan）
        if monthly_token_limit is not None:
            # 检查当前已使用的 tokens 加上预估的 tokens 是否会超过限制
            if monthly_tokens_used + estimated_tokens > monthly_token_limit:
                remaining = monthly_token_limit - monthly_tokens_used
                if remaining <= 0:
                    return False, f"本月 tokens 已用完：{monthly_tokens_used:,}/{monthly_token_limit:,}。请下月再试或升级Plan。"
                else:
                    return False, f"本月 tokens 配额不足：已使用 {monthly_tokens_used:,}/{monthly_token_limit:,}，剩余 {remaining:,}，但预估需要 {estimated_tokens:,}。请下月再试或升级Plan。"
        
        return True, ""
    except Exception as e:
        print(f"Check rate limit failed: {e}")
        import traceback
        traceback.print_exc()
        # 出错时允许请求，避免阻塞
        return True, ""

