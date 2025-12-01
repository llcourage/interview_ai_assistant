-- ========================================
-- AI Interview Assistant 数据库表结构（简化版）
-- 用于 Supabase 数据库
-- 只保留 Normal 和 High Plan
-- ========================================

-- 1. 用户订阅计划表
CREATE TABLE IF NOT EXISTS user_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (plan IN ('normal', 'high')),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_status VARCHAR(50),
    plan_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_plans_user_id ON user_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_stripe_customer_id ON user_plans(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_stripe_subscription_id ON user_plans(stripe_subscription_id);

-- 2. API 调用记录表
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_plan ON usage_logs(user_id, plan);

-- 3. 用户配额管理表
CREATE TABLE IF NOT EXISTS usage_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_usage_quotas_user_id ON usage_quotas(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_reset_date ON usage_quotas(quota_reset_date);

-- ========================================
-- RLS (Row Level Security) 策略
-- ========================================

-- 启用 RLS
ALTER TABLE user_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_quotas ENABLE ROW LEVEL SECURITY;

-- 用户只能读取和更新自己的数据

-- user_plans 策略
CREATE POLICY "Users can view their own plan"
    ON user_plans FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own plan"
    ON user_plans FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own plan"
    ON user_plans FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- usage_logs 策略
CREATE POLICY "Users can view their own usage logs"
    ON usage_logs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "System can insert usage logs"
    ON usage_logs FOR INSERT
    WITH CHECK (true);

-- usage_quotas 策略
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
-- 触发器：自动更新 updated_at
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
-- 初始化：为现有用户创建默认 Normal Plan
-- ========================================

-- 这个脚本会为所有现有用户创建 normal plan（默认）
INSERT INTO user_plans (user_id, plan, created_at, updated_at)
SELECT 
    id,
    'normal',
    NOW(),
    NOW()
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM user_plans)
ON CONFLICT (user_id) DO NOTHING;
