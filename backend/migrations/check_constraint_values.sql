-- ========================================
-- Check current constraint values
-- ========================================

-- Method 1: View detailed constraint information
SELECT 
    tc.constraint_name,
    tc.table_name,
    cc.check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_name = 'user_plans' 
    AND tc.constraint_type = 'CHECK'
    AND tc.constraint_name = 'user_plans_plan_check';

-- Method 2: View all plan values in current table
SELECT plan, COUNT(*) as count 
FROM user_plans 
GROUP BY plan
ORDER BY plan;

-- Method 3: Try to view constraint definition (PostgreSQL specific)
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conname = 'user_plans_plan_check';

