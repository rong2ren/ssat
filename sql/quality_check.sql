-- ========================================
-- QUALITY CHECK AND CLEANUP SCRIPT
-- For SSAT Training Examples Database
-- ========================================

-- ========================================
-- FIND EXACT DUPLICATES
-- ========================================

-- Find exact duplicates by question text
SELECT 
    question, 
    COUNT(*) as count, 
    array_agg(id) as ids,
    array_agg(subsection) as subsections,
    array_agg(difficulty) as difficulties
FROM ssat_questions 
GROUP BY question 
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- ========================================
-- delete orphaned reading questions
-- ========================================

SELECT arq.id, arq.question, arq.passage_id, 'orphaned_question' as issue
FROM ai_generated_reading_questions arq
LEFT JOIN reading_passages rp ON arq.passage_id = rp.id
WHERE rp.id IS NULL;


DELETE FROM ai_generated_reading_questions 
WHERE id IN (
    SELECT arq.id
    FROM ai_generated_reading_questions arq
    LEFT JOIN reading_passages rp ON arq.passage_id = rp.id
    WHERE rp.id IS NULL
);


-- Find any remaining non-standardized subsections
SELECT DISTINCT subsection 
FROM ssat_questions 
WHERE section = 'Quantitative' 
AND subsection NOT IN (
    'Number Sense', 'Arithmetic', 'Fractions', 'Decimals', 'Percentages',
    'Patterns', 'Sequences', 'Algebra', 'Variables',
    'Area', 'Perimeter', 'Shapes', 'Spatial',
    'Measurement', 'Time', 'Money',
    'Probability', 'Data', 'Graphs'
);

-- If any found, update them to 'Arithmetic' as default
-- UPDATE ssat_questions 
-- SET subsection = 'Arithmetic'
-- WHERE section = 'Quantitative' 
-- AND subsection NOT IN (
--     'Number Sense', 'Arithmetic', 'Fractions', 'Decimals', 'Percentages',
--     'Patterns', 'Sequences', 'Algebra', 'Variables',
--     'Area', 'Perimeter', 'Shapes', 'Spatial',
--     'Measurement', 'Time', 'Money',
--     'Probability', 'Data', 'Graphs'
-- ); 


-- ========================================
-- READING DATA INVESTIGATION QUERIES
-- ========================================
-- Queries to investigate reading passages vs questions discrepancy

-- ========================================
-- 1. BASIC COUNTS
-- ========================================

-- Get basic counts
SELECT 
    'Total Passages' as type,
    COUNT(*) as count
FROM reading_passages
UNION ALL
SELECT 
    'Total Reading Questions' as type,
    COUNT(*) as count
FROM reading_questions
ORDER BY type;

-- ========================================
-- 2. QUESTIONS PER PASSAGE DISTRIBUTION
-- ========================================

-- Show how many questions each passage has
SELECT 
    p.id as passage_id,
    COUNT(q.id) as question_count
FROM reading_passages p
LEFT JOIN reading_questions q ON p.id = q.passage_id
GROUP BY p.id
ORDER BY question_count DESC, p.id;

-- ========================================
-- 3. PASSAGES WITH UNUSUAL QUESTION COUNTS
-- ========================================

-- Passages with more than 5 questions
SELECT 
    'Passages with >5 questions' as category,
    COUNT(*) as passage_count
FROM (
    SELECT 
        p.id,
        COUNT(q.id) as question_count
    FROM reading_passages p
    LEFT JOIN reading_questions q ON p.id = q.passage_id
    GROUP BY p.id
    HAVING COUNT(q.id) > 5
) subq
UNION ALL
-- Passages with no questions
SELECT 
    'Passages with 0 questions' as category,
    COUNT(*) as passage_count
FROM (
    SELECT 
        p.id,
        COUNT(q.id) as question_count
    FROM reading_passages p
    LEFT JOIN reading_questions q ON p.id = q.passage_id
    GROUP BY p.id
    HAVING COUNT(q.id) = 0
) subq
UNION ALL
-- Passages with 1-2 questions (unusually low)
SELECT 
    'Passages with 1-2 questions' as category,
    COUNT(*) as passage_count
FROM (
    SELECT 
        p.id,
        COUNT(q.id) as question_count
    FROM reading_passages p
    LEFT JOIN reading_questions q ON p.id = q.passage_id
    GROUP BY p.id
    HAVING COUNT(q.id) BETWEEN 1 AND 2
) subq
ORDER BY category;

-- ========================================
-- 4. ORPHANED QUESTIONS
-- ========================================

-- Questions without a valid passage (orphaned questions)
SELECT 
    q.id as question_id,
    q.passage_id as referenced_passage_id,
    q.question,
    'ORPHANED - passage does not exist' as issue
FROM reading_questions q
LEFT JOIN reading_passages p ON q.passage_id = p.id
WHERE p.id IS NULL
ORDER BY q.id;

-- ========================================
-- 5. DETAILED BREAKDOWN BY QUESTION COUNT
-- ========================================

-- Count of passages by number of questions they have
SELECT 
    question_count,
    COUNT(*) as passages_with_this_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM (
    SELECT 
        p.id,
        COUNT(q.id) as question_count
    FROM reading_passages p
    LEFT JOIN reading_questions q ON p.id = q.passage_id
    GROUP BY p.id
) subq
GROUP BY question_count
ORDER BY question_count;

-- ========================================
-- 6. PASSAGES WITH MOST QUESTIONS (TOP 10)
-- ========================================

-- Show the top 10 passages with most questions
SELECT 
    p.id as passage_id,
    COALESCE(p.title, 'No Title') as title,
    LEFT(p.passage, 100) || '...' as passage_preview,
    COUNT(q.id) as question_count
FROM reading_passages p
LEFT JOIN reading_questions q ON p.id = q.passage_id
GROUP BY p.id, p.title, p.passage
ORDER BY question_count DESC, p.id
LIMIT 10;

-- ========================================
-- 7. VERIFY REFERENTIAL INTEGRITY
-- ========================================

-- Check for any referential integrity issues
SELECT 
    'Total Questions' as metric,
    COUNT(*) as value
FROM reading_questions
UNION ALL
SELECT 
    'Questions with Valid Passages' as metric,
    COUNT(*) as value
FROM reading_questions q
INNER JOIN reading_passages p ON q.passage_id = p.id
UNION ALL
SELECT 
    'Questions with Invalid Passages' as metric,
    COUNT(*) as value
FROM reading_questions q
LEFT JOIN reading_passages p ON q.passage_id = p.id
WHERE p.id IS NULL
ORDER BY metric;

-- ========================================
-- 8. SAMPLE OF PASSAGES WITH MANY QUESTIONS
-- ========================================

-- Show details of passages that have 8+ questions
SELECT 
    p.id as passage_id,
    COALESCE(p.title, 'No Title') as title,
    p.passage_type,
    COUNT(q.id) as question_count,
    ARRAY_AGG(q.id ORDER BY q.id) as question_ids
FROM reading_passages p
INNER JOIN reading_questions q ON p.id = q.passage_id
GROUP BY p.id, p.title, p.passage_type
HAVING COUNT(q.id) >= 8
ORDER BY question_count DESC, p.id; 