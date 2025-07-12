-- Clear all SSAT tables for fresh upload
DELETE FROM reading_questions;
DELETE FROM reading_passages;
DELETE FROM ssat_questions;
DELETE FROM writing_prompts;

-- Reset any sequences if needed
-- (Supabase will handle this automatically)