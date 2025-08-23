# LLM Integration & Question Generation

This document describes the AI/LLM integration for the SSAT Question Generator, including the question generation process, provider management, and quality improvements.

## 🎯 Overview

The system uses multiple LLM providers to generate high-quality SSAT questions with a focus on elementary-level appropriateness and educational value.

## 🤖 Supported LLM Providers

### 1. Google Gemini (Recommended)
- **Pros**: Free tier, good quality, fast response times
- **Cons**: Limited context window, occasional formatting issues
- **Setup**: Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Cost**: Free tier available, then pay-per-use

### 2. DeepSeek
- **Pros**: Affordable, good quality, large context window
- **Cons**: Newer provider, less documentation
- **Setup**: Get API key from [DeepSeek Console](https://platform.deepseek.com/)
- **Cost**: Very affordable pricing

### 3. OpenAI
- **Pros**: Best quality, reliable, excellent formatting
- **Cons**: Expensive, rate limits
- **Setup**: Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Cost**: Premium pricing

## 🔄 Question Generation Process

### 1. Input Validation
```python
# Validate request parameters
def validate_generation_request(request: GenerationRequest):
    # Check question type validity
    # Validate difficulty level
    # Ensure count is within limits
    # Verify topic appropriateness
```

### 2. Provider Selection
```python
# Choose best available LLM provider
def select_provider(request: GenerationRequest) -> LLMProvider:
    # Check provider availability
    # Consider cost optimization
    # Match provider to question type
    # Handle fallback scenarios
```

### 3. Prompt Construction
```python
# Build context-aware prompts
def build_few_shot_prompt(request: GenerationRequest) -> str:
    # Include SSAT format requirements
    # Add elementary-level constraints
    # Include relevant examples
    # Specify output format
```

### 4. Question Generation
```python
# Generate questions with AI
async def generate_questions(prompt: str, provider: LLMProvider):
    # Send request to LLM
    # Handle rate limiting
    # Parse response
    # Validate output format
```

### 5. Quality Validation
```python
# Validate generated questions
def validate_question_quality(question: Question) -> QualityReport:
    # Check readability level
    # Validate SSAT format compliance
    # Assess cognitive appropriateness
    # Score overall quality
```

### 6. Storage & Embeddings
```python
# Store questions with embeddings
async def store_question_with_embedding(question: Question):
    # Generate text embeddings
    # Store in database
    # Index for semantic search
    # Track metadata
```

## 📚 Few-Shot Learning Implementation

### Training Example Selection
```python
def select_training_examples(question_type: str, topic: str, count: int = 3):
    # Semantic search for relevant examples
    # Diversity sampling for variety
    # Quality filtering for best examples
    # Age-appropriate selection
```

### Example Format
```json
{
  "question": "What is 8 + 5?",
  "options": ["A) 11", "B) 12", "C) 13", "D) 14"],
  "correct_answer": "C",
  "explanation": "8 + 5 = 13",
  "difficulty": "easy",
  "topic": "addition"
}
```

### Prompt Template
```
You are an expert SSAT question generator for elementary students (grades 3-4).

REQUIREMENTS:
- Questions must be appropriate for elementary students
- Use simple vocabulary and clear language
- Include 4 multiple choice options (A, B, C, D)
- Provide educational explanations
- Follow SSAT format standards

EXAMPLES:
[Include 2-3 high-quality examples]

Generate [count] [question_type] questions about [topic] at [difficulty] level.

OUTPUT FORMAT:
{
  "questions": [
    {
      "question": "...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A/B/C/D",
      "explanation": "..."
    }
  ]
}
```

## 🎓 Educational Quality Assurance

### Elementary-Level Validation
```python
def validate_elementary_readability(text: str) -> Dict[str, Any]:
    """Validate text is appropriate for grades 3-4."""
    return {
        'flesch_kincaid_grade': calculate_fk_grade(text),  # Should be ≤ 4.0
        'vocabulary_level': check_elementary_vocabulary(text),
        'sentence_complexity': analyze_sentence_complexity(text),
        'is_appropriate': grade <= 4.0 and vocab_appropriate
    }
```

### SSAT Format Compliance
```python
def validate_ssat_compliance(question: Question) -> Dict[str, Any]:
    """Validate question follows authentic SSAT format."""
    return {
        'distractor_quality': check_plausible_distractors(question),
        'explanation_quality': validate_explanation_educational_value(question),
        'stem_clarity': check_question_stem_clarity(question),
        'mathematical_notation': validate_math_notation(question),
        'timing_appropriateness': estimate_time_to_solve(question),
        'ssat_compliance_score': calculate_compliance_score(question)
    }
```

### Cognitive Level Enforcement
```python
ELEMENTARY_COGNITIVE_LEVELS = {
    'easy': ['REMEMBER', 'UNDERSTAND'],
    'medium': ['UNDERSTAND', 'APPLY'], 
    'hard': ['APPLY', 'ANALYZE']  # Limited analysis for elementary
}

def get_appropriate_cognitive_level(difficulty: str, question_type: str) -> List[str]:
    """Get age-appropriate cognitive levels for elementary students."""
    base_levels = ELEMENTARY_COGNITIVE_LEVELS[difficulty.lower()]
    
    # Adjust based on question type
    if question_type == 'math':
        # Math can handle more application at elementary level
        return base_levels + ['APPLY'] if 'APPLY' not in base_levels else base_levels
    
    return base_levels
```

## 🔍 RAG (Retrieval-Augmented Generation)

### Knowledge Base Construction
```python
# Build knowledge base of validated questions
def build_question_knowledge_base():
    # Extract questions from training data
    # Generate embeddings for semantic search
    # Index for fast retrieval
    # Maintain quality metrics
```

### Semantic Search Implementation
```python
# Implement semantic search for example retrieval
def retrieve_relevant_examples(query: str, question_type: str, count: int = 3):
    # Generate query embedding
    # Search similar questions
    # Filter by quality and relevance
    # Return diverse examples
```

### Cost Optimization
- **Embedding Storage**: ~$100/month (FAISS + embeddings)
- **Search Optimization**: Efficient indexing for fast retrieval
- **Caching**: Cache frequently used examples

## 🎯 Fine-Tuning Strategy

### When to Fine-Tune
- **Prerequisites**: >1k high-quality questions
- **Cost**: ~$500 initial cost for GPT-3.5 fine-tuning
- **Maintenance**: Keep RAG for dynamic updates

### Fine-Tuning Process
```python
# Prepare training data for fine-tuning
def prepare_fine_tuning_data():
    # Select high-quality questions
    # Format for fine-tuning
    # Validate data quality
    # Split into train/validation sets
```

### Long-term Strategy
- **RAG + Fine-tuned Model**: Best of both worlds
- **RAG**: For example retrieval and dynamic updates
- **Fine-tuned Model**: For generation with domain expertise

## 📄 PDF Processing Pipeline

### PDF Extraction & Cleaning
**Tools Needed:**
- **Free PDF parser**: PyMuPDF
- **OCR (if scanned PDFs)**: Tesseract
- **Data cleaning**: Python + RegEx

```python
def extract_questions_from_pdf(pdf_path: str) -> List[Question]:
    # Extract text from PDF
    # Apply OCR if needed
    # Clean and format text
    # Parse questions and answers
    # Validate extracted content
```

### Question Classification & Tagging
```python
def classify_and_tag_questions(questions: List[str]) -> List[TaggedQuestion]:
    # Zero-shot classification using transformers
    # Embedding model: all-MiniLM-L6-v2
    # Tag by question type, difficulty, topic
    # Validate classifications
```

## 🔧 Implementation Details

### Provider Management
```python
class LLMProviderManager:
    def __init__(self):
        self.providers = {
            'gemini': GeminiProvider(),
            'deepseek': DeepSeekProvider(),
            'openai': OpenAIProvider()
        }
    
    async def generate_with_fallback(self, prompt: str, primary_provider: str):
        # Try primary provider
        # Fallback to secondary providers
        # Handle errors gracefully
        # Return best result
```

### Quality Pipeline
```python
class QuestionQualityAssessor:
    def __init__(self):
        self.readability_checker = ReadabilityChecker()
        self.ssat_validator = SSATValidator()
        self.cognitive_assessor = CognitiveAssessor()
    
    def assess_question_quality(self, question: Question) -> QualityReport:
        # Comprehensive quality assessment
        # Multiple validation layers
        # Quality scoring
        # Improvement suggestions
```

### Error Handling
```python
async def robust_generation(prompt: str, max_retries: int = 3):
    # Retry logic for failed requests
    # Provider fallback
    # Graceful degradation
    # Error logging and monitoring
```

## 📊 Success Metrics

- **Readability**: 95%+ of questions score ≤ 4.0 Flesch-Kincaid Grade Level
- **Vocabulary**: 98%+ of vocabulary appropriate for elementary students
- **SSAT Compliance**: 90%+ compliance with authentic SSAT format characteristics
- **Cognitive Appropriateness**: 95%+ of questions match target cognitive level
- **Overall Quality**: Average quality score ≥ 0.85/1.0

## 🔗 Dependencies

### Required Libraries
- `textstat` - Readability calculations
- `nltk` - Natural language processing
- `spacy` - Advanced text analysis
- `sentence-transformers` - Text embeddings
- `httpx` - Async HTTP client

### External Services
- Google Gemini API
- DeepSeek API
- OpenAI API
- Supabase (for storage and embeddings)

## 📚 Additional Resources

- [Quality Improvements Roadmap](QUALITY_IMPROVEMENTS.md)
- [Backend API Documentation](../backend/README.md)
- [Supabase Vector Search](https://supabase.com/docs/guides/ai/vector-embeddings)
- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)

---

**Note**: This implementation focuses on educational quality and age-appropriateness for elementary SSAT preparation. Regular monitoring and updates are essential for maintaining high-quality question generation.