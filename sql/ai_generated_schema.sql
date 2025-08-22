-- AI-Generated SSAT Content Schema for Supabase
-- Stores all AI-generated questions, passages, and prompts with metadata

-- Enable necessary extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========================================
-- AI-GENERATED CONTENT TABLES
-- ========================================

-- AI-Generated Questions (parallel to ssat_questions)
CREATE TABLE ai_generated_questions (
    id TEXT PRIMARY KEY,                    -- Pure UUID: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    generation_session_id TEXT NOT NULL,   -- Links to test generation session
    
    -- Question content (matches ssat_questions structure)
    section TEXT NOT NULL,                 -- "Quantitative", "Verbal"
    subsection TEXT NOT NULL,              -- "Fractions", "Synonyms", "Analogies"
    question TEXT NOT NULL,
    choices TEXT[],
    answer INTEGER,
    explanation TEXT,
    difficulty TEXT,
    tags TEXT[],
    visual_description TEXT,
    embedding vector(384),                 -- For future similarity search
    
    -- Generation metadata
    training_examples_used TEXT[],         -- IDs of training examples used
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI-Generated Reading Passages 
CREATE TABLE ai_generated_reading_passages (
    id TEXT PRIMARY KEY,                    -- Pure UUID: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    generation_session_id TEXT NOT NULL,
    
    -- Content (matches reading_passages structure)
    passage TEXT NOT NULL,
    passage_type TEXT,
    tags TEXT[],
    embedding vector(384),
    
    -- Generation metadata
    training_examples_used TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI-Generated Reading Questions (linked to AI passages)
CREATE TABLE ai_generated_reading_questions (
    id TEXT PRIMARY KEY,                    -- Pure UUID: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    passage_id TEXT NOT NULL REFERENCES ai_generated_reading_passages(id) ON DELETE CASCADE,
    generation_session_id TEXT NOT NULL,
    
    -- Content (matches reading_questions structure)
    question TEXT NOT NULL,
    choices TEXT[],
    answer INTEGER,
    explanation TEXT,
    difficulty TEXT,
    tags TEXT[],
    visual_description TEXT,
    embedding vector(384),
    
    -- Generation metadata (removed training_examples_used from reading questions)
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI-Generated Writing Prompts
CREATE TABLE ai_generated_writing_prompts (
    id TEXT PRIMARY KEY,                    -- Pure UUID: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    generation_session_id TEXT NOT NULL,
    
    -- Content (matches writing_prompts structure)
    prompt TEXT NOT NULL,
    tags TEXT[],
    visual_description TEXT,
    image_path TEXT,                        -- Path to the image file for picture-based prompts
    embedding vector(384),
    
    -- Generation metadata
    training_examples_used TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Session tracking for complete tests
CREATE TABLE ai_generation_sessions (
    id TEXT PRIMARY KEY,                    -- job_id from job_manager
    user_id UUID,                          -- Links to user_profiles (optional)
    request_params JSONB NOT NULL,         -- Complete request parameters
    total_questions_generated INTEGER,     -- Count of questions generated
    providers_used TEXT[],                 -- List of providers used
    generation_duration_ms INTEGER,        -- Total generation time
    status TEXT NOT NULL,                  -- "completed", "failed", "partial"
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- INDEXES FOR AI-GENERATED CONTENT
-- ========================================

-- Basic lookup indexes
CREATE INDEX idx_ai_question_session ON ai_generated_questions(generation_session_id);
CREATE INDEX idx_ai_question_section ON ai_generated_questions(section);
CREATE INDEX idx_ai_question_subsection ON ai_generated_questions(subsection);
CREATE INDEX idx_ai_question_difficulty ON ai_generated_questions(difficulty);

CREATE INDEX idx_ai_reading_passage_session ON ai_generated_reading_passages(generation_session_id);
CREATE INDEX idx_ai_reading_question_passage ON ai_generated_reading_questions(passage_id);
CREATE INDEX idx_ai_reading_question_session ON ai_generated_reading_questions(generation_session_id);

CREATE INDEX idx_ai_writing_session ON ai_generated_writing_prompts(generation_session_id);

-- User tracking indexes
CREATE INDEX idx_ai_generation_sessions_user_id ON ai_generation_sessions(user_id);

-- JSONB indexes for fast request_params queries
CREATE INDEX idx_ai_sessions_question_type ON ai_generation_sessions USING GIN ((request_params->'question_type'));
CREATE INDEX idx_ai_sessions_include_sections ON ai_generation_sessions USING GIN ((request_params->'include_sections'));
CREATE INDEX idx_ai_sessions_provider ON ai_generation_sessions USING GIN ((request_params->'provider'));
CREATE INDEX idx_ai_sessions_difficulty ON ai_generation_sessions USING GIN ((request_params->'difficulty'));
CREATE INDEX idx_ai_sessions_request_params ON ai_generation_sessions USING GIN (request_params);

-- Tag search indexes
CREATE INDEX idx_ai_question_tags ON ai_generated_questions USING GIN(tags);
CREATE INDEX idx_ai_passage_tags ON ai_generated_reading_passages USING GIN(tags);
CREATE INDEX idx_ai_reading_question_tags ON ai_generated_reading_questions USING GIN(tags);
CREATE INDEX idx_ai_writing_tags ON ai_generated_writing_prompts USING GIN(tags);

-- Embedding indexes for future similarity search
CREATE INDEX idx_ai_question_embedding ON ai_generated_questions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_ai_passage_embedding ON ai_generated_reading_passages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_ai_reading_question_embedding ON ai_generated_reading_questions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_ai_writing_embedding ON ai_generated_writing_prompts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- ========================================
-- AI CONTENT RETRIEVAL FUNCTIONS
-- ========================================


-- Get AI-generated questions by section
CREATE OR REPLACE FUNCTION get_ai_generated_questions_by_section(
    section_filter TEXT DEFAULT NULL,
    subsection_filter TEXT DEFAULT NULL,
    difficulty_filter TEXT DEFAULT NULL,
    limit_count INT DEFAULT 20
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
        (section_filter IS NULL OR q.section = section_filter)
        AND (subsection_filter IS NULL OR q.subsection = subsection_filter)
        AND (difficulty_filter IS NULL OR q.difficulty = difficulty_filter)
    ORDER BY q.created_at DESC
    LIMIT limit_count;
END;
$$;

-- Get AI-generated reading comprehension content
CREATE OR REPLACE FUNCTION get_ai_generated_reading_content(
    passage_type_filter TEXT DEFAULT NULL,
    limit_count INT DEFAULT 10
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
        rq.created_at
    FROM ai_generated_reading_passages rp
    JOIN ai_generated_reading_questions rq ON rp.id = rq.passage_id
    WHERE 
        (passage_type_filter IS NULL OR rp.passage_type = passage_type_filter)
    ORDER BY rq.created_at DESC
    LIMIT limit_count;
END;
$$;

-- ========================================
-- UTILITY FUNCTIONS
-- ========================================

-- Get AI-generated writing prompts
CREATE OR REPLACE FUNCTION get_ai_generated_writing_prompts(
    topic_filter TEXT DEFAULT NULL,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    id TEXT,
    prompt TEXT,
    visual_description TEXT,
    image_path TEXT,  -- Added image_path
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
        wp.prompt,
        wp.visual_description,
        wp.image_path,  -- Added image_path
        wp.tags,
        wp.generation_session_id,
        wp.created_at
    FROM ai_generated_writing_prompts wp
    WHERE 
        (topic_filter IS NULL OR wp.prompt ILIKE '%' || topic_filter || '%')
    ORDER BY wp.created_at DESC
    LIMIT limit_count;
END;
$$;

-- Get generation sessions (with optional user filter)
CREATE OR REPLACE FUNCTION get_ai_generation_sessions(
    p_user_id UUID DEFAULT NULL,
    limit_count INT DEFAULT 20
)
RETURNS TABLE (
    session_id TEXT,
    user_id UUID,
    request_params JSONB,
    total_questions INTEGER,
    providers_used TEXT[],
    generation_duration_ms INTEGER,
    status TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.user_id,
        s.request_params,
        s.total_questions_generated,
        s.providers_used,
        s.generation_duration_ms,
        s.status,
        s.created_at
    FROM ai_generation_sessions s
    WHERE (p_user_id IS NULL OR s.user_id = p_user_id)
    ORDER BY s.created_at DESC
    LIMIT limit_count;
END;
$$;

-- Get detailed session statistics
CREATE OR REPLACE FUNCTION get_session_statistics(
    p_session_id TEXT
)
RETURNS TABLE (
    session_id TEXT,
    user_id UUID,
    total_questions INTEGER,
    math_questions INTEGER,
    verbal_questions INTEGER,
    reading_passages INTEGER,
    reading_questions INTEGER,
    writing_prompts INTEGER,
    providers_used TEXT[],
    generation_duration_ms INTEGER,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.user_id,
        s.total_questions_generated,
        (SELECT COUNT(*)::INTEGER FROM ai_generated_questions WHERE generation_session_id = s.id AND section = 'Quantitative'),
        (SELECT COUNT(*)::INTEGER FROM ai_generated_questions WHERE generation_session_id = s.id AND section = 'Verbal'),
        (SELECT COUNT(*)::INTEGER FROM ai_generated_reading_passages WHERE generation_session_id = s.id),
        (SELECT COUNT(*)::INTEGER FROM ai_generated_reading_questions WHERE generation_session_id = s.id),
        (SELECT COUNT(*)::INTEGER FROM ai_generated_writing_prompts WHERE generation_session_id = s.id),
        s.providers_used,
        s.generation_duration_ms,
        s.created_at
    FROM ai_generation_sessions s
    WHERE s.id = p_session_id;
END;
$$;

-- ========================================
-- COMMENTS
-- ========================================

COMMENT ON TABLE ai_generated_questions IS 'AI-generated SSAT questions with generation metadata';
COMMENT ON TABLE ai_generated_reading_passages IS 'AI-generated reading passages with metadata';
COMMENT ON TABLE ai_generated_reading_questions IS 'AI-generated reading questions linked to AI passages';
COMMENT ON TABLE ai_generated_writing_prompts IS 'AI-generated writing prompts with metadata and image support';
COMMENT ON COLUMN ai_generated_writing_prompts.image_path IS 'Path to the image file for picture-based writing prompts';
COMMENT ON TABLE ai_generation_sessions IS 'Tracking sessions for complete test generation';

COMMENT ON FUNCTION get_ai_generated_questions_by_section IS 'Get AI-generated questions with filtering by section/difficulty';
COMMENT ON FUNCTION get_ai_generated_reading_content IS 'Get AI-generated reading comprehension content';
COMMENT ON FUNCTION get_ai_generated_writing_prompts IS 'Get AI-generated writing prompts with topic filtering and image_path support';
COMMENT ON FUNCTION get_ai_generation_sessions IS 'Get generation sessions (all or filtered by user)';
COMMENT ON FUNCTION get_session_statistics IS 'Get detailed statistics for a specific session';