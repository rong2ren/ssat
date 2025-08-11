-- ========================================
-- HYBRID FUNCTIONS - CLEAN IMPLEMENTATION
-- ========================================
-- Add new unified hybrid functions and remove unused functions

-- ========================================
-- 1. NEW HYBRID FUNCTIONS
-- ========================================

-- Unified function: Get training examples with hybrid approach
CREATE OR REPLACE FUNCTION get_training_examples_hybrid(
    topic_filter TEXT DEFAULT NULL,
    section_filter TEXT DEFAULT NULL,
    subsection_filter TEXT DEFAULT NULL,
    difficulty_filter TEXT DEFAULT NULL,
    query_embedding VECTOR(384) DEFAULT NULL,
    limit_count INT DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    question TEXT,
    choices TEXT[],
    answer INTEGER,
    explanation TEXT,
    difficulty TEXT,
    subsection TEXT,
    visual_description TEXT,
    similarity REAL,
    search_method TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- If topic and embedding provided, try embedding search first
    IF topic_filter IS NOT NULL AND query_embedding IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            q.id,
            q.question,
            q.choices,
            q.answer,
            q.explanation,
            q.difficulty,
            q.subsection,
            q.visual_description,
            (1 - (q.embedding <=> query_embedding))::REAL as similarity,
            'embedding'::TEXT as search_method
        FROM ssat_questions q
        WHERE 
            q.embedding IS NOT NULL
            AND (section_filter IS NULL OR q.section = section_filter)
            AND (subsection_filter IS NULL OR q.subsection = subsection_filter)
            AND (difficulty_filter IS NULL OR q.difficulty = difficulty_filter)
        ORDER BY q.embedding <=> query_embedding
        LIMIT limit_count;
        
        IF FOUND THEN RETURN; END IF;
    END IF;
    
    -- Fallback: try text-based topic filtering
    IF topic_filter IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            q.id,
            q.question,
            q.choices,
            q.answer,
            q.explanation,
            q.difficulty,
            q.subsection,
            q.visual_description,
            0.6::REAL as similarity,
            'text'::TEXT as search_method
        FROM ssat_questions q
        WHERE 
            (section_filter IS NULL OR q.section = section_filter)
            AND (subsection_filter IS NULL OR q.subsection = subsection_filter)
            AND (difficulty_filter IS NULL OR q.difficulty = difficulty_filter)
            AND (
                q.question ILIKE '%' || topic_filter || '%'
                OR q.subsection ILIKE '%' || topic_filter || '%'
                OR q.tags::TEXT ILIKE '%' || topic_filter || '%'
            )
        ORDER BY RANDOM()
        LIMIT limit_count;
        
        IF FOUND THEN RETURN; END IF;
    END IF;
    
    -- Final fallback: get random examples by section
    RETURN QUERY
    SELECT 
        q.id,
        q.question,
        q.choices,
        q.answer,
        q.explanation,
        q.difficulty,
        q.subsection,
        q.visual_description,
        0.5::REAL as similarity,
        'random'::TEXT as search_method
    FROM ssat_questions q
    WHERE 
        (section_filter IS NULL OR q.section = section_filter)
        AND (subsection_filter IS NULL OR q.subsection = subsection_filter)
        AND (difficulty_filter IS NULL OR q.difficulty = difficulty_filter)
    ORDER BY RANDOM()
    LIMIT limit_count;
END;
$$;

-- Unified function: Get reading training examples with hybrid approach
CREATE OR REPLACE FUNCTION get_reading_training_examples_hybrid(
    topic_filter TEXT DEFAULT NULL,
    passage_type_filter TEXT DEFAULT NULL,
    query_embedding VECTOR(384) DEFAULT NULL,
    limit_count INT DEFAULT 3
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
    similarity REAL,
    search_method TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- If topic and embedding provided, try embedding search first
    IF topic_filter IS NOT NULL AND query_embedding IS NOT NULL THEN
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
            (1 - (rp.embedding <=> query_embedding))::REAL as similarity,
            'embedding'::TEXT as search_method
        FROM reading_passages rp
        JOIN reading_questions rq ON rp.id = rq.passage_id
        WHERE 
            rp.embedding IS NOT NULL
            AND (passage_type_filter IS NULL OR rp.passage_type = passage_type_filter)
        ORDER BY rp.embedding <=> query_embedding
        LIMIT limit_count;
        
        IF FOUND THEN RETURN; END IF;
    END IF;
    
    -- Fallback: try text-based topic filtering
    IF topic_filter IS NOT NULL THEN
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
            0.6::REAL as similarity,
            'text'::TEXT as search_method
        FROM reading_passages rp
        JOIN reading_questions rq ON rp.id = rq.passage_id
        WHERE 
            (passage_type_filter IS NULL OR rp.passage_type = passage_type_filter)
            AND (
                rp.passage ILIKE '%' || topic_filter || '%'
                OR rp.tags::TEXT ILIKE '%' || topic_filter || '%'
                OR rq.question ILIKE '%' || topic_filter || '%'
            )
        ORDER BY RANDOM()
        LIMIT limit_count;
        
        IF FOUND THEN RETURN; END IF;
    END IF;
    
    -- Final fallback: get random examples
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
        0.5::REAL as similarity,
        'random'::TEXT as search_method
    FROM reading_passages rp
    JOIN reading_questions rq ON rp.id = rq.passage_id
    WHERE 
        (passage_type_filter IS NULL OR rp.passage_type = passage_type_filter)
    ORDER BY RANDOM()
    LIMIT limit_count;
END;
$$;

-- Unified function: Get writing training examples with hybrid approach
CREATE OR REPLACE FUNCTION get_writing_training_examples_hybrid(
    topic_filter TEXT DEFAULT NULL,
    query_embedding VECTOR(384) DEFAULT NULL,
    limit_count INT DEFAULT 3
)
RETURNS TABLE (
    id TEXT,
    prompt TEXT,
    visual_description TEXT,
    tags TEXT[],
    similarity REAL,
    search_method TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- If topic and embedding provided, try embedding search first
    IF topic_filter IS NOT NULL AND query_embedding IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            wp.id,
            wp.prompt,
            wp.visual_description,
            wp.tags,
            (1 - (wp.embedding <=> query_embedding))::REAL as similarity,
            'embedding'::TEXT as search_method
        FROM writing_prompts wp
        WHERE 
            wp.embedding IS NOT NULL
        ORDER BY wp.embedding <=> query_embedding
        LIMIT limit_count;
        
        IF FOUND THEN RETURN; END IF;
    END IF;
    
    -- Fallback: try text-based topic filtering
    IF topic_filter IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            wp.id,
            wp.prompt,
            wp.visual_description,
            wp.tags,
            0.6::REAL as similarity,
            'text'::TEXT as search_method
        FROM writing_prompts wp
        WHERE 
            wp.prompt ILIKE '%' || topic_filter || '%'
        ORDER BY RANDOM()
        LIMIT limit_count;
        
        IF FOUND THEN RETURN; END IF;
    END IF;
    
    -- Final fallback: get random examples
    RETURN QUERY
    SELECT 
        wp.id,
        wp.prompt,
        wp.visual_description,
        wp.tags,
        0.5::REAL as similarity,
        'random'::TEXT as search_method
    FROM writing_prompts wp
    ORDER BY RANDOM()
    LIMIT limit_count;
END;
$$;

-- ========================================
-- 2. CLEANUP: REMOVE UNUSED FUNCTIONS
-- ========================================

-- Remove unused training example functions
DROP FUNCTION IF EXISTS get_training_examples_by_embedding(VECTOR(384), TEXT, TEXT, TEXT, INT);
DROP FUNCTION IF EXISTS get_training_examples_by_section(TEXT, TEXT, TEXT, INT);
DROP FUNCTION IF EXISTS get_training_examples_by_topic(TEXT, TEXT, TEXT, TEXT, INT);

-- Remove unused reading functions
DROP FUNCTION IF EXISTS get_reading_training_examples_by_embedding(VECTOR(384), TEXT, INT);
DROP FUNCTION IF EXISTS get_reading_training_examples_by_topic(TEXT, TEXT, INT);

-- Remove unused writing functions
DROP FUNCTION IF EXISTS get_writing_training_examples_by_embedding(VECTOR(384), INT);

-- Remove additional unused functions
DROP FUNCTION IF EXISTS get_reading_questions_for_passage(TEXT, INT);

-- ========================================
-- 3. CLEANUP: REMOVE UNUSED FUNCTION COMMENTS
-- ========================================

-- Remove comments for unused functions
COMMENT ON FUNCTION get_training_examples_by_embedding IS NULL;
COMMENT ON FUNCTION get_training_examples_by_topic IS NULL;
COMMENT ON FUNCTION get_reading_training_examples_by_embedding IS NULL;
COMMENT ON FUNCTION get_reading_training_examples_by_topic IS NULL;
COMMENT ON FUNCTION get_reading_questions_for_passage IS NULL;
COMMENT ON FUNCTION get_writing_training_examples_by_embedding IS NULL; 


❌ get_training_examples_by_embedding
❌ get_training_examples_by_topic
❌ get_reading_training_examples_by_embedding
❌ get_reading_training_examples_by_topic
❌ get_reading_questions_for_passage
❌ get_writing_training_examples_by_embedding