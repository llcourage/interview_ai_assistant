-- ========================================
-- Desktop AI Database Table Structure (Simplified)
-- For Supabase Database
-- Supports Start Plan (Free), Normal Plan, High Plan, Ultra Plan, Premium Plan, Internal Plan
-- ========================================

-- 1. User Subscription Plan Table
CREATE TABLE IF NOT EXISTS user_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal')),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_status VARCHAR(50),
    plan_expires_at TIMESTAMPTZ,
    next_plan VARCHAR(20) CHECK (next_plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal')),
    next_update_at TIMESTAMPTZ,  -- Next billing/renewal date (for subscription plans)
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    stripe_event_ts BIGINT,  -- Stripe event.created (Unix timestamp in seconds) - for webhook deduplication
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_plans_user_id ON user_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_stripe_customer_id ON user_plans(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_stripe_subscription_id ON user_plans(stripe_subscription_id);

-- 2. API Call Log Table
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0.0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_plan ON usage_logs(user_id, plan);

-- 3. User Quota Management Table
CREATE TABLE IF NOT EXISTS usage_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL,
    daily_requests INTEGER DEFAULT 0,
    monthly_requests INTEGER DEFAULT 0,
    daily_limit INTEGER DEFAULT 200,
    monthly_limit INTEGER DEFAULT 5000,
    weekly_tokens_used BIGINT NOT NULL DEFAULT 0,  -- Weekly tokens used (resets weekly)
    monthly_tokens_used BIGINT NOT NULL DEFAULT 0,  -- Monthly tokens used (resets monthly)
    weekly_token_limit BIGINT,  -- Weekly token limit (for weekly plans)
    monthly_token_limit BIGINT,  -- Monthly token limit (for monthly plans)
    lifetime_token_limit BIGINT,  -- Lifetime token limit (for start plan, no reset)
    quota_type VARCHAR(20) DEFAULT 'weekly' CHECK (quota_type IN ('weekly', 'monthly', 'lifetime')),
    last_request_at TIMESTAMPTZ,
    quota_reset_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_usage_quotas_user_id ON usage_quotas(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_reset_date ON usage_quotas(quota_reset_date);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_weekly_tokens ON usage_quotas(user_id, weekly_tokens_used);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_monthly_tokens ON usage_quotas(user_id, monthly_tokens_used);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_quota_type ON usage_quotas(quota_type);

-- ========================================
-- RLS (Row Level Security) Policies
-- ========================================

-- Enable RLS
ALTER TABLE user_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_quotas ENABLE ROW LEVEL SECURITY;

-- Users can only read and update their own data

-- user_plans policies
CREATE POLICY "Users can view their own plan"
    ON user_plans FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own plan"
    ON user_plans FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own plan"
    ON user_plans FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- usage_logs policies
CREATE POLICY "Users can view their own usage logs"
    ON usage_logs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "System can insert usage logs"
    ON usage_logs FOR INSERT
    WITH CHECK (true);

-- usage_quotas policies
CREATE POLICY "Users can view their own quota"
    ON usage_quotas FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own quota"
    ON usage_quotas FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own quota"
    ON usage_quotas FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ========================================
-- Triggers: Automatically update updated_at
-- ========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_plans_updated_at BEFORE UPDATE ON user_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usage_quotas_updated_at BEFORE UPDATE ON usage_quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Initialization: Create default Normal Plan for existing users
-- ========================================

-- This script will create normal plan for all existing users (default)
INSERT INTO user_plans (user_id, plan, created_at, updated_at)
SELECT 
    id,
    'normal',
    NOW(),
    NOW()
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM user_plans)
ON CONFLICT (user_id) DO NOTHING;
