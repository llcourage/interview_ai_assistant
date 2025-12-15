-- ========================================
-- Migration: Add next_plan, cancel_at_period_end, stripe_event_ts columns to user_plans table
-- ========================================
-- This migration adds three new columns to track plan changes and Stripe events:
-- - next_plan: The plan to switch to (for plan changes)
-- - cancel_at_period_end: Whether subscription will cancel at period end
-- - stripe_event_ts: Timestamp of the last Stripe webhook event

-- Add next_plan column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_plans' 
        AND column_name = 'next_plan'
    ) THEN
        ALTER TABLE user_plans
        ADD COLUMN next_plan VARCHAR(20) CHECK (next_plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal'));
        
        COMMENT ON COLUMN user_plans.next_plan IS 'Next plan to switch to (for plan changes scheduled in the future)';
        
        RAISE NOTICE 'Added next_plan column to user_plans table';
    ELSE
        RAISE NOTICE 'next_plan column already exists in user_plans table';
        
        -- Ensure CHECK constraint exists (in case column was added without constraint)
        IF NOT EXISTS (
            SELECT 1 
            FROM pg_constraint 
            WHERE conrelid = 'user_plans'::regclass 
            AND conname = 'user_plans_next_plan_check'
        ) THEN
            ALTER TABLE user_plans
            ADD CONSTRAINT user_plans_next_plan_check
            CHECK (next_plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal'));
            
            RAISE NOTICE 'Added CHECK constraint for next_plan column';
        ELSE
            RAISE NOTICE 'CHECK constraint for next_plan already exists';
        END IF;
    END IF;
END $$;

-- Add cancel_at_period_end column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_plans' 
        AND column_name = 'cancel_at_period_end'
    ) THEN
        ALTER TABLE user_plans
        ADD COLUMN cancel_at_period_end BOOLEAN DEFAULT FALSE;
        
        COMMENT ON COLUMN user_plans.cancel_at_period_end IS 'Whether subscription will cancel at period end (true if user cancelled but subscription is still active until period end)';
        
        RAISE NOTICE 'Added cancel_at_period_end column to user_plans table';
    ELSE
        RAISE NOTICE 'cancel_at_period_end column already exists in user_plans table';
    END IF;
END $$;

-- Add stripe_event_ts column if it doesn't exist
-- Note: Using BIGINT to store Stripe's event.created (Unix timestamp in seconds)
-- This avoids timezone conversion issues and allows direct comparison
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_plans' 
        AND column_name = 'stripe_event_ts'
    ) THEN
        ALTER TABLE user_plans
        ADD COLUMN stripe_event_ts BIGINT;
        
        COMMENT ON COLUMN user_plans.stripe_event_ts IS 'Stripe event.created (Unix timestamp in seconds) - used to prevent processing duplicate/out-of-order webhook events';
        
        RAISE NOTICE 'Added stripe_event_ts column to user_plans table';
    ELSE
        -- If column exists but is TIMESTAMPTZ, convert it to BIGINT
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'user_plans' 
            AND column_name = 'stripe_event_ts'
            AND data_type = 'timestamp with time zone'
        ) THEN
            ALTER TABLE user_plans
            ALTER COLUMN stripe_event_ts TYPE BIGINT USING EXTRACT(EPOCH FROM stripe_event_ts)::BIGINT;
            
            RAISE NOTICE 'Converted stripe_event_ts from TIMESTAMPTZ to BIGINT';
        ELSE
            RAISE NOTICE 'stripe_event_ts column already exists in user_plans table';
        END IF;
    END IF;
END $$;

-- Verify the columns were added
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND column_name IN ('next_plan', 'cancel_at_period_end', 'stripe_event_ts')
ORDER BY column_name;

