# Supabase Database Setup and Upload Guide (Simplified)

## 📊 Database Schema Overview

The Supabase database uses a **simplified, high-performance schema** with a single main table for questions and embeddings for semantic search.

### **Main Tables:**

1. **`ssat_questions`** - All SSAT questions in one table
   - `id` (TEXT) - Human-readable ID like "MATH-001"
   - `source_file` - Original PDF filename
   - `section` - "Quantitative", "Verbal", "Reading", "Writing"
   - `subsection` - "Fractions", "Synonyms", "Comprehension", etc.
   - `question` - The actual question text
   - `passage` - For reading comprehension questions
   - `choices` - Array of multiple choice options
   - `answer` - 0-based index of correct choice
   - `explanation` - Explanation of the correct answer
   - `explanation_source` - 'pdf', 'generated', 'manual'
   - `difficulty` - 'Easy', 'Medium', 'Hard'
   - `tags` - Array of tags for categorization
   - `visual_description` - For questions with diagrams
   - `embedding` - 384-dim vector for semantic search
   - `created_at` - Timestamp

2. **`writing_prompts`** - Separate table for writing prompts
   - `id` - Human-readable ID like "WRITING-001"
   - `source_file` - Original PDF filename
   - `prompt` - The writing prompt text
   - `requirements` - Array of requirements
   - `visual_description` - Description of the picture
   - `sample_responses` - JSONB for graded examples
   - `embedding` - 384-dim vector for semantic search
   - `tags` - Array of tags
   - `created_at` - Timestamp

### **Key Features:**

- **Single table design** for fast queries and simplicity
- **384-dim embeddings** using Sentence-Transformers (faster than 1536-dim)
- **Array fields** for choices and tags (no joins needed)
- **Data integrity constraints** for valid sections/difficulties
- **Semantic search functions** for finding similar questions
- **Summary views** for analytics

## 🚀 Setup Instructions

### **Step 1: Create Supabase Project**

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your project URL and anon key

### **Step 2: Run Database Schema**

1. Copy the contents of `supabase_schema.sql`
2. Go to your Supabase dashboard → SQL Editor
3. Paste and run the schema script
4. This will create the simplified tables, indexes, and functions

### **Step 3: Configure Environment Variables**

Add to your `.env` file:
```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=your_openai_api_key
```

### **Step 4: Install Dependencies**

```bash
uv sync
```

### **Step 5: Upload JSON Files**

```bash
uv run python src/upload_to_supabase.py
```

## 📁 JSON File Structure Analysis

Based on your JSON files, here's the structure pattern:

```json
{
  "exam_info": {
    "name": "string",
    "grade": [numbers],
    "source": "string",
    "sections": {
      "Quantitative": ["subsections"],
      "Verbal": ["subsections"],
      "Reading": ["subsections"],
      "Writing": ["subsections"]
    }
  },
  "questions": [
    {
      "id": "string",
      "section": "string",
      "subsection": "string",
      "question": "string",
      "choices": ["array"],
      "answer": number,
      "explanation": {
        "text": "string",
        "source": "string"
      },
      "difficulty": "string",
      "tags": ["array"]
    }
  ]
}
```

### **Variations Handled:**

1. **Reading Questions**: Have nested `passage` and `questions` array
2. **Writing Prompts**: Have `prompt`, `visual_description`, `requirements`
3. **Visual Questions**: Include `visual_description` field
4. **Multiple AI Providers**: Detected from filename (`-Gemini.json`, `-Deepseek.json`)

## 🔍 Features

### **Semantic Search**
- Uses 384-dim embeddings (faster than 1536-dim)
- Vector similarity search with configurable threshold
- Filter by section, difficulty, source file
- Separate search functions for questions and writing prompts

### **Simplified Data Model**
- Single table for all questions (no complex joins)
- Array fields for choices and tags
- Direct field access for fast queries
- Handles all SSAT question types

### **Performance Optimized**
- Proper indexes for fast queries
- Vector indexes for semantic search
- GIN indexes for array operations
- No complex relationships to maintain

### **Easy Querying**
- Complete view with all fields
- Summary views for analytics
- Simple filtering and sorting
- Support for complex queries

## 📊 Expected Results

Based on your JSON files, you should expect:

- **~15-20 JSON files** to be processed
- **~500-1000+ questions** total
- **Multiple AI providers** (Gemini, Deepseek)
- **All SSAT sections** covered
- **384-dim embeddings** generated for semantic search

## 🔧 Troubleshooting

### **Common Issues:**

1. **Missing API Keys**: Ensure all required API keys are in `.env`
2. **Database Connection**: Verify Supabase URL and key
3. **Schema Errors**: Run schema script completely
4. **Embedding Failures**: Check OpenAI API quota and rate limits

### **Upload Process:**

The upload script will:
- ✅ Process all JSON files automatically
- ✅ Generate 384-dim embeddings for each question
- ✅ Handle different question types
- ✅ Map data to simplified schema
- ✅ Provide detailed progress and error reporting

## 🎯 Next Steps

After successful upload:

1. **Test Semantic Search**: Query similar questions
2. **Build API Endpoints**: Create REST API for question retrieval
3. **Add Authentication**: Configure RLS policies
4. **Monitor Performance**: Check query performance
5. **Scale as Needed**: Add more questions and sources

## 📈 Database Statistics

After upload, you can run these queries to check your data:

```sql
-- Count questions by section
SELECT section, COUNT(*) as question_count
FROM ssat_questions
GROUP BY section
ORDER BY question_count DESC;

-- Count questions by difficulty
SELECT difficulty, COUNT(*) as question_count
FROM ssat_questions
GROUP BY difficulty
ORDER BY question_count DESC;

-- Count questions by source
SELECT source_file, COUNT(*) as question_count
FROM ssat_questions
GROUP BY source_file
ORDER BY question_count DESC;

-- Check embedding coverage
SELECT 
    COUNT(*) as total_questions,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as questions_with_embeddings,
    ROUND(COUNT(*) FILTER (WHERE embedding IS NOT NULL) * 100.0 / COUNT(*), 2) as embedding_coverage_percent
FROM ssat_questions;
```

## 🔍 Example Queries

### **Semantic Search Examples:**

```sql
-- Find similar questions (requires embedding)
SELECT id, question, section, similarity
FROM search_questions_semantic(
    '[0.1, 0.2, ...]'::vector(384),  -- Your query embedding
    0.7,  -- Similarity threshold
    10,   -- Number of results
    'Quantitative',  -- Filter by section
    'Medium'         -- Filter by difficulty
);

-- Find similar writing prompts
SELECT id, prompt, similarity
FROM search_writing_prompts_semantic(
    '[0.1, 0.2, ...]'::vector(384),  -- Your query embedding
    0.7,  -- Similarity threshold
    5     -- Number of results
);
```

### **Simple Filtering:**

```sql
-- Get all math questions
SELECT * FROM ssat_questions 
WHERE section = 'Quantitative' 
ORDER BY created_at DESC;

-- Get questions by tags
SELECT * FROM ssat_questions 
WHERE 'fractions' = ANY(tags);

-- Get questions from specific source
SELECT * FROM ssat_questions 
WHERE source_file = 'SSAT_ElementaryTest4th_1.pdf';
```

## 🎉 Benefits of Simplified Schema

### **Performance:**
- **Faster queries** - no complex joins
- **Smaller embeddings** - 384 vs 1536 dimensions
- **Direct field access** - no relationship lookups

### **Simplicity:**
- **Easier to understand** - single table for questions
- **Less maintenance** - no complex relationships
- **Faster development** - simpler queries

### **Flexibility:**
- **Easy to modify** - add fields without schema changes
- **Simple analytics** - direct aggregation on fields
- **Quick prototyping** - no complex data modeling needed 