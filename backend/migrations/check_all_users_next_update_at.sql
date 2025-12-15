-- ========================================
-- 查看所有用户的 next_update_at（下次续费时间）
-- ========================================

SELECT 
    user_id,
    plan,
    stripe_subscription_id,
    subscription_status,
    plan_expires_at,
    next_update_at,
    CASE 
        WHEN next_update_at IS NULL THEN '无续费时间（start plan 或未设置）'
        WHEN next_update_at > NOW() THEN CONCAT('将在 ', TO_CHAR(next_update_at, 'YYYY-MM-DD HH24:MI:SS'), ' 续费')
        ELSE CONCAT('已过期 (', TO_CHAR(next_update_at, 'YYYY-MM-DD HH24:MI:SS'), ')')
    END as next_update_status,
    CASE 
        WHEN next_update_at IS NULL THEN NULL
        WHEN next_update_at > NOW() THEN EXTRACT(EPOCH FROM (next_update_at - NOW())) / 86400
        ELSE NULL
    END as days_until_next_update,
    created_at,
    updated_at
FROM user_plans
WHERE stripe_subscription_id IS NOT NULL
ORDER BY 
    CASE 
        WHEN next_update_at IS NOT NULL AND next_update_at > NOW() THEN 1
        WHEN next_update_at IS NOT NULL AND next_update_at <= NOW() THEN 2
        ELSE 3
    END,
    next_update_at ASC;



