-- ========================================
-- Check Current Fields in user_plans Table
-- ========================================
-- This script shows the current column definitions in the user_plans table

-- Show all columns in user_plans table
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Check specifically for the 3 target fields
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND table_schema = 'public'
  AND column_name IN ('next_plan', 'cancel_at_period_end', 'stripe_event_ts')
ORDER BY column_name;

-- Summary: Check if fields exist and verify types
SELECT 
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'user_plans' AND table_schema = 'public' AND column_name = 'next_plan') as next_plan_exists,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'user_plans' AND table_schema = 'public' AND column_name = 'cancel_at_period_end') as cancel_at_period_end_exists,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'user_plans' AND table_schema = 'public' AND column_name = 'stripe_event_ts') as stripe_event_ts_exists,
    (SELECT data_type FROM information_schema.columns 
     WHERE table_name = 'user_plans' AND table_schema = 'public' AND column_name = 'stripe_event_ts') as stripe_event_ts_type;

