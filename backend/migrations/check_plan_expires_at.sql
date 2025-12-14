-- ========================================
-- 检查 user_plans 表是否有 plan_expires_at 字段
-- ========================================

-- 检查字段是否存在
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_plans'
  AND column_name = 'plan_expires_at';

-- 如果上面的查询返回空结果，说明字段不存在，需要运行下面的 migration



