# New SSAT Content Generation Architecture

## Overview

Implemented proper type-specific content generation architecture that eliminates the previous patching approach and follows the natural structure of SSAT content types.

## Key Architectural Principles

1. **Different content types have different data structures**
2. **Same generation functions for individual and complete tests**
3. **Type-specific generators with unified routing**
4. **No more forcing everything into Question[] format**

## Architecture Components

### 1. Type-Specific Content Generators (`app/content_generators.py`)

```python
# Standalone questions (math, verbal, analogy, synonym)
def generate_standalone_questions(request) -> List[Question]

# Reading comprehension (7 passages × 4 questions = 28 questions)
def generate_reading_passages(request) -> List[ReadingPassage] 

# Writing prompts (creative writing tasks)
def generate_writing_prompts(request) -> List[WritingPrompt]

# Unified dispatcher
def generate_content(request) -> Union[List[Question], List[ReadingPassage], List[WritingPrompt]]
```

### 2. Proper Data Models

```python
class ReadingPassage:
    - id, title, text, passage_type, grade_level, topic
    - questions: List[Question]  # Always 4 questions per passage
    - metadata

class WritingPrompt:
    - id, prompt_text, instructions, visual_description
    - grade_level, story_elements, prompt_type
```

### 3. Unified Content Service (`app/services/unified_content_service.py`)

```python
class UnifiedContentService:
    async def generate_content(request) -> Union[
        QuestionGenerationResponse,     # For math/verbal/analogy/synonym
        ReadingGenerationResponse,      # For reading comprehension
        WritingGenerationResponse       # For writing prompts
    ]
```

### 4. API Response Models (`app/models/responses.py`)

```python
# Type-specific responses
class QuestionGenerationResponse:
    questions: List[GeneratedQuestion]
    
class ReadingGenerationResponse:
    passages: List[ReadingPassage]
    total_questions: int
    
class WritingGenerationResponse:
    prompts: List[WritingPrompt]
```

### 5. Updated API Routing (`app/main.py`)

```python
@app.post("/generate")
async def generate_content(request: QuestionGenerationRequest):
    # Routes to appropriate generator based on question type
    result = await content_service.generate_content(request)
    return result  # Type-specific response
```

### 6. Frontend Response Handling (`frontend/src/components/QuestionGenerator.tsx`)

```typescript
const data = await response.json()

if (data.questions) {
    // Standalone questions
    setQuestions(data.questions)
} else if (data.passages) {
    // Reading comprehension - flatten for display
    const allQuestions = []
    for (const passage of data.passages) {
        for (const question of passage.questions) {
            allQuestions.push({
                ...question,
                text: `PASSAGE:\n${passage.text}\n\nQUESTION: ${question.text}`
            })
        }
    }
    setQuestions(allQuestions)
} else if (data.prompts) {
    // Writing prompts - convert for display
    const promptQuestions = data.prompts.map(prompt => ({
        text: `WRITING PROMPT:\n${prompt.prompt_text}\n\nINSTRUCTIONS: ${prompt.instructions}`,
        options: [], // No options for writing
        // ...
    }))
    setQuestions(promptQuestions)
}
```

## Official SSAT Structure (from specifications.py)

- **Quantitative**: 30 individual questions
- **Verbal**: 30 individual questions (synonyms + analogies)
- **Reading**: 7 passages × 4 questions each = 28 questions
- **Writing**: 1 creative writing prompt (unscored)

## Benefits of New Architecture

1. **Natural Structure**: Each content type follows its natural SSAT format
2. **No Patching**: No more trying to fit reading into Question[] format
3. **Reusable**: Same generators for individual and complete tests
4. **Type Safe**: Proper data models with validation
5. **Extensible**: Easy to add new content types
6. **Maintainable**: Clear separation of concerns

## Usage Examples

### Individual Reading Generation
```python
request = QuestionRequest(question_type="reading", count=2)  # 2 passages
result = await content_service.generate_content(request)
# Returns ReadingGenerationResponse with 2 passages, 8 total questions
```

### Complete Test Reading Section
```python
request = QuestionRequest(question_type="reading", count=7)  # 7 passages
result = await content_service.generate_content(request) 
# Returns ReadingGenerationResponse with 7 passages, 28 total questions
```

### Individual Writing Generation
```python
request = QuestionRequest(question_type="writing", count=1)
result = await content_service.generate_content(request)
# Returns WritingGenerationResponse with 1 creative writing prompt
```

## Migration from Old Architecture

**Before (Broken)**:
```
Reading Request → generate_questions() → Question[] with "PASSAGE: + QUESTION:" mashed together
```

**After (Correct)**:
```
Reading Request → generate_reading_passages() → ReadingPassage[] with proper separation
```

The new architecture eliminates all the formatting/reformatting between different parts of the system and ensures each content type follows its natural structure throughout the entire pipeline.