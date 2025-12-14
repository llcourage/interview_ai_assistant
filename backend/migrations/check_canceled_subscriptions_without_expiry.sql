-- ========================================
-- 检查已取消订阅但 plan_expires_at 为 null 的用户
-- ========================================

-- 查找有 stripe_subscription_id 但 subscription_status 不是 'active' 的用户
-- 这些用户可能已经取消了订阅，但 plan_expires_at 没有被设置
SELECT 
    user_id,
    plan,
    stripe_customer_id,
    stripe_subscription_id,
    subscription_status,
    plan_expires_at,
    created_at,
    updated_at,
    CASE 
        WHEN subscription_status IN ('canceled', 'past_due', 'unpaid') 
             AND plan != 'start' 
             AND plan_expires_at IS NULL 
        THEN '⚠️ 已取消订阅但 plan_expires_at 为 null，应该已降级到 start'
        WHEN subscription_status = 'active' 
             AND plan_expires_at IS NOT NULL 
        THEN 'ℹ️ 有活跃订阅但 plan_expires_at 已设置（可能正在取消中）'
        WHEN subscription_status = 'active' 
             AND plan_expires_at IS NULL 
        THEN '✅ 正常：活跃订阅，无过期时间'
        ELSE '其他状态'
    END as status_check
FROM user_plans
WHERE stripe_subscription_id IS NOT NULL
ORDER BY 
    CASE 
        WHEN subscription_status IN ('canceled', 'past_due', 'unpaid') 
             AND plan != 'start' 
             AND plan_expires_at IS NULL 
        THEN 1
        ELSE 2
    END,
    updated_at DESC;



