-- ========================================
-- Check next_plan CHECK Constraint
-- ========================================
-- This script verifies that the CHECK constraint exists for next_plan column

-- Check if the constraint exists
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'user_plans'::regclass
  AND contype = 'c'
  AND (conname LIKE '%next_plan%' OR pg_get_constraintdef(oid) LIKE '%next_plan%')
ORDER BY conname;

-- Summary
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✓ CHECK constraint exists for next_plan'
        ELSE '✗ CHECK constraint missing for next_plan'
    END as constraint_status
FROM pg_constraint
WHERE conrelid = 'user_plans'::regclass
  AND contype = 'c'
  AND (conname LIKE '%next_plan%' OR pg_get_constraintdef(oid) LIKE '%next_plan%');

