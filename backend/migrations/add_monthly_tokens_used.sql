-- ========================================
-- Migration: Add monthly_tokens_used column to usage_quotas
-- ========================================
-- This migration adds token usage tracking for monthly token limits

ALTER TABLE usage_quotas
  ADD COLUMN IF NOT EXISTS monthly_tokens_used BIGINT NOT NULL DEFAULT 0;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_usage_quotas_monthly_tokens ON usage_quotas(user_id, monthly_tokens_used);

-- Comment
COMMENT ON COLUMN usage_quotas.monthly_tokens_used IS 'Monthly tokens used by the user (resets monthly)';

