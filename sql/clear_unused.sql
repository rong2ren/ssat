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