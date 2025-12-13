-- ========================================
-- Migration: Add Internal Plan and Monthly Quota Support
-- ========================================
-- This migration:
-- 1. Adds 'internal' and 'premium' plan type support
-- 2. Adds monthly quota columns for monthly plans
-- 3. Updates plan constraints
--
-- IMPORTANT NOTES:
-- - This migration assumes user_plans and usage_quotas tables already exist
-- - It only uses ALTER TABLE statements, no CREATE TABLE
-- - This migration does NOT create RLS policies
-- - If you encounter "policy already exists" errors:
--   1. Run fix_policy_conflicts.sql first to clean up existing policies
--   2. Then run this migration
--   3. Finally, recreate policies from database_schema.sql if needed
--
-- This migration is safe to run multiple times (idempotent).

-- Step 1: Add monthly quota columns if they don't exist
-- Note: This assumes usage_quotas table already exists
-- It only adds columns, does not create the table
ALTER TABLE usage_quotas
  ADD COLUMN IF NOT EXISTS monthly_token_limit BIGINT,
  ADD COLUMN IF NOT EXISTS monthly_tokens_used BIGINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS quota_type VARCHAR(20) DEFAULT 'weekly';

-- Step 2: Add quota_type constraint
ALTER TABLE usage_quotas
  DROP CONSTRAINT IF EXISTS usage_quotas_quota_type_check;
  
ALTER TABLE usage_quotas
  ADD CONSTRAINT usage_quotas_quota_type_check 
  CHECK (quota_type IN ('weekly', 'monthly', 'lifetime'));

-- Step 3: Update user_plans table constraint to allow 'premium' and 'internal' plans
-- Note: This assumes user_plans table already exists
-- It only updates the constraint, does not create the table
ALTER TABLE user_plans 
DROP CONSTRAINT IF EXISTS user_plans_plan_check;

ALTER TABLE user_plans 
ADD CONSTRAINT user_plans_plan_check 
CHECK (plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal'));

-- Step 4: Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_usage_quotas_monthly_tokens ON usage_quotas(user_id, monthly_tokens_used);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_quota_type ON usage_quotas(quota_type);

-- Step 5: Update existing quotas based on new plan configuration
-- Normal Plan: Weekly 1M quota
UPDATE usage_quotas
SET 
  weekly_token_limit = 1000000,
  monthly_token_limit = NULL,
  monthly_tokens_used = 0,
  quota_type = 'weekly'
WHERE plan = 'normal';

-- High Plan: Monthly 1M quota
UPDATE usage_quotas
SET 
  monthly_token_limit = 1000000,
  weekly_token_limit = NULL,
  weekly_tokens_used = 0,
  quota_type = 'monthly'
WHERE plan = 'high';

-- Ultra Plan: Monthly 5M quota
UPDATE usage_quotas
SET 
  monthly_token_limit = 5000000,
  weekly_token_limit = NULL,
  weekly_tokens_used = 0,
  quota_type = 'monthly'
WHERE plan = 'ultra';

-- Premium Plan: Monthly 20M quota
UPDATE usage_quotas
SET 
  monthly_token_limit = 20000000,
  weekly_token_limit = NULL,
  weekly_tokens_used = 0,
  quota_type = 'monthly'
WHERE plan = 'premium';

-- Internal Plan: Unlimited (monthly_token_limit = NULL means unlimited)
-- Note: Internal Plan users should be manually added in Supabase
-- This migration just ensures the schema supports it

-- Step 6: Add comments
COMMENT ON COLUMN usage_quotas.monthly_token_limit IS 'Monthly token limit (for monthly plans, NULL = unlimited)';
COMMENT ON COLUMN usage_quotas.monthly_tokens_used IS 'Monthly tokens used (resets monthly)';
COMMENT ON COLUMN usage_quotas.quota_type IS 'Quota reset type: weekly, monthly, or lifetime';

-- Step 7: Verify constraint was added successfully
SELECT constraint_name, check_clause 
FROM information_schema.check_constraints 
WHERE constraint_name = 'user_plans_plan_check';

-- Step 8: Verify quota_type constraint
SELECT constraint_name, check_clause 
FROM information_schema.check_constraints 
WHERE constraint_name = 'usage_quotas_quota_type_check';

