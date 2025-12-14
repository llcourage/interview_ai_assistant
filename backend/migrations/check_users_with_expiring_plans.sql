-- ========================================
-- 查看有 plan_expires_at 的用户（即将降级的用户）
-- ========================================

SELECT 
    user_id,
    plan as current_plan,
    stripe_subscription_id,
    subscription_status,
    plan_expires_at,
    TO_CHAR(plan_expires_at, 'YYYY-MM-DD HH24:MI:SS') as expires_at_formatted,
    CASE 
        WHEN plan_expires_at > NOW() THEN 
            CONCAT(
                ROUND(EXTRACT(EPOCH FROM (plan_expires_at - NOW())) / 86400, 1), 
                ' 天后降级到 start plan'
            )
        ELSE '已过期，应降级到 start plan'
    END as status_description,
    EXTRACT(EPOCH FROM (plan_expires_at - NOW())) / 86400 as days_until_expiry
FROM user_plans
WHERE plan_expires_at IS NOT NULL
ORDER BY plan_expires_at ASC;



