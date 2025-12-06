-- ========================================
-- Migration: Migrate 'starter' to 'start' and Add Ultra Plan Support
-- ========================================
-- 这个脚本会：
-- 1. 先删除旧约束（允许更新数据）
-- 2. 将现有的 'starter' plan 迁移为 'start'
-- 3. 添加新约束以支持 'start', 'normal', 'high', 'ultra'

-- 步骤 1: 检查当前约束（查看当前允许的值）
SELECT constraint_name, check_clause 
FROM information_schema.check_constraints 
WHERE constraint_name = 'user_plans_plan_check';

-- 步骤 2: 检查是否有 'starter' plan（查看现有数据）
SELECT plan, COUNT(*) as count 
FROM user_plans 
WHERE plan = 'starter'
GROUP BY plan;

-- 步骤 3: 删除旧的 CHECK 约束（必须先删除才能更新数据）
ALTER TABLE user_plans 
DROP CONSTRAINT IF EXISTS user_plans_plan_check;

-- 步骤 4: 将 'starter' 更新为 'start'（现在没有约束，可以更新）
UPDATE user_plans 
SET plan = 'start' 
WHERE plan = 'starter';

-- 步骤 5: 检查是否还有其他无效的 plan 值（确保数据一致性）
SELECT DISTINCT plan 
FROM user_plans 
WHERE plan NOT IN ('start', 'normal', 'high', 'ultra');

-- 步骤 6: 添加新的 CHECK 约束，允许 'start', 'normal', 'high', 'ultra'
ALTER TABLE user_plans 
ADD CONSTRAINT user_plans_plan_check 
CHECK (plan IN ('start', 'normal', 'high', 'ultra'));

-- 步骤 7: 验证约束是否添加成功
SELECT constraint_name, constraint_type, check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc ON tc.constraint_name = cc.constraint_name
WHERE tc.table_name = 'user_plans' 
AND tc.constraint_type = 'CHECK';

-- 步骤 8: 验证迁移结果（最终检查）
SELECT plan, COUNT(*) as count 
FROM user_plans 
GROUP BY plan
ORDER BY plan;

