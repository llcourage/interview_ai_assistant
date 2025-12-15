-- ========================================
-- Migration: Add plan_expires_at column if missing
-- ========================================
-- This migration adds plan_expires_at column to user_plans table
-- if it doesn't already exist (idempotent)

-- Add plan_expires_at column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_plans' 
        AND column_name = 'plan_expires_at'
    ) THEN
        ALTER TABLE user_plans
        ADD COLUMN plan_expires_at TIMESTAMPTZ;
        
        COMMENT ON COLUMN user_plans.plan_expires_at IS 'Plan expiration time - when user cancels subscription, plan will downgrade to start at this time';
        
        RAISE NOTICE 'Added plan_expires_at column to user_plans table';
    ELSE
        RAISE NOTICE 'plan_expires_at column already exists in user_plans table';
    END IF;
END $$;

-- Verify the column was added
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND column_name = 'plan_expires_at';



