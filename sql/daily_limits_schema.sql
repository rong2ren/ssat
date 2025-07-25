-- ========================================
-- DAILY LIMITS SCHEMA
-- Simple, clean implementation for SSAT section-based limits
-- ========================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- DAILY LIMITS TABLE
-- ========================================

-- Track daily usage limits for each user by SSAT section
CREATE TABLE IF NOT EXISTS user_daily_limits (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    last_reset_date DATE NOT NULL DEFAULT CURRENT_DATE,
    quantitative_generated INTEGER DEFAULT 0,
    analogy_generated INTEGER DEFAULT 0,
    synonyms_generated INTEGER DEFAULT 0,
    reading_passages_generated INTEGER DEFAULT 0,
    writing_generated INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_daily_limits_user_date ON user_daily_limits(user_id, last_reset_date);

-- ========================================
-- DAILY LIMITS FUNCTIONS
-- ========================================

-- Get or create user daily limits record with automatic reset
CREATE OR REPLACE FUNCTION get_or_create_user_daily_limits(p_user_id UUID)
RETURNS TABLE (
    user_id UUID,
    last_reset_date DATE,
    quantitative_generated INTEGER,
    analogy_generated INTEGER,
    synonyms_generated INTEGER,
    reading_passages_generated INTEGER,
    writing_generated INTEGER,
    needs_reset BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    today_date DATE := CURRENT_DATE;
    record_exists BOOLEAN;
    current_record RECORD;
BEGIN
    -- Check if record exists
    SELECT EXISTS(SELECT 1 FROM user_daily_limits WHERE user_daily_limits.user_id = p_user_id) INTO record_exists;
    
    IF NOT record_exists THEN
        -- Create new record
        INSERT INTO user_daily_limits (user_id, last_reset_date)
        VALUES (p_user_id, today_date);
        
        RETURN QUERY
        SELECT 
            p_user_id,
            today_date,
            0, 0, 0, 0, 0,
            FALSE;
    ELSE
        -- Get existing record
        SELECT * INTO current_record 
        FROM user_daily_limits 
        WHERE user_daily_limits.user_id = p_user_id;
        
        -- Check if reset is needed
        IF current_record.last_reset_date < today_date THEN
            -- Reset counters
            UPDATE user_daily_limits 
            SET 
                quantitative_generated = 0,
                analogy_generated = 0,
                synonyms_generated = 0,
                reading_passages_generated = 0,
                writing_generated = 0,
                last_reset_date = today_date,
                updated_at = NOW()
            WHERE user_daily_limits.user_id = p_user_id;
            
            RETURN QUERY
            SELECT 
                p_user_id,
                today_date,
                0, 0, 0, 0, 0,
                TRUE;
        ELSE
            -- No reset needed
            RETURN QUERY
            SELECT 
                current_record.user_id,
                current_record.last_reset_date,
                current_record.quantitative_generated,
                current_record.analogy_generated,
                current_record.synonyms_generated,
                current_record.reading_passages_generated,
                current_record.writing_generated,
                FALSE;
        END IF;
    END IF;
END;
$$;

-- Increment user daily usage for a specific section
-- Note: This function only handles the increment operation
-- Limit checking is done in the Python service
CREATE OR REPLACE FUNCTION increment_user_daily_usage(
    p_user_id UUID,
    p_section TEXT,
    p_amount INTEGER DEFAULT 1
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    current_usage RECORD;
BEGIN
    -- Validate input
    IF p_amount <= 0 THEN
        RETURN FALSE; -- Invalid amount
    END IF;
    
    -- Get current usage (with automatic reset if needed)
    SELECT * INTO current_usage 
    FROM get_or_create_user_daily_limits(p_user_id);
    
    -- Increment usage for the specified section by the specified amount
    CASE p_section
        WHEN 'quantitative' THEN
            UPDATE user_daily_limits 
            SET quantitative_generated = quantitative_generated + p_amount, updated_at = NOW()
            WHERE user_daily_limits.user_id = p_user_id;
        WHEN 'analogy' THEN
            UPDATE user_daily_limits 
            SET analogy_generated = analogy_generated + p_amount, updated_at = NOW()
            WHERE user_daily_limits.user_id = p_user_id;
        WHEN 'synonyms' THEN
            UPDATE user_daily_limits 
            SET synonyms_generated = synonyms_generated + p_amount, updated_at = NOW()
            WHERE user_daily_limits.user_id = p_user_id;
        WHEN 'reading_passages' THEN
            UPDATE user_daily_limits 
            SET reading_passages_generated = reading_passages_generated + p_amount, updated_at = NOW()
            WHERE user_daily_limits.user_id = p_user_id;
        WHEN 'writing' THEN
            UPDATE user_daily_limits 
            SET writing_generated = writing_generated + p_amount, updated_at = NOW()
            WHERE user_daily_limits.user_id = p_user_id;
        ELSE
            RETURN FALSE; -- Invalid section
    END CASE;
    
    RETURN TRUE; -- Success
END;
$$;

-- Batched increment for multiple sections at once
CREATE OR REPLACE FUNCTION increment_user_daily_usage_batch(
    p_user_id UUID,
    p_sections TEXT[],
    p_amounts INTEGER[]
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    i INTEGER;
    section TEXT;
    amount INTEGER;
    success BOOLEAN := TRUE;
BEGIN
    IF array_length(p_sections, 1) IS DISTINCT FROM array_length(p_amounts, 1) THEN
        RETURN FALSE; -- Mismatched array lengths
    END IF;
    
    FOR i IN 1..array_length(p_sections, 1) LOOP
        section := p_sections[i];
        amount := p_amounts[i];
        IF amount <= 0 THEN
            CONTINUE;
        END IF;
        -- Use the single-section increment function for each
        PERFORM increment_user_daily_usage(p_user_id, section, amount);
    END LOOP;
    RETURN success;
END;
$$;

-- True batch increment for all sections in one call
CREATE OR REPLACE FUNCTION increment_user_daily_limits(
    p_user_id UUID,
    p_quantitative INTEGER DEFAULT 0,
    p_analogy INTEGER DEFAULT 0,
    p_synonyms INTEGER DEFAULT 0,
    p_reading_passages INTEGER DEFAULT 0,
    p_writing INTEGER DEFAULT 0
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE user_daily_limits
    SET
        quantitative_generated = quantitative_generated + p_quantitative,
        analogy_generated = analogy_generated + p_analogy,
        synonyms_generated = synonyms_generated + p_synonyms,
        reading_passages_generated = reading_passages_generated + p_reading_passages,
        writing_generated = writing_generated + p_writing,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$;


-- ========================================
-- DEBUG QUERIES
-- ========================================

-- Get user's current daily limits usage
-- SELECT * FROM get_or_create_user_daily_limits('user-uuid-here');

-- Test incrementing usage (returns true if successful, false if invalid section)
-- SELECT increment_user_daily_usage('user-uuid-here', 'quantitative');

-- View all user daily limits
-- SELECT 
--     ul.user_id,
--     u.email,
--     ul.last_reset_date,
--     ul.quantitative_generated,
--     ul.analogy_generated,
--     ul.synonyms_generated,
--     ul.reading_passages_generated,
--     ul.writing_generated,
--     ul.updated_at
-- FROM user_daily_limits ul
-- JOIN auth.users u ON ul.user_id = u.id
-- ORDER BY ul.updated_at DESC;

-- Reset all user limits (for testing)
-- UPDATE user_daily_limits 
-- SET 
--     quantitative_generated = 0,
--     analogy_generated = 0,
--     synonyms_generated = 0,
--     reading_passages_generated = 0,
--     writing_generated = 0,
--     last_reset_date = CURRENT_DATE,
--     updated_at = NOW(); 