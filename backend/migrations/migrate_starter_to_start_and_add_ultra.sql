-- ========================================
-- Migration: Migrate 'starter' to 'start' and Add Ultra Plan Support
-- ========================================
-- This script will:
-- 1. First delete old constraint (allow data update)
-- 2. Migrate existing 'starter' plan to 'start'
-- 3. Add new constraint to support 'start', 'normal', 'high', 'ultra'

-- Step 1: Check current constraint (view currently allowed values)
SELECT constraint_name, check_clause 
FROM information_schema.check_constraints 
WHERE constraint_name = 'user_plans_plan_check';

-- Step 2: Check if there are 'starter' plans (view existing data)
SELECT plan, COUNT(*) as count 
FROM user_plans 
WHERE plan = 'starter'
GROUP BY plan;

-- Step 3: Delete old CHECK constraint (must delete first to update data)
ALTER TABLE user_plans 
DROP CONSTRAINT IF EXISTS user_plans_plan_check;

-- Step 4: Update 'starter' to 'start' (no constraint now, can update)
UPDATE user_plans 
SET plan = 'start' 
WHERE plan = 'starter';

-- Step 5: Check if there are other invalid plan values (ensure data consistency)
SELECT DISTINCT plan 
FROM user_plans 
WHERE plan NOT IN ('start', 'normal', 'high', 'ultra');

-- Step 6: Add new CHECK constraint, allow 'start', 'normal', 'high', 'ultra'
ALTER TABLE user_plans 
ADD CONSTRAINT user_plans_plan_check 
CHECK (plan IN ('start', 'normal', 'high', 'ultra'));

-- Step 7: Verify constraint was added successfully
SELECT constraint_name, constraint_type, check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc ON tc.constraint_name = cc.constraint_name
WHERE tc.table_name = 'user_plans' 
AND tc.constraint_type = 'CHECK';

-- Step 8: Verify migration results (final check)
SELECT plan, COUNT(*) as count 
FROM user_plans 
GROUP BY plan
ORDER BY plan;

