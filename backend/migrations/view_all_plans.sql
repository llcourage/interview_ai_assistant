-- ========================================
-- View all available plan values
-- ========================================

-- View all different plan values and their counts in user_plans table
SELECT 
    plan, 
    COUNT(*) as user_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM user_plans 
GROUP BY plan
ORDER BY plan;

-- View detailed information for each plan (if need to see specific users)
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

