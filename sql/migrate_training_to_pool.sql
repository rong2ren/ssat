-- ========================================
-- SMART MIGRATION SYSTEM
-- ========================================
-- This script migrates training examples to the user-facing pool
-- Uses simple existence checks instead of complex tracking tables

-- ========================================
-- 1. MIGRATE TRAINING QUESTIONS
-- ========================================

-- Function to migrate training questions to the user pool
CREATE OR REPLACE FUNCTION migrate_training_questions_to_pool()
RETURNS TABLE (
    migrated_count INTEGER,
    skipped_count INTEGER,
    error_count INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    training_question RECORD;
    migrated_count INTEGER := 0;
    skipped_count INTEGER := 0;
    error_count INTEGER := 0;
    new_id TEXT;
    existing_id TEXT;
BEGIN
    -- Loop through all training questions
    FOR training_question IN 
        SELECT * FROM ssat_questions 
        ORDER BY id
    LOOP
        BEGIN
            -- Check if already migrated by looking for pool item
            SELECT id INTO existing_id 
            FROM ai_generated_questions 
            WHERE id = 'MIGRATED-' || training_question.id;
            
            -- If not migrated yet, or if we want to update existing
            IF existing_id IS NULL THEN
                -- Generate new ID for the AI-generated pool
                new_id := 'MIGRATED-' || training_question.id;
                
                -- Insert into ai_generated_questions
                INSERT INTO ai_generated_questions (
                    id,
                    generation_session_id,
                    section,
                    subsection,
                    question,
                    choices,
                    answer,
                    explanation,
                    difficulty,
                    tags,
                    visual_description,
                    embedding,
                    training_examples_used
                ) VALUES (
                    new_id,
                    'MIGRATED-SESSION-' || training_question.id,
                    training_question.section,
                    training_question.subsection,
                    training_question.question,
                    COALESCE(training_question.choices, ARRAY[]::TEXT[]),
                    COALESCE(training_question.answer, 0),
                    COALESCE(training_question.explanation, ''),
                    COALESCE(training_question.difficulty, 'Medium'),
                    COALESCE(training_question.tags, ARRAY[]::TEXT[]),
                    COALESCE(training_question.visual_description, ''),
                    training_question.embedding,
                    ARRAY[training_question.id] -- Mark as migrated from this training example
                );
                
                migrated_count := migrated_count + 1;
            ELSE
                skipped_count := skipped_count + 1;
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            error_count := error_count + 1;
            RAISE NOTICE 'Error migrating question %: %', training_question.id, SQLERRM;
        END;
    END LOOP;
    
    RETURN QUERY SELECT migrated_count, skipped_count, error_count;
END;
$$;

-- ========================================
-- 2. MIGRATE READING CONTENT
-- ========================================

-- Function to migrate reading passages and questions
CREATE OR REPLACE FUNCTION migrate_reading_content_to_pool()
RETURNS TABLE (
    migrated_passages INTEGER,
    migrated_questions INTEGER,
    skipped_count INTEGER,
    error_count INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    reading_passage RECORD;
    reading_question RECORD;
    migrated_passages INTEGER := 0;
    migrated_questions INTEGER := 0;
    skipped_count INTEGER := 0;
    error_count INTEGER := 0;
    new_passage_id TEXT;
    new_question_id TEXT;
    existing_passage_id TEXT;
    existing_question_id TEXT;
BEGIN
    -- Loop through all reading passages
    FOR reading_passage IN 
        SELECT * FROM reading_passages 
        ORDER BY id
    LOOP
        BEGIN
            -- Check if passage already migrated
            SELECT id INTO existing_passage_id 
            FROM ai_generated_reading_passages 
            WHERE id = 'MIGRATED-' || reading_passage.id;
            
            IF existing_passage_id IS NULL THEN
                -- Generate new ID for the passage
                new_passage_id := 'MIGRATED-' || reading_passage.id;
                
                -- Insert passage (FIXED: Use correct field names)
                INSERT INTO ai_generated_reading_passages (
                    id,
                    generation_session_id,
                    passage,
                    passage_type,
                    tags,
                    embedding,
                    training_examples_used
                ) VALUES (
                    new_passage_id,
                    'MIGRATED-SESSION-' || reading_passage.id,
                    reading_passage.passage,
                    COALESCE(reading_passage.passage_type, 'fiction'),
                    COALESCE(reading_passage.tags, ARRAY[]::TEXT[]),
                    reading_passage.embedding,
                    ARRAY[reading_passage.id]
                );
                
                migrated_passages := migrated_passages + 1;
                
                -- Migrate associated questions
                FOR reading_question IN 
                    SELECT * FROM reading_questions 
                    WHERE passage_id = reading_passage.id
                LOOP
                    BEGIN
                        -- Check if question already migrated
                        SELECT id INTO existing_question_id 
                        FROM ai_generated_reading_questions 
                        WHERE id = 'MIGRATED-' || reading_question.id;
                        
                        IF existing_question_id IS NULL THEN
                            -- Generate new ID for the question
                            new_question_id := 'MIGRATED-' || reading_question.id;
                            
                            -- Insert question (FIXED: Remove training_examples_used field)
                            INSERT INTO ai_generated_reading_questions (
                                id,
                                generation_session_id,
                                passage_id,
                                question,
                                choices,
                                answer,
                                explanation,
                                difficulty,
                                tags,
                                visual_description,
                                embedding
                            ) VALUES (
                                new_question_id,
                                'MIGRATED-SESSION-' || reading_question.id,
                                new_passage_id,
                                reading_question.question,
                                COALESCE(reading_question.choices, ARRAY[]::TEXT[]),
                                COALESCE(reading_question.answer, 0),
                                COALESCE(reading_question.explanation, ''),
                                COALESCE(reading_question.difficulty, 'Medium'),
                                COALESCE(reading_question.tags, ARRAY[]::TEXT[]),
                                COALESCE(reading_question.visual_description, ''),
                                reading_question.embedding
                            );
                            
                            migrated_questions := migrated_questions + 1;
                        END IF;
                        
                    EXCEPTION WHEN OTHERS THEN
                        error_count := error_count + 1;
                        RAISE NOTICE 'Error migrating reading question %: %', reading_question.id, SQLERRM;
                    END;
                END LOOP;
            ELSE
                skipped_count := skipped_count + 1;
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            error_count := error_count + 1;
            RAISE NOTICE 'Error migrating reading passage %: %', reading_passage.id, SQLERRM;
        END;
    END LOOP;
    
    RETURN QUERY SELECT migrated_passages, migrated_questions, skipped_count, error_count;
END;
$$;

-- ========================================
-- 3. MIGRATE WRITING PROMPTS
-- ========================================

-- Function to migrate writing prompts to the user pool
CREATE OR REPLACE FUNCTION migrate_writing_prompts_to_pool()
RETURNS TABLE (
    migrated_count INTEGER,
    skipped_count INTEGER,
    error_count INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    writing_prompt RECORD;
    migrated_count INTEGER := 0;
    skipped_count INTEGER := 0;
    error_count INTEGER := 0;
    new_id TEXT;
    existing_id TEXT;
BEGIN
    -- Loop through all writing prompts
    FOR writing_prompt IN 
        SELECT * FROM writing_prompts 
        ORDER BY id
    LOOP
        BEGIN
            -- Check if already migrated
            SELECT id INTO existing_id 
            FROM ai_generated_writing_prompts 
            WHERE id = 'MIGRATED-' || writing_prompt.id;
            
            IF existing_id IS NULL THEN
                -- Generate new ID for the AI-generated pool
                new_id := 'MIGRATED-' || writing_prompt.id;
                
                -- Insert into ai_generated_writing_prompts (FIXED: Use correct field names)
                INSERT INTO ai_generated_writing_prompts (
                    id,
                    generation_session_id,
                    prompt,
                    tags,
                    visual_description,
                    embedding,
                    training_examples_used
                ) VALUES (
                    new_id,
                    'MIGRATED-SESSION-' || writing_prompt.id,
                    writing_prompt.prompt,
                    COALESCE(writing_prompt.tags, ARRAY[]::TEXT[]),
                    COALESCE(writing_prompt.visual_description, ''),
                    writing_prompt.embedding,
                    ARRAY[writing_prompt.id]
                );
                
                migrated_count := migrated_count + 1;
            ELSE
                skipped_count := skipped_count + 1;
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            error_count := error_count + 1;
            RAISE NOTICE 'Error migrating writing prompt %: %', writing_prompt.id, SQLERRM;
        END;
    END LOOP;
    
    RETURN QUERY SELECT migrated_count, skipped_count, error_count;
END;
$$;

-- ========================================
-- 4. MIGRATE ALL CONTENT
-- ========================================

-- Function to migrate all training content to the user pool
CREATE OR REPLACE FUNCTION migrate_all_training_to_pool()
RETURNS TABLE (
    migrated_questions INTEGER,
    migrated_passages INTEGER,
    migrated_reading_questions INTEGER,
    migrated_writing_prompts INTEGER,
    total_skipped INTEGER,
    total_errors INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    questions_result RECORD;
    reading_result RECORD;
    writing_result RECORD;
BEGIN
    -- Migrate training questions
    SELECT * INTO questions_result FROM migrate_training_questions_to_pool();
    
    -- Migrate reading content
    SELECT * INTO reading_result FROM migrate_reading_content_to_pool();
    
    -- Migrate writing prompts
    SELECT * INTO writing_result FROM migrate_writing_prompts_to_pool();
    
    RETURN QUERY SELECT 
        questions_result.migrated_count,
        reading_result.migrated_passages,
        reading_result.migrated_questions,
        writing_result.migrated_count,
        questions_result.skipped_count + reading_result.skipped_count + writing_result.skipped_count,
        questions_result.error_count + reading_result.error_count + writing_result.error_count;
END;
$$;

-- ========================================
-- 5. STATISTICS
-- ========================================

-- Function to get migration statistics
CREATE OR REPLACE FUNCTION get_migration_statistics()
RETURNS TABLE (
    training_questions_count BIGINT,
    training_passages_count BIGINT,
    training_reading_questions_count BIGINT,
    training_writing_prompts_count BIGINT,
    pool_questions_count BIGINT,
    pool_passages_count BIGINT,
    pool_reading_questions_count BIGINT,
    pool_writing_prompts_count BIGINT,
    migrated_questions_count BIGINT,
    migrated_passages_count BIGINT,
    migrated_reading_questions_count BIGINT,
    migrated_writing_prompts_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY SELECT 
        -- Training content counts
        (SELECT COUNT(*) FROM ssat_questions),
        (SELECT COUNT(*) FROM reading_passages),
        (SELECT COUNT(*) FROM reading_questions),
        (SELECT COUNT(*) FROM writing_prompts),
        
        -- Pool content counts
        (SELECT COUNT(*) FROM ai_generated_questions),
        (SELECT COUNT(*) FROM ai_generated_reading_passages),
        (SELECT COUNT(*) FROM ai_generated_reading_questions),
        (SELECT COUNT(*) FROM ai_generated_writing_prompts),
        
        -- Migrated content counts (by session ID pattern)
        (SELECT COUNT(*) FROM ai_generated_questions WHERE generation_session_id LIKE 'MIGRATED-SESSION-%'),
        (SELECT COUNT(*) FROM ai_generated_reading_passages WHERE generation_session_id LIKE 'MIGRATED-SESSION-%'),
        (SELECT COUNT(*) FROM ai_generated_reading_questions WHERE generation_session_id LIKE 'MIGRATED-SESSION-%'),
        (SELECT COUNT(*) FROM ai_generated_writing_prompts WHERE generation_session_id LIKE 'MIGRATED-SESSION-%');
END;
$$;

-- ========================================
-- 6. CLEANUP
-- ========================================

-- Function to cleanup migrated content from the user pool
CREATE OR REPLACE FUNCTION cleanup_migrated_content()
RETURNS TABLE (
    removed_questions INTEGER,
    removed_passages INTEGER,
    removed_reading_questions INTEGER,
    removed_writing_prompts INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    removed_questions INTEGER := 0;
    removed_passages INTEGER := 0;
    removed_reading_questions INTEGER := 0;
    removed_writing_prompts INTEGER := 0;
BEGIN
    -- Remove migrated questions
    DELETE FROM ai_generated_questions 
    WHERE generation_session_id LIKE 'MIGRATED-SESSION-%';
    GET DIAGNOSTICS removed_questions = ROW_COUNT;
    
    -- Remove migrated reading passages (questions will be removed by cascade)
    DELETE FROM ai_generated_reading_passages 
    WHERE generation_session_id LIKE 'MIGRATED-SESSION-%';
    GET DIAGNOSTICS removed_passages = ROW_COUNT;
    
    -- Remove migrated writing prompts
    DELETE FROM ai_generated_writing_prompts 
    WHERE generation_session_id LIKE 'MIGRATED-SESSION-%';
    GET DIAGNOSTICS removed_writing_prompts = ROW_COUNT;
    
    RETURN QUERY SELECT removed_questions, removed_passages, removed_reading_questions, removed_writing_prompts;
END;
$$; 