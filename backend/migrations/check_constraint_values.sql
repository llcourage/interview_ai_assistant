-- ========================================
-- Check current constraint values
-- ========================================

-- 方法 1: 查看约束的详细信息
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

-- 方法 2: 查看当前表中的所有 plan 值
SELECT plan, COUNT(*) as count 
FROM user_plans 
GROUP BY plan
ORDER BY plan;

-- 方法 3: 尝试查看约束定义（PostgreSQL 特有）
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conname = 'user_plans_plan_check';

