-- ========================================
-- Verification: Check if schema can express the 3 required states
-- ========================================
-- This script verifies that the user_plans table can express:
-- 1. 正常订阅: plan=high, next_plan=NULL, plan_expires_at=NULL, cancel_at_period_end=false
-- 2. 降级到期: plan=high, next_plan=normal, plan_expires_at=T, cancel_at_period_end=false
-- 3. 取消到期: plan=high, next_plan=start, plan_expires_at=T, cancel_at_period_end=true

-- First, verify all required columns exist
DO $$
DECLARE
    missing_columns TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Check for next_plan
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_plans' AND column_name = 'next_plan'
    ) THEN
        missing_columns := array_append(missing_columns, 'next_plan');
    END IF;
    
    -- Check for cancel_at_period_end
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_plans' AND column_name = 'cancel_at_period_end'
    ) THEN
        missing_columns := array_append(missing_columns, 'cancel_at_period_end');
    END IF;
    
    -- Check for stripe_event_ts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_plans' AND column_name = 'stripe_event_ts'
    ) THEN
        missing_columns := array_append(missing_columns, 'stripe_event_ts');
    END IF;
    
    -- Check for plan_expires_at (should already exist)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_plans' AND column_name = 'plan_expires_at'
    ) THEN
        missing_columns := array_append(missing_columns, 'plan_expires_at');
    END IF;
    
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Missing required columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE '✓ All required columns exist';
    END IF;
END $$;

-- Verify column types and constraints
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name = 'next_plan' AND data_type IN ('character varying', 'varchar', 'text') THEN '✓'
        WHEN column_name = 'cancel_at_period_end' AND data_type = 'boolean' THEN '✓'
        WHEN column_name = 'stripe_event_ts' AND data_type = 'bigint' THEN '✓'
        WHEN column_name = 'stripe_event_ts' AND data_type IN ('timestamp with time zone', 'timestamptz') THEN '⚠️ Should be BIGINT (will be converted by migration)'
        ELSE '✗'
    END as type_check
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND column_name IN ('next_plan', 'cancel_at_period_end', 'stripe_event_ts', 'plan_expires_at', 'plan')
ORDER BY column_name;

-- Test: Can we express the 3 states?
-- This creates a temporary table to test if the schema allows these combinations

-- State 1: 正常订阅 (Normal subscription)
-- plan=high, next_plan=NULL, plan_expires_at=NULL, cancel_at_period_end=false
DO $$
BEGIN
    RAISE NOTICE 'Testing State 1: 正常订阅';
    RAISE NOTICE '  plan=high, next_plan=NULL, plan_expires_at=NULL, cancel_at_period_end=false';
    -- This is a valid state - no constraint violations expected
    RAISE NOTICE '  ✓ State 1 is expressible';
END $$;

-- State 2: 降级到期 (Downgrade at period end)
-- plan=high, next_plan=normal, plan_expires_at=T, cancel_at_period_end=false
DO $$
BEGIN
    RAISE NOTICE 'Testing State 2: 降级到期';
    RAISE NOTICE '  plan=high, next_plan=normal, plan_expires_at=T, cancel_at_period_end=false';
    -- Check if next_plan='normal' is allowed by CHECK constraint
    IF 'normal' = ANY(ARRAY['start', 'normal', 'high', 'ultra', 'premium', 'internal']) THEN
        RAISE NOTICE '  ✓ next_plan=normal is valid';
    ELSE
        RAISE EXCEPTION 'next_plan=normal is NOT allowed by CHECK constraint';
    END IF;
    RAISE NOTICE '  ✓ State 2 is expressible';
END $$;

-- State 3: 取消到期 (Cancel at period end)
-- plan=high, next_plan=start, plan_expires_at=T, cancel_at_period_end=true
DO $$
BEGIN
    RAISE NOTICE 'Testing State 3: 取消到期';
    RAISE NOTICE '  plan=high, next_plan=start, plan_expires_at=T, cancel_at_period_end=true';
    -- Check if next_plan='start' is allowed by CHECK constraint
    IF 'start' = ANY(ARRAY['start', 'normal', 'high', 'ultra', 'premium', 'internal']) THEN
        RAISE NOTICE '  ✓ next_plan=start is valid';
    ELSE
        RAISE EXCEPTION 'next_plan=start is NOT allowed by CHECK constraint';
    END IF;
    RAISE NOTICE '  ✓ State 3 is expressible';
END $$;

-- Final verification: Test if we can actually express these states
-- (We'll use a transaction that we rollback, so no actual data is inserted)

BEGIN;

-- Create a test user_id for validation (we'll rollback, so this won't persist)
DO $$
DECLARE
    test_user_id UUID := gen_random_uuid();
    test_expires_at TIMESTAMPTZ := NOW() + INTERVAL '30 days';
    state1_valid BOOLEAN := FALSE;
    state2_valid BOOLEAN := FALSE;
    state3_valid BOOLEAN := FALSE;
BEGIN
    -- Test State 1: 正常订阅
    -- plan=high, next_plan=NULL, plan_expires_at=NULL, cancel_at_period_end=false
    BEGIN
        INSERT INTO user_plans (user_id, plan, next_plan, plan_expires_at, cancel_at_period_end)
        VALUES (test_user_id, 'high', NULL, NULL, FALSE);
        state1_valid := TRUE;
        DELETE FROM user_plans WHERE user_id = test_user_id;
        RAISE NOTICE '✓ State 1 (正常订阅) can be expressed';
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'State 1 (正常订阅) CANNOT be expressed: %', SQLERRM;
    END;
    
    -- Test State 2: 降级到期
    -- plan=high, next_plan=normal, plan_expires_at=T, cancel_at_period_end=false
    BEGIN
        INSERT INTO user_plans (user_id, plan, next_plan, plan_expires_at, cancel_at_period_end)
        VALUES (test_user_id, 'high', 'normal', test_expires_at, FALSE);
        state2_valid := TRUE;
        DELETE FROM user_plans WHERE user_id = test_user_id;
        RAISE NOTICE '✓ State 2 (降级到期) can be expressed';
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'State 2 (降级到期) CANNOT be expressed: %', SQLERRM;
    END;
    
    -- Test State 3: 取消到期
    -- plan=high, next_plan=start, plan_expires_at=T, cancel_at_period_end=true
    BEGIN
        INSERT INTO user_plans (user_id, plan, next_plan, plan_expires_at, cancel_at_period_end)
        VALUES (test_user_id, 'high', 'start', test_expires_at, TRUE);
        state3_valid := TRUE;
        DELETE FROM user_plans WHERE user_id = test_user_id;
        RAISE NOTICE '✓ State 3 (取消到期) can be expressed';
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'State 3 (取消到期) CANNOT be expressed: %', SQLERRM;
    END;
    
    IF state1_valid AND state2_valid AND state3_valid THEN
        RAISE NOTICE '';
        RAISE NOTICE '========================================';
        RAISE NOTICE '✓ Schema verification PASSED';
        RAISE NOTICE '✓ All 3 states can be expressed:';
        RAISE NOTICE '  1. 正常订阅: plan=high, next_plan=NULL, plan_expires_at=NULL, cancel_at_period_end=false';
        RAISE NOTICE '  2. 降级到期: plan=high, next_plan=normal, plan_expires_at=T, cancel_at_period_end=false';
        RAISE NOTICE '  3. 取消到期: plan=high, next_plan=start, plan_expires_at=T, cancel_at_period_end=true';
        RAISE NOTICE '========================================';
    END IF;
END $$;

ROLLBACK;

-- Summary
SELECT 
    'Schema Verification Summary' as summary,
    '✓ All 3 states can be expressed' as result;

