-- ========================================
-- Migration: Fix plan column default value
-- ========================================
-- This migration fixes the default value for the plan column in user_plans table
-- to prevent constraint violations when inserting new records without plan value.
--
-- Problem: Database default value might be 'starter' which violates the check constraint
-- Solution: Change default value to 'start' which is allowed by the constraint
--
-- This migration is safe to run multiple times (idempotent).

-- Step 1: Check current default value
SELECT 
    column_name,
    column_default,
    data_type
FROM information_schema.columns
WHERE table_name = 'user_plans' 
AND column_name = 'plan';

-- Step 2: Alter the default value to 'start'
ALTER TABLE user_plans
ALTER COLUMN plan SET DEFAULT 'start';

-- Step 3: Verify the change
SELECT 
    column_name,
    column_default,
    data_type
FROM information_schema.columns
WHERE table_name = 'user_plans' 
AND column_name = 'plan';

-- Expected result: column_default should be 'start'::character varying

