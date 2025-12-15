-- ========================================
-- 用户 plan 统计摘要
-- ========================================

-- 1. 按 plan 类型统计
SELECT 
    plan,
    COUNT(*) as user_count,
    COUNT(CASE WHEN plan_expires_at IS NOT NULL THEN 1 END) as users_with_expiry,
    COUNT(CASE WHEN plan_expires_at IS NOT NULL AND plan_expires_at > NOW() THEN 1 END) as users_expiring_soon,
    COUNT(CASE WHEN plan_expires_at IS NOT NULL AND plan_expires_at <= NOW() THEN 1 END) as users_expired
FROM user_plans
GROUP BY plan
ORDER BY user_count DESC;

-- 2. 按订阅状态统计
SELECT 
    subscription_status,
    COUNT(*) as user_count,
    COUNT(CASE WHEN plan_expires_at IS NOT NULL THEN 1 END) as users_with_expiry
FROM user_plans
WHERE subscription_status IS NOT NULL
GROUP BY subscription_status
ORDER BY user_count DESC;

-- 3. 即将在7天内过期的用户
SELECT 
    user_id,
    plan as current_plan,
    plan_expires_at,
    TO_CHAR(plan_expires_at, 'YYYY-MM-DD HH24:MI:SS') as expires_at,
    ROUND(EXTRACT(EPOCH FROM (plan_expires_at - NOW())) / 86400, 1) as days_until_expiry
FROM user_plans
WHERE plan_expires_at IS NOT NULL
  AND plan_expires_at > NOW()
  AND plan_expires_at <= NOW() + INTERVAL '7 days'
ORDER BY plan_expires_at ASC;



