-- ========================================
-- Migration: Add weekly_tokens_used column to usage_quotas
-- ========================================
-- This migration adds token usage tracking for weekly token limits
-- This replaces the old monthly_tokens_used column with weekly-based tracking

-- Add weekly_tokens_used column if it doesn't exist
ALTER TABLE usage_quotas
  ADD COLUMN IF NOT EXISTS weekly_tokens_used BIGINT NOT NULL DEFAULT 0;

-- Add weekly_token_limit column if it doesn't exist
ALTER TABLE usage_quotas
  ADD COLUMN IF NOT EXISTS weekly_token_limit BIGINT;

-- Add lifetime_token_limit column if it doesn't exist (for start plan)
ALTER TABLE usage_quotas
  ADD COLUMN IF NOT EXISTS lifetime_token_limit BIGINT;

-- Migrate existing monthly_tokens_used data to weekly_tokens_used if monthly_tokens_used exists
-- This handles the transition from monthly to weekly tracking
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 
    FROM information_schema.columns 
    WHERE table_name = 'usage_quotas' 
    AND column_name = 'monthly_tokens_used'
  ) THEN
    UPDATE usage_quotas
    SET weekly_tokens_used = monthly_tokens_used
    WHERE weekly_tokens_used = 0 
    AND monthly_tokens_used IS NOT NULL 
    AND monthly_tokens_used > 0;
  END IF;
END $$;

-- Migrate monthly_token_limit to weekly_token_limit if monthly_token_limit exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 
    FROM information_schema.columns 
    WHERE table_name = 'usage_quotas' 
    AND column_name = 'monthly_token_limit'
  ) THEN
    UPDATE usage_quotas
    SET weekly_token_limit = monthly_token_limit
    WHERE weekly_token_limit IS NULL 
    AND monthly_token_limit IS NOT NULL;
  END IF;
END $$;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_usage_quotas_weekly_tokens ON usage_quotas(user_id, weekly_tokens_used);

-- Comment
COMMENT ON COLUMN usage_quotas.weekly_tokens_used IS 'Weekly tokens used by the user (resets weekly)';
COMMENT ON COLUMN usage_quotas.weekly_token_limit IS 'Weekly token limit for the user plan';
COMMENT ON COLUMN usage_quotas.lifetime_token_limit IS 'Lifetime token limit (for start plan, no reset)';








