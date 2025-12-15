-- ========================================
-- Test Database Schema (Simplified for Integration Tests)
-- Removes foreign key constraints and RLS for easier testing
-- ========================================

-- 1. User Subscription Plan Table
CREATE TABLE IF NOT EXISTS user_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- Removed FK constraint for testing
    plan VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal')),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_status VARCHAR(50),
    plan_expires_at TIMESTAMPTZ,
    next_plan VARCHAR(20) CHECK (next_plan IN ('start', 'normal', 'high', 'ultra', 'premium', 'internal')),
    next_update_at TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    stripe_event_ts BIGINT,
    weekly_tokens_used INTEGER DEFAULT 0,
    monthly_tokens_used INTEGER DEFAULT 0,
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
    user_id UUID NOT NULL,  -- Removed FK constraint for testing
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
    user_id UUID NOT NULL,  -- Removed FK constraint for testing
    plan VARCHAR(20) NOT NULL,
    daily_requests INTEGER DEFAULT 0,
    monthly_requests INTEGER DEFAULT 0,
    daily_limit INTEGER DEFAULT 200,
    monthly_limit INTEGER DEFAULT 5000,
    last_request_at TIMESTAMPTZ,
    quota_reset_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_usage_quotas_user_id ON usage_quotas(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_reset_date ON usage_quotas(quota_reset_date);

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

-- Note: RLS is disabled for testing (service_role_key bypasses RLS anyway)


