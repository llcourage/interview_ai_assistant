-- ========================================
-- Fix: Remove duplicate policies if they exist
-- ========================================
-- Run this BEFORE running add_internal_plan_and_monthly_quota.sql
-- if you encounter "policy already exists" errors
--
-- This script safely removes policies if they exist,
-- allowing you to recreate them via database_schema.sql

-- Drop user_plans policies if they exist
DROP POLICY IF EXISTS "Users can view their own plan" ON user_plans;
DROP POLICY IF EXISTS "Users can update their own plan" ON user_plans;
DROP POLICY IF EXISTS "Users can insert their own plan" ON user_plans;

-- Drop usage_logs policies if they exist
DROP POLICY IF EXISTS "Users can view their own usage logs" ON usage_logs;
DROP POLICY IF EXISTS "System can insert usage logs" ON usage_logs;

-- Drop usage_quotas policies if they exist
DROP POLICY IF EXISTS "Users can view their own quota" ON usage_quotas;
DROP POLICY IF EXISTS "Users can update their own quota" ON usage_quotas;
DROP POLICY IF EXISTS "Users can insert their own quota" ON usage_quotas;

-- Note: After running this, you may need to recreate policies
-- by running the relevant sections from database_schema.sql

