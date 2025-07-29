-- ========================================
-- USER QUESTION USAGE TRACKING SCHEMA
-- Tracks which questions each user has used (permanent tracking)
-- ========================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- USER QUESTION USAGE TABLE
-- ========================================

-- Track which questions each user has used (permanent tracking)
CREATE TABLE IF NOT EXISTS user_question_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,                  -- ID from existing ai_generated_* tables
    content_type TEXT NOT NULL,                 -- 'quantitative', 'analogy', 'synonym', 'reading', 'writing'
    usage_type TEXT NOT NULL,                   -- 'full_test', 'custom_section'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, question_id)                -- Prevent duplicate usage EVER
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Fast lookups by user
CREATE INDEX IF NOT EXISTS idx_user_question_usage_user_id ON user_question_usage(user_id);

-- Fast lookups by question_id
CREATE INDEX IF NOT EXISTS idx_user_question_usage_question_id ON user_question_usage(question_id);

-- Fast lookups by content type
CREATE INDEX IF NOT EXISTS idx_user_question_usage_content_type ON user_question_usage(content_type);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_user_question_usage_user_content ON user_question_usage(user_id, content_type);

-- ========================================
-- UTILITY FUNCTIONS
-- ========================================

-- Get questions a user has never used before
CREATE OR REPLACE FUNCTION get_unused_questions_for_user(
    p_user_id UUID,
    p_section TEXT DEFAULT NULL,
    p_difficulty TEXT DEFAULT NULL,
    p_subsection TEXT DEFAULT NULL,
    p_limit_count INT DEFAULT 20
)
RETURNS TABLE (
    id TEXT,
    question TEXT,
    choices TEXT[],
    answer INTEGER,
    explanation TEXT,
    difficulty TEXT,
    section TEXT,
    subsection TEXT,
    generation_session_id TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.id,
        q.question,
        q.choices,
        q.answer,
        q.explanation,
        q.difficulty,
        q.section,
        q.subsection,
        q.generation_session_id,
        q.created_at
    FROM ai_generated_questions q
    WHERE 
        (p_section IS NULL OR q.section = p_section)
        AND (p_difficulty IS NULL OR q.difficulty = p_difficulty)
        AND (p_subsection IS NULL OR q.subsection = p_subsection)
        AND NOT EXISTS (
            SELECT 1 
            FROM user_question_usage uqu 
            WHERE uqu.user_id = p_user_id 
              AND uqu.content_type IN ('quantitative', 'analogy', 'synonym')
              AND uqu.question_id = q.id
        )
    ORDER BY q.created_at DESC
    LIMIT p_limit_count;
END;
$$;

-- Get reading content a user has never used before
CREATE OR REPLACE FUNCTION get_unused_reading_content_for_user(
    p_user_id UUID,
    p_limit_count INT DEFAULT 10
)
RETURNS TABLE (
    passage_id TEXT,
    passage TEXT,
    passage_type TEXT,
    question_id TEXT,
    question TEXT,
    choices TEXT[],
    answer INTEGER,
    explanation TEXT,
    difficulty TEXT,
    visual_description TEXT,
    generation_session_id TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rp.id,
        rp.passage,
        rp.passage_type,
        rq.id,
        rq.question,
        rq.choices,
        rq.answer,
        rq.explanation,
        rq.difficulty,
        rq.visual_description,
        rp.generation_session_id,
        rp.created_at
    FROM ai_generated_reading_passages rp
    JOIN ai_generated_reading_questions rq ON rp.id = rq.passage_id
    WHERE 
        rp.id IN (
            -- Get N unused passages
            SELECT id FROM ai_generated_reading_passages 
            WHERE NOT EXISTS (
                SELECT 1 
                FROM user_question_usage uqu 
                WHERE uqu.user_id = p_user_id 
                  AND uqu.content_type = 'reading' 
                  AND uqu.question_id = ai_generated_reading_passages.id
            )
            LIMIT p_limit_count
        )
    ORDER BY rp.created_at DESC, rq.id;
END;
$$;

-- Get writing prompts a user has never used before
CREATE OR REPLACE FUNCTION get_unused_writing_prompts_for_user(
    p_user_id UUID,
    p_limit_count INT DEFAULT 10
)
RETURNS TABLE (
    id TEXT,
    prompt_text TEXT,
    visual_description TEXT,
    tags TEXT[],
    generation_session_id TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wp.id,
        wp.prompt as prompt_text,
        wp.visual_description,
        wp.tags,
        wp.generation_session_id,
        wp.created_at
    FROM ai_generated_writing_prompts wp
    WHERE 
        NOT EXISTS (
            SELECT 1 
            FROM user_question_usage uqu 
            WHERE uqu.user_id = p_user_id 
              AND uqu.content_type = 'writing' 
              AND uqu.question_id = wp.id
        )
    ORDER BY wp.created_at DESC
    LIMIT p_limit_count;
END;
$$;

-- ========================================
-- DEBUG QUERIES
-- ========================================

-- Get user's usage statistics
-- SELECT 
--     user_id,
--     content_type,
--     COUNT(*) as usage_count
-- FROM user_question_usage 
-- WHERE user_id = 'user-uuid-here'
-- GROUP BY user_id, content_type;

-- Get available questions for a user
-- SELECT * FROM get_unused_questions_for_user('user-uuid-here', 'Quantitative', 'Medium', 10);

-- Get available reading content for a user
-- SELECT * FROM get_unused_reading_content_for_user('user-uuid-here', 5);

-- Get available writing prompts for a user
-- SELECT * FROM get_unused_writing_prompts_for_user('user-uuid-here', 5); 