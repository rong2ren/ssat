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

-- Key function: Get training examples using embedding similarity
CREATE OR REPLACE FUNCTION get_training_examples_by_embedding(
    query_embedding VECTOR(384),
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
        (1 - (q.embedding <=> query_embedding))::REAL as similarity
    FROM ssat_questions q
    WHERE 
        q.embedding IS NOT NULL
        AND (section_filter IS NULL OR q.section = section_filter)
        AND (subsection_filter IS NULL OR q.subsection = subsection_filter)
        AND (difficulty_filter IS NULL OR q.difficulty = difficulty_filter)
    ORDER BY q.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$;

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

-- Simple function to get questions for a passage
CREATE OR REPLACE FUNCTION get_reading_questions_for_passage(
    passage_id_param TEXT
)
RETURNS TABLE (
    id TEXT,
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
        rq.id,
        rq.question,
        rq.choices,
        rq.answer,
        rq.explanation,
        rq.difficulty,
        rq.visual_description
    FROM reading_questions rq
    WHERE rq.passage_id = passage_id_param
    ORDER BY rq.created_at ASC;
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
-- AI TRAINING VIEW
-- ========================================

-- Simplified view for AI training context
CREATE VIEW ai_training_examples AS
SELECT 
    'math_verbal' as type,
    id,
    section,
    subsection,
    question,
    choices,
    answer,
    explanation,
    difficulty,
    tags,
    source_file
FROM ssat_questions
UNION ALL
SELECT 
    'reading' as type,
    rq.id,
    'Reading' as section,
    rp.passage_type as subsection,
    rq.question,
    rq.choices,
    rq.answer,
    rq.explanation,
    rq.difficulty,
    rq.tags,
    rp.source_file
FROM reading_questions rq
JOIN reading_passages rp ON rq.passage_id = rp.id;

-- ========================================
-- COMMENTS
-- ========================================

COMMENT ON TABLE ssat_questions IS 'SSAT Math and Verbal questions for AI training examples';
COMMENT ON TABLE reading_passages IS 'Reading comprehension passages for AI training';
COMMENT ON TABLE reading_questions IS 'Reading comprehension questions linked to passages';
COMMENT ON TABLE writing_prompts IS 'Writing prompts for AI training';

COMMENT ON FUNCTION get_training_examples_by_embedding IS 'Get semantically similar SSAT questions using embedding similarity for AI training';
COMMENT ON FUNCTION get_training_examples_by_section IS 'Get SSAT questions by section/difficulty when no topic specified';
COMMENT ON FUNCTION get_reading_training_examples IS 'Get reading comprehension examples for AI training';
COMMENT ON FUNCTION get_reading_questions_for_passage IS 'Get all questions for a specific reading passage';
COMMENT ON FUNCTION get_writing_training_examples IS 'Get writing prompt examples for AI training';

COMMENT ON VIEW ai_training_examples IS 'Unified view of all questions for AI training context';