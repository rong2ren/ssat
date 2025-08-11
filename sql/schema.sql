-- SSAT Question Database Schema for Supabase
-- Optimized for AI training with real SSAT examples

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========================================
-- CORE TABLES
-- ========================================

-- Main questions table for Math and Verbal questions
CREATE TABLE ssat_questions (
    id TEXT PRIMARY KEY,                    -- e.g. "MATH-001", "VERBAL-002"
    source_file TEXT NOT NULL,              -- Original PDF filename
    section TEXT NOT NULL,                  -- "Quantitative", "Verbal"
    subsection TEXT NOT NULL,               -- "Fractions", "Synonyms", "Analogies", etc.
    question TEXT NOT NULL,                 -- The actual question text
    choices TEXT[],                         -- Array of multiple choice options
    answer INTEGER,                         -- 0-based index of correct choice
    explanation TEXT,                       -- Explanation of the correct answer
    difficulty TEXT,                        -- 'Easy', 'Medium', 'Hard'
    tags TEXT[],                            -- Array of tags for categorization
    visual_description TEXT,                -- Description of diagrams, charts, or visual elements
    embedding vector(384),                  -- For finding similar training examples
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reading comprehension passages
CREATE TABLE reading_passages (
    id TEXT PRIMARY KEY,                    -- e.g. "READING-PASSAGE-001"
    source_file TEXT NOT NULL,              -- Original PDF filename
    passage TEXT NOT NULL,                  -- The reading passage text
    passage_type TEXT,                      -- "Fiction", "Non-Fiction", "Poetry", "Science"
    embedding vector(384),                  -- For finding similar passages
    tags TEXT[],                            -- Array of tags
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reading comprehension questions (linked to passages)
CREATE TABLE reading_questions (
    id TEXT PRIMARY KEY,                    -- e.g. "READING-Q-001"
    passage_id TEXT NOT NULL REFERENCES reading_passages(id) ON DELETE CASCADE,
    question TEXT NOT NULL,                 -- The question text
    choices TEXT[],                         -- Array of multiple choice options
    answer INTEGER,                         -- 0-based index of correct choice
    explanation TEXT,                       -- Explanation of correct answer
    difficulty TEXT,                        -- 'Easy', 'Medium', 'Hard'
    tags TEXT[],                            -- Question-specific tags
    visual_description TEXT,                -- Description of visual elements in question
    embedding vector(384),                  -- For finding similar questions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Writing prompts table
CREATE TABLE writing_prompts (
    id TEXT PRIMARY KEY,                    -- e.g. "WRITING-001"
    source_file TEXT NOT NULL,              -- Original PDF filename
    prompt TEXT NOT NULL,                   -- The writing prompt text
    tags TEXT[],                            -- Array of tags
    visual_description TEXT,                -- Description of picture prompts or visual stimuli
    embedding vector(384),                  -- For finding similar prompts
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- ESSENTIAL INDEXES
-- ========================================

-- Basic lookup indexes
CREATE INDEX idx_question_section ON ssat_questions(section);
CREATE INDEX idx_question_subsection ON ssat_questions(subsection);
CREATE INDEX idx_question_difficulty ON ssat_questions(difficulty);
CREATE INDEX idx_reading_question_passage_id ON reading_questions(passage_id);
CREATE INDEX idx_reading_question_difficulty ON reading_questions(difficulty);
CREATE INDEX idx_passage_type ON reading_passages(passage_type);

-- Tag search indexes
CREATE INDEX idx_question_tags ON ssat_questions USING GIN(tags);
CREATE INDEX idx_passage_tags ON reading_passages USING GIN(tags);
CREATE INDEX idx_reading_question_tags ON reading_questions USING GIN(tags);
CREATE INDEX idx_writing_tags ON writing_prompts USING GIN(tags);

-- Critical: Embedding indexes for training example retrieval
CREATE INDEX idx_question_embedding ON ssat_questions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_passage_embedding ON reading_passages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_reading_question_embedding ON reading_questions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_writing_embedding ON writing_prompts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========================================
-- AI TRAINING FUNCTIONS
-- ========================================



-- Fallback function: Get training examples by section only (when no topic specified)
CREATE OR REPLACE FUNCTION get_training_examples_by_section(
    section_filter TEXT,
    subsection_filter TEXT DEFAULT NULL,
    difficulty_filter TEXT DEFAULT NULL,
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
    similarity REAL
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
        q.subsection,
        q.visual_description,
        0.5::REAL as similarity  -- Default similarity when no embedding search
    FROM ssat_questions q
    WHERE 
        (section_filter IS NULL OR q.section = section_filter)
        AND (subsection_filter IS NULL OR q.subsection = subsection_filter)
        AND (difficulty_filter IS NULL OR q.difficulty = difficulty_filter)
    ORDER BY RANDOM()
    LIMIT limit_count;
END;
$$;



-- Function to get reading examples for a passage type
CREATE OR REPLACE FUNCTION get_reading_training_examples(
    passage_type_filter TEXT DEFAULT NULL,
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
    visual_description TEXT
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
        rq.visual_description
    FROM reading_passages rp
    JOIN reading_questions rq ON rp.id = rq.passage_id
    WHERE 
        (passage_type_filter IS NULL OR rp.passage_type = passage_type_filter)
    ORDER BY RANDOM()
    LIMIT limit_count;
END;
$$;







-- Function to get writing training examples
CREATE OR REPLACE FUNCTION get_writing_training_examples(
    topic_filter TEXT DEFAULT NULL,
    limit_count INT DEFAULT 3
)
RETURNS TABLE (
    id TEXT,
    prompt TEXT,
    visual_description TEXT,
    tags TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wp.id,
        wp.prompt,
        wp.visual_description,
        wp.tags
    FROM writing_prompts wp
    WHERE 
        (topic_filter IS NULL OR wp.prompt ILIKE '%' || topic_filter || '%')
    ORDER BY RANDOM()
    LIMIT limit_count;
END;
$$;



-- ========================================
-- UNIFIED HYBRID FUNCTIONS (NEW)
-- ========================================

-- Unified function: Get training examples with hybrid approach (embedding + text + random)
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
        
        -- If we got results, return them
        IF FOUND THEN
            RETURN;
        END IF;
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
            0.6::REAL as similarity,  -- Slightly higher than random for text-based search
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
        
        -- If we got results, return them
        IF FOUND THEN
            RETURN;
        END IF;
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
        0.5::REAL as similarity,  -- Default similarity for random selection
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
        
        -- If we got results, return them
        IF FOUND THEN
            RETURN;
        END IF;
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
        
        -- If we got results, return them
        IF FOUND THEN
            RETURN;
        END IF;
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
        
        -- If we got results, return them
        IF FOUND THEN
            RETURN;
        END IF;
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
        
        -- If we got results, return them
        IF FOUND THEN
            RETURN;
        END IF;
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
-- COMMENTS
-- ========================================

COMMENT ON TABLE ssat_questions IS 'SSAT Math and Verbal questions for AI training examples';
COMMENT ON TABLE reading_passages IS 'Reading comprehension passages for AI training';
COMMENT ON TABLE reading_questions IS 'Reading comprehension questions linked to passages';
COMMENT ON TABLE writing_prompts IS 'Writing prompts for AI training';

COMMENT ON FUNCTION get_training_examples_by_section IS 'Get SSAT questions by section/difficulty when no topic specified';
COMMENT ON FUNCTION get_reading_training_examples IS 'Get reading comprehension examples for AI training';
COMMENT ON FUNCTION get_writing_training_examples IS 'Get writing prompt examples for AI training';
COMMENT ON FUNCTION get_training_examples_hybrid IS 'Unified hybrid function: Get training examples with embedding + text + random fallback';
COMMENT ON FUNCTION get_reading_training_examples_hybrid IS 'Unified hybrid function: Get reading examples with embedding + text + random fallback';
COMMENT ON FUNCTION get_writing_training_examples_hybrid IS 'Unified hybrid function: Get writing examples with embedding + text + random fallback';