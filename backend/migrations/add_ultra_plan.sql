-- ========================================
-- Migration: Add Ultra Plan Support
-- ========================================
-- This script updates user_plans table to allow 'ultra' plan

-- 1. Delete old CHECK constraint (if exists)
ALTER TABLE user_plans 
DROP CONSTRAINT IF EXISTS user_plans_plan_check;

-- 2. Add new CHECK constraint, allow 'start', 'normal', 'high', 'ultra'
ALTER TABLE user_plans 
ADD CONSTRAINT user_plans_plan_check 
CHECK (plan IN ('start', 'normal', 'high', 'ultra'));

-- Verify
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'user_plans' 
AND constraint_type = 'CHECK';

