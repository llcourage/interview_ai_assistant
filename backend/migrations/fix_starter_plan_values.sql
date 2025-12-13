-- ========================================
-- Migration: Fix 'starter' plan values to 'start'
-- ========================================
-- This migration fixes any remaining 'starter' plan values in the database
-- by converting them to 'start' to match the current constraint.
--
-- This migration is safe to run multiple times (idempotent).

-- Step 1: Update user_plans table
UPDATE user_plans
SET plan = 'start'
WHERE plan = 'starter';

-- Step 2: Update usage_quotas table
UPDATE usage_quotas
SET plan = 'start'
WHERE plan = 'starter';

-- Step 3: Verify the update
SELECT 
    'user_plans' AS table_name,
    COUNT(*) AS starter_count
FROM user_plans
WHERE plan = 'starter'

UNION ALL

SELECT 
    'usage_quotas' AS table_name,
    COUNT(*) AS starter_count
FROM usage_quotas
WHERE plan = 'starter';

-- If the above query returns 0 rows for both tables, the migration was successful.

