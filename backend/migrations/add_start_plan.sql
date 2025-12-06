-- ========================================
-- Migration: Add Start Plan Support
-- ========================================
-- 这个脚本更新 user_plans 表，允许 'start' plan

-- 1. 删除旧的 CHECK 约束（如果存在）
ALTER TABLE user_plans 
DROP CONSTRAINT IF EXISTS user_plans_plan_check;

-- 2. 添加新的 CHECK 约束，允许 'start', 'normal', 'high'
ALTER TABLE user_plans 
ADD CONSTRAINT user_plans_plan_check 
CHECK (plan IN ('start', 'normal', 'high'));

-- 验证
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'user_plans' 
AND constraint_type = 'CHECK';

