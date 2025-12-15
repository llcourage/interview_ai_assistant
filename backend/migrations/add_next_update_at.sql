-- ========================================
-- Migration: Add next_update_at column to user_plans table
-- ========================================
-- This migration adds next_update_at column to track when the plan will renew
-- For subscription plans (normal/high/ultra/premium), this is the next billing date
-- For start plan, this is NULL (one-time purchase)

-- Add next_update_at column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_plans' 
        AND column_name = 'next_update_at'
    ) THEN
        ALTER TABLE user_plans
        ADD COLUMN next_update_at TIMESTAMPTZ;
        
        COMMENT ON COLUMN user_plans.next_update_at IS 'Next billing/renewal date - when subscription will automatically renew (for subscription plans)';
        
        RAISE NOTICE 'Added next_update_at column to user_plans table';
    ELSE
        RAISE NOTICE 'next_update_at column already exists in user_plans table';
    END IF;
END $$;

-- Verify the column was added
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND column_name = 'next_update_at';



