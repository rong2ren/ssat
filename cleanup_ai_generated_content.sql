-- ========================================
-- CLEANUP AI-GENERATED CONTENT SCRIPT
-- Deletes all AI-generated content to regenerate with better training examples
-- ========================================

-- WARNING: This will permanently delete all AI-generated content!
-- Make sure you have backups if needed.

-- ========================================
-- STEP 1: CHECK CURRENT CONTENT COUNTS
-- ========================================

SELECT 'BEFORE CLEANUP - Current content counts:' as info;

SELECT 
    'ai_generated_questions' as table_name,
    COUNT(*) as count
FROM ai_generated_questions

UNION ALL

SELECT 
    'ai_generated_reading_passages' as table_name,
    COUNT(*) as count
FROM ai_generated_reading_passages

UNION ALL

SELECT 
    'ai_generated_reading_questions' as table_name,
    COUNT(*) as count
FROM ai_generated_reading_questions

UNION ALL

SELECT 
    'ai_generated_writing_prompts' as table_name,
    COUNT(*) as count
FROM ai_generated_writing_prompts

UNION ALL

SELECT 
    'ai_generation_sessions' as table_name,
    COUNT(*) as count
FROM ai_generation_sessions

UNION ALL

SELECT 
    'user_question_usage' as table_name,
    COUNT(*) as count
FROM user_question_usage

ORDER BY table_name;

-- ========================================
-- STEP 2: DELETE IN CORRECT ORDER (respecting foreign keys)
-- ========================================

-- 1. Delete user usage tracking (references AI content IDs)
DELETE FROM user_question_usage;
SELECT 'Deleted user_question_usage records' as status;

-- 2. Delete reading questions (references reading passages)
DELETE FROM ai_generated_reading_questions;
SELECT 'Deleted ai_generated_reading_questions records' as status;

-- 3. Delete reading passages (referenced by reading questions)
DELETE FROM ai_generated_reading_passages;
SELECT 'Deleted ai_generated_reading_passages records' as status;

-- 4. Delete standalone questions
DELETE FROM ai_generated_questions;
SELECT 'Deleted ai_generated_questions records' as status;

-- 5. Delete writing prompts
DELETE FROM ai_generated_writing_prompts;
SELECT 'Deleted ai_generated_writing_prompts records' as status;

-- 6. Delete generation sessions (optional - for clean slate)
DELETE FROM ai_generation_sessions;
SELECT 'Deleted ai_generation_sessions records' as status;

-- ========================================
-- STEP 3: VERIFY CLEANUP
-- ========================================

SELECT 'AFTER CLEANUP - Remaining content counts:' as info;

SELECT 
    'ai_generated_questions' as table_name,
    COUNT(*) as count
FROM ai_generated_questions

UNION ALL

SELECT 
    'ai_generated_reading_passages' as table_name,
    COUNT(*) as count
FROM ai_generated_reading_passages

UNION ALL

SELECT 
    'ai_generated_reading_questions' as table_name,
    COUNT(*) as count
FROM ai_generated_reading_questions

UNION ALL

SELECT 
    'ai_generated_writing_prompts' as table_name,
    COUNT(*) as count
FROM ai_generated_writing_prompts

UNION ALL

SELECT 
    'ai_generation_sessions' as table_name,
    COUNT(*) as count
FROM ai_generation_sessions

UNION ALL

SELECT 
    'user_question_usage' as table_name,
    COUNT(*) as count
FROM user_question_usage

ORDER BY table_name;

-- ========================================
-- STEP 4: RESET SEQUENCES (if any)
-- ========================================

-- Note: Since we're using UUIDs, no sequences to reset

-- ========================================
-- STEP 5: VERIFY TRAINING EXAMPLES ARE READY
-- ========================================

SELECT 'Training examples available for regeneration:' as info;

SELECT 
    'training_questions' as table_name,
    COUNT(*) as count
FROM training_questions

UNION ALL

SELECT 
    'training_reading_passages' as table_name,
    COUNT(*) as count
FROM training_reading_passages

UNION ALL

SELECT 
    'training_reading_questions' as table_name,
    COUNT(*) as count
FROM training_reading_questions

UNION ALL

SELECT 
    'training_writing_prompts' as table_name,
    COUNT(*) as count
FROM training_writing_prompts

ORDER BY table_name;

-- ========================================
-- COMPLETION MESSAGE
-- ========================================

SELECT 'CLEANUP COMPLETE! All AI-generated content has been deleted.' as status;
SELECT 'You can now regenerate content using better training examples.' as next_step;
