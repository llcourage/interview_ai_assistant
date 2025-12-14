-- ========================================
-- 查看所有用户的 plan 和过期时间
-- ========================================

SELECT 
    user_id,
    plan,
    stripe_customer_id,
    stripe_subscription_id,
    subscription_status,
    plan_expires_at,
    CASE 
        WHEN plan_expires_at IS NULL THEN '无过期时间'
        WHEN plan_expires_at > NOW() THEN CONCAT('将在 ', TO_CHAR(plan_expires_at, 'YYYY-MM-DD HH24:MI:SS'), ' 过期')
        ELSE CONCAT('已过期 (', TO_CHAR(plan_expires_at, 'YYYY-MM-DD HH24:MI:SS'), ')')
    END as expires_status,
    CASE 
        WHEN plan_expires_at IS NULL THEN NULL
        WHEN plan_expires_at > NOW() THEN EXTRACT(EPOCH FROM (plan_expires_at - NOW())) / 86400
        ELSE NULL
    END as days_until_expiry,
    created_at,
    updated_at
FROM user_plans
ORDER BY 
    CASE 
        WHEN plan_expires_at IS NOT NULL AND plan_expires_at > NOW() THEN 1
        WHEN plan_expires_at IS NOT NULL AND plan_expires_at <= NOW() THEN 2
        ELSE 3
    END,
    plan_expires_at ASC;



