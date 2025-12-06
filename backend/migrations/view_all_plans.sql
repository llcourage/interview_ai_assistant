-- ========================================
-- 查看所有可用的 plan 值
-- ========================================

-- 查看 user_plans 表中所有不同的 plan 值及其数量
SELECT 
    plan, 
    COUNT(*) as user_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM user_plans 
GROUP BY plan
ORDER BY plan;

-- 查看每个 plan 的详细信息（如果需要看具体用户）
SELECT 
    id,
    user_id,
    plan,
    stripe_customer_id,
    stripe_subscription_id,
    subscription_status,
    created_at,
    updated_at
FROM user_plans
ORDER BY plan, created_at;

