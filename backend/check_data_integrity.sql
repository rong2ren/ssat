-- ========================================
-- DATA INTEGRITY CHECK QUERIES
-- Check for orphaned questions and empty passages
-- ========================================

-- 1. QUESTIONS WITHOUT PASSAGES (orphaned questions)
-- These are questions that reference a passage_id that doesn't exist
SELECT 
    'Questions without passages' as issue_type,
    COUNT(*) as count,
    'These questions reference non-existent passages' as description
FROM ai_generated_reading_questions rq
LEFT JOIN ai_generated_reading_passages rp ON rq.passage_id = rp.id
WHERE rp.id IS NULL

UNION ALL

-- 2. PASSAGES WITHOUT QUESTIONS (empty passages)
-- These are passages that have no associated questions
SELECT 
    'Passages without questions' as issue_type,
    COUNT(*) as count,
    'These passages have no associated questions' as description
FROM ai_generated_reading_passages rp
LEFT JOIN ai_generated_reading_questions rq ON rp.id = rq.passage_id
WHERE rq.id IS NULL

UNION ALL

-- 3. TOTAL PASSAGES
SELECT 
    'Total passages' as issue_type,
    COUNT(*) as count,
    'All passages in the database' as description
FROM ai_generated_reading_passages

UNION ALL

-- 4. TOTAL QUESTIONS
SELECT 
    'Total questions' as issue_type,
    COUNT(*) as count,
    'All questions in the database' as description
FROM ai_generated_reading_questions

UNION ALL

-- 5. PASSAGES WITH QUESTIONS
SELECT 
    'Passages with questions' as issue_type,
    COUNT(DISTINCT rp.id) as count,
    'Passages that have at least one question' as description
FROM ai_generated_reading_passages rp
INNER JOIN ai_generated_reading_questions rq ON rp.id = rq.passage_id

ORDER BY issue_type;

-- ========================================
-- DETAILED BREAKDOWN QUERIES
-- ========================================

-- Show sample orphaned questions (if any)
-- Uncomment to see details:
/*
SELECT 
    'Sample orphaned questions:' as info,
    rq.id as question_id,
    rq.passage_id as missing_passage_id,
    rq.question,
    rq.difficulty,
    rq.created_at
FROM ai_generated_reading_questions rq
LEFT JOIN ai_generated_reading_passages rp ON rq.passage_id = rp.id
WHERE rp.id IS NULL
LIMIT 10;
*/

-- Show sample empty passages (if any)
-- Uncomment to see details:
/*
SELECT 
    'Sample empty passages:' as info,
    rp.id as passage_id,
    rp.passage_type,
    rp.created_at,
    rp.generation_session_id
FROM ai_generated_reading_passages rp
LEFT JOIN ai_generated_reading_questions rq ON rp.id = rq.passage_id
WHERE rq.id IS NULL
ORDER BY rp.created_at DESC
LIMIT 10;
*/

-- ========================================
-- QUESTION DISTRIBUTION BY PASSAGE
-- ========================================

-- Show how many questions each passage has
SELECT 
    'Question distribution by passage:' as info,
    COUNT(rq.id) as questions_per_passage,
    COUNT(*) as number_of_passages
FROM ai_generated_reading_passages rp
LEFT JOIN ai_generated_reading_questions rq ON rp.id = rq.passage_id
GROUP BY rp.id
ORDER BY questions_per_passage DESC;

-- ========================================
-- CLEANUP QUERIES (use with caution!)
-- ========================================

-- Delete orphaned questions (questions without passages)
-- WARNING: This will permanently delete data!
-- Uncomment and run only if you want to clean up orphaned questions:
/*
DELETE FROM ai_generated_reading_questions 
WHERE passage_id NOT IN (
    SELECT id FROM ai_generated_reading_passages
);
*/

-- Delete empty passages (passages without questions)
-- WARNING: This will permanently delete data!
-- Uncomment and run only if you want to clean up empty passages:
/*
DELETE FROM ai_generated_reading_passages 
WHERE id NOT IN (
    SELECT DISTINCT passage_id FROM ai_generated_reading_questions
);
*/
