-- ========================================
-- PREVIEW CLEANUP AI-GENERATED CONTENT SCRIPT
-- Shows what will be deleted WITHOUT actually deleting anything
-- ========================================

-- ========================================
-- CURRENT CONTENT COUNTS
-- ========================================

SELECT 'CURRENT CONTENT COUNTS:' as info;

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
-- SAMPLE CONTENT TO BE DELETED
-- ========================================

SELECT 'SAMPLE AI-GENERATED QUESTIONS TO BE DELETED:' as info;
SELECT 
    id,
    section,
    subsection,
    difficulty,
    created_at
FROM ai_generated_questions 
ORDER BY created_at DESC 
LIMIT 5;

SELECT 'SAMPLE AI-GENERATED READING PASSAGES TO BE DELETED:' as info;
SELECT 
    id,
    passage_type,
    created_at
FROM ai_generated_reading_passages 
ORDER BY created_at DESC 
LIMIT 5;

SELECT 'SAMPLE AI-GENERATED WRITING PROMPTS TO BE DELETED:' as info;
SELECT 
    id,
    created_at
FROM ai_generated_writing_prompts 
ORDER BY created_at DESC 
LIMIT 5;

-- ========================================
-- USER USAGE STATISTICS
-- ========================================

SELECT 'USER USAGE STATISTICS (will be reset):' as info;
SELECT 
    content_type,
    COUNT(*) as usage_count,
    COUNT(DISTINCT user_id) as unique_users
FROM user_question_usage 
GROUP BY content_type
ORDER BY content_type;

-- ========================================
-- TRAINING EXAMPLES AVAILABLE
-- ========================================

SELECT 'TRAINING EXAMPLES AVAILABLE FOR REGENERATION:' as info;

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
-- DELETION ORDER PREVIEW
-- ========================================

SELECT 'DELETION ORDER (due to foreign key constraints):' as info;
SELECT '1. user_question_usage (references AI content IDs)' as step_1;
SELECT '2. ai_generated_reading_questions (references reading passages)' as step_2;
SELECT '3. ai_generated_reading_passages (referenced by reading questions)' as step_3;
SELECT '4. ai_generated_questions (standalone questions)' as step_4;
SELECT '5. ai_generated_writing_prompts (standalone writing prompts)' as step_5;
SELECT '6. ai_generation_sessions (session tracking - optional)' as step_6;
