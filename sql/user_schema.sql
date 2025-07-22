-- ========================================
-- SIMPLIFIED USER SCHEMA
-- Uses only auth.users table with metadata
-- Following NestJS Supabase Auth approach
-- ========================================

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ========================================
-- FUNCTIONS
-- ========================================



-- Get user content generation statistics by section type
CREATE OR REPLACE FUNCTION get_user_content_count(p_user_id UUID)
RETURNS TABLE (
    quantitative_count INTEGER,
    analogy_count INTEGER,
    synonym_count INTEGER,
    reading_count INTEGER,
    writing_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)::INTEGER FROM ai_generated_questions WHERE generation_session_id IN
            (SELECT id FROM ai_generation_sessions WHERE user_id = p_user_id) AND section = 'Quantitative') as quantitative_count,
        (SELECT COUNT(*)::INTEGER FROM ai_generated_questions WHERE generation_session_id IN
            (SELECT id FROM ai_generation_sessions WHERE user_id = p_user_id) AND subsection = 'Analogies') as analogy_count,
        (SELECT COUNT(*)::INTEGER FROM ai_generated_questions WHERE generation_session_id IN
            (SELECT id FROM ai_generation_sessions WHERE user_id = p_user_id) AND subsection = 'Synonyms') as synonym_count,
        (SELECT COUNT(*)::INTEGER FROM ai_generated_reading_passages WHERE generation_session_id IN
            (SELECT id FROM ai_generation_sessions WHERE user_id = p_user_id)) as reading_count,
        (SELECT COUNT(*)::INTEGER FROM ai_generated_writing_prompts WHERE generation_session_id IN
            (SELECT id FROM ai_generation_sessions WHERE user_id = p_user_id)) as writing_count;
END;
$$;

-- ========================================
-- DEBUG QUERIES
-- ========================================

-- View all users with their metadata
-- SELECT 
--     id,
--     email,
--     raw_user_meta_data,
--     created_at,
--     last_sign_in_at
-- FROM auth.users 
-- WHERE deleted_at IS NULL;

-- Get user content statistics
-- SELECT * FROM get_user_content_count('user-uuid-here');

-- Get user's generation sessions
-- SELECT * FROM get_ai_generation_sessions('user-uuid-here', 10); 