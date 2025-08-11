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