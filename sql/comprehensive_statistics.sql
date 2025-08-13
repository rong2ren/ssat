-- ========================================
-- MVP STATISTICS SYSTEM - DEVELOPMENT PHASE
-- ========================================
-- Simplified statistics for development and early testing
-- Only includes essential metrics needed before real users

-- ========================================
-- BASIC INDEXES (Essential only)
-- ========================================

-- Critical indexes for the functions we're actually using
CREATE INDEX IF NOT EXISTS idx_ai_sessions_created_at ON ai_generation_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_sessions_status ON ai_generation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_ai_questions_created_at ON ai_generated_questions(created_at);

-- ========================================
-- 1. PLATFORM OVERVIEW - MVP VERSION
-- ========================================

CREATE OR REPLACE FUNCTION get_platform_overview_statistics()
RETURNS TABLE (
    -- Basic User Count
    total_users BIGINT,
    
    -- Content Inventory
    total_training_content BIGINT,
    total_ai_generated_content BIGINT,
    
    -- System Health (Essential)
    total_generation_sessions BIGINT,
    successful_generations_last_7_days BIGINT,
    failed_generations_last_7_days BIGINT,
    success_rate_percentage DECIMAL(5,2)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY SELECT 
        -- Basic User Count - Use user_daily_limits instead of auth.users
        (SELECT COUNT(DISTINCT user_id) FROM user_daily_limits)::BIGINT,
        
        -- Content Inventory
        ((SELECT COUNT(*) FROM ssat_questions) + 
         (SELECT COUNT(*) FROM reading_passages) + 
         (SELECT COUNT(*) FROM reading_questions) + 
         (SELECT COUNT(*) FROM writing_prompts))::BIGINT,
        ((SELECT COUNT(*) FROM ai_generated_questions) + 
         (SELECT COUNT(*) FROM ai_generated_reading_passages) + 
         (SELECT COUNT(*) FROM ai_generated_reading_questions) + 
         (SELECT COUNT(*) FROM ai_generated_writing_prompts))::BIGINT,
        
        -- System Health (Essential for development)
        (SELECT COUNT(*) FROM ai_generation_sessions)::BIGINT,
        (SELECT COUNT(*) FROM ai_generation_sessions WHERE status = 'completed' AND created_at >= NOW() - INTERVAL '7 days')::BIGINT,
        (SELECT COUNT(*) FROM ai_generation_sessions WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '7 days')::BIGINT,
        (SELECT 
            CASE 
                WHEN COUNT(*) > 0 THEN 
                    ROUND((COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*)), 2)
                ELSE 0.00 
            END
         FROM ai_generation_sessions)::DECIMAL(5,2);
END;
$$;

-- ========================================
-- 2. CONTENT BREAKDOWN - MVP VERSION
-- ========================================

CREATE OR REPLACE FUNCTION get_content_breakdown_statistics()
RETURNS TABLE (
    -- Training Content by Type
    training_quantitative BIGINT,
    training_analogies BIGINT,
    training_synonyms BIGINT,
    training_reading_passages BIGINT,
    training_reading_questions BIGINT,
    training_writing_prompts BIGINT,
    
    -- AI Generated Content by Type
    ai_quantitative BIGINT,
    ai_analogies BIGINT,
    ai_synonyms BIGINT,
    ai_reading_passages BIGINT,
    ai_reading_questions BIGINT,
    ai_writing_prompts BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY SELECT 
        -- Training Content by Type
        (SELECT COUNT(*) FROM ssat_questions WHERE section = 'Quantitative')::BIGINT,
        (SELECT COUNT(*) FROM ssat_questions WHERE subsection = 'Analogies')::BIGINT,
        (SELECT COUNT(*) FROM ssat_questions WHERE subsection = 'Synonyms')::BIGINT,
        (SELECT COUNT(*) FROM reading_passages)::BIGINT,
        (SELECT COUNT(*) FROM reading_questions)::BIGINT,
        (SELECT COUNT(*) FROM writing_prompts)::BIGINT,
        
        -- AI Generated Content by Type
        (SELECT COUNT(*) FROM ai_generated_questions WHERE section = 'Quantitative')::BIGINT,
        (SELECT COUNT(*) FROM ai_generated_questions WHERE subsection = 'Analogies')::BIGINT,
        (SELECT COUNT(*) FROM ai_generated_questions WHERE subsection = 'Synonyms')::BIGINT,
        (SELECT COUNT(*) FROM ai_generated_reading_passages)::BIGINT,
        (SELECT COUNT(*) FROM ai_generated_reading_questions)::BIGINT,
        (SELECT COUNT(*) FROM ai_generated_writing_prompts)::BIGINT;
END;
$$;

-- ========================================
-- 3. POOL USAGE - MVP VERSION
-- ========================================

CREATE OR REPLACE FUNCTION get_pool_utilization_statistics()
RETURNS TABLE (
    -- All Content Types: Used and Remaining
    quantitative_used BIGINT,
    quantitative_remaining BIGINT,
    analogy_used BIGINT,
    analogy_remaining BIGINT,
    synonym_used BIGINT,
    synonym_remaining BIGINT,
    reading_used BIGINT,
    reading_remaining BIGINT,
    writing_used BIGINT,
    writing_remaining BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    quant_total BIGINT;
    quant_used BIGINT;
    anal_total BIGINT;
    anal_used BIGINT;
    syn_total BIGINT;
    syn_used BIGINT;
    reading_total BIGINT;
    reading_used BIGINT;
    writing_total BIGINT;
    writing_used BIGINT;
BEGIN
    -- Get totals by content type
    SELECT COUNT(*) INTO quant_total FROM ai_generated_questions WHERE section = 'Quantitative';
    SELECT COUNT(*) INTO anal_total FROM ai_generated_questions WHERE subsection = 'Analogies';
    SELECT COUNT(*) INTO syn_total FROM ai_generated_questions WHERE subsection = 'Synonyms';
    SELECT COUNT(*) INTO reading_total FROM ai_generated_reading_passages;
    SELECT COUNT(*) INTO writing_total FROM ai_generated_writing_prompts;
    
    -- Get used counts by content type (only AI-generated content)
    SELECT COUNT(DISTINCT uqu.question_id) INTO quant_used 
    FROM user_question_usage uqu
    JOIN ai_generated_questions agq ON uqu.question_id = agq.id::text
    WHERE uqu.content_type = 'quantitative' AND agq.section = 'Quantitative' AND uqu.question_id IS NOT NULL;
    
    SELECT COUNT(DISTINCT uqu.question_id) INTO anal_used 
    FROM user_question_usage uqu
    JOIN ai_generated_questions agq ON uqu.question_id = agq.id::text
    WHERE uqu.content_type = 'analogy' AND agq.subsection = 'Analogies' AND uqu.question_id IS NOT NULL;
    
    SELECT COUNT(DISTINCT uqu.question_id) INTO syn_used 
    FROM user_question_usage uqu
    JOIN ai_generated_questions agq ON uqu.question_id = agq.id::text
    WHERE uqu.content_type = 'synonym' AND agq.subsection = 'Synonyms' AND uqu.question_id IS NOT NULL;
    
    SELECT COUNT(DISTINCT uqu.question_id) INTO reading_used 
    FROM user_question_usage uqu
    JOIN ai_generated_reading_passages agp ON uqu.question_id = agp.id::text
    WHERE uqu.content_type = 'reading' AND uqu.question_id IS NOT NULL;
    
    SELECT COUNT(DISTINCT uqu.question_id) INTO writing_used 
    FROM user_question_usage uqu
    JOIN ai_generated_writing_prompts awp ON uqu.question_id = awp.id::text
    WHERE uqu.content_type = 'writing' AND uqu.question_id IS NOT NULL;
    
    RETURN QUERY SELECT 
        -- All Content Types: Used and Remaining
        COALESCE(quant_used, 0)::BIGINT,
        (quant_total - COALESCE(quant_used, 0))::BIGINT,
        COALESCE(anal_used, 0)::BIGINT,
        (anal_total - COALESCE(anal_used, 0))::BIGINT,
        COALESCE(syn_used, 0)::BIGINT,
        (syn_total - COALESCE(syn_used, 0))::BIGINT,
        COALESCE(reading_used, 0)::BIGINT,
        (reading_total - COALESCE(reading_used, 0))::BIGINT,
        COALESCE(writing_used, 0)::BIGINT,
        (writing_total - COALESCE(writing_used, 0))::BIGINT;
END;
$$;

-- ========================================
-- FUTURE FUNCTIONS (COMMENTED OUT)
-- ========================================
-- Uncomment and deploy these when you have real users and need the metrics

/*
-- 4. USER ACTIVITY STATISTICS (Deploy when you have 10+ active users)
-- 5. PERFORMANCE & SYSTEM HEALTH (Deploy when you have 100+ generations/day)  
-- 6. DAILY TRENDS (Deploy after 30+ days of real user activity)
*/ 