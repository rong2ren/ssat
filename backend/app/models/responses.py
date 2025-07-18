"""Response models for the SSAT Question Generator API."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime

from .enums import QuestionType

# Import Option from base module to avoid duplication
from .base import Option

class GeneratedQuestion(BaseModel):
    """A generated SSAT question."""
    id: Optional[str] = Field(default=None, description="Question ID")
    question_type: str = Field(..., description="Type of question")
    difficulty: str = Field(..., description="Difficulty level")
    text: str = Field(..., description="Question text")
    options: List[Option] = Field(default_factory=list, description="Answer options")
    correct_answer: str = Field(..., description="Correct answer (A, B, C, or D)")
    explanation: str = Field(..., description="Detailed explanation")
    cognitive_level: str = Field(..., description="Cognitive complexity level")
    subsection: Optional[str] = Field(default=None, description="AI-generated subsection categorization")
    tags: List[str] = Field(default_factory=list, description="Question tags")
    visual_description: Optional[str] = Field(default=None, description="Visual elements description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class GenerationMetadata(BaseModel):
    """Metadata about the question generation process."""
    generation_time: float = Field(..., description="Time taken to generate questions (seconds)")
    provider_used: str = Field(..., description="LLM provider used")
    training_examples_count: int = Field(..., description="Number of training examples used")
    training_example_ids: List[str] = Field(default_factory=list, description="IDs of training examples used")
    request_id: Optional[str] = Field(default=None, description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Generation timestamp")

class ReadingPassage(BaseModel):
    """A reading passage with associated questions."""
    id: str = Field(..., description="Unique passage identifier")
    title: Optional[str] = Field(default=None, description="Passage title")
    text: str = Field(..., description="Passage text (150-200 words for elementary)")
    passage_type: str = Field(..., description="Type of reading passage")
    grade_level: str = Field(default="3-4", description="Target grade level")
    topic: str = Field(..., description="Passage topic/theme")
    questions: List[GeneratedQuestion] = Field(..., description="Questions based on this passage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional passage metadata")

class WritingPrompt(BaseModel):
    """A writing prompt for the writing section."""
    prompt_text: str = Field(..., description="The main writing prompt")
    instructions: str = Field(..., description="Instructions for students")
    visual_description: Optional[str] = Field(default=None, description="Description of visual prompt")
    grade_level: str = Field(default="3-4", description="Target grade level")
    story_elements: List[str] = Field(default_factory=list, description="Suggested story elements")
    prompt_type: str = Field(default="picture_story", description="Type of writing prompt")
    tags: List[str] = Field(default_factory=list, description="Writing skills and element tags")
    subsection: Optional[str] = Field(default=None, description="AI-generated subsection categorization")
    
    def model_dump(self, **kwargs):
        """Custom serialization to exclude empty visual descriptions."""
        data = super().model_dump(**kwargs)
        
        # Remove visual_description if it's empty or contains generic "none" values
        if 'visual_description' in data:
            visual_desc = data['visual_description']
            if not visual_desc or not visual_desc.strip() or \
               visual_desc.lower() in ["none", "no visual elements", "no visual elements required", ""]:
                del data['visual_description']
        
        return data

class QuantitativeSection(BaseModel):
    """Mathematics section - arithmetic, fractions, geometry, word problems."""
    section_type: Literal[QuestionType.QUANTITATIVE] = QuestionType.QUANTITATIVE
    questions: List[GeneratedQuestion] = Field(..., description="Math questions")
    time_limit_minutes: int = Field(..., description="Time limit for this section")
    instructions: str = Field(..., description="Section instructions")

class SynonymSection(BaseModel):
    """Vocabulary section - word meaning and definition questions."""
    section_type: Literal[QuestionType.SYNONYM] = QuestionType.SYNONYM
    questions: List[GeneratedQuestion] = Field(..., description="Synonym questions")
    time_limit_minutes: int = Field(..., description="Time limit for this section")
    instructions: str = Field(..., description="Section instructions")

class AnalogySection(BaseModel):
    """Word relationship section - logical reasoning with word pairs."""
    section_type: Literal[QuestionType.ANALOGY] = QuestionType.ANALOGY
    questions: List[GeneratedQuestion] = Field(..., description="Analogy questions")
    time_limit_minutes: int = Field(..., description="Time limit for this section")
    instructions: str = Field(..., description="Section instructions")

class ReadingSection(BaseModel):
    """Reading comprehension section with passages and questions."""
    section_type: Literal[QuestionType.READING] = QuestionType.READING
    passages: List[ReadingPassage] = Field(..., description="Reading passages with questions")
    time_limit_minutes: int = Field(..., description="Time limit for this section")
    instructions: str = Field(..., description="Section instructions")

class WritingSection(BaseModel):
    """Writing section with a single prompt."""
    section_type: Literal[QuestionType.WRITING] = QuestionType.WRITING
    prompt: WritingPrompt = Field(..., description="Writing prompt")
    time_limit_minutes: int = Field(..., description="Time limit for this section")
    instructions: str = Field(..., description="Section instructions")

# Union type for polymorphic sections
TestSection = Union[QuantitativeSection, SynonymSection, AnalogySection, ReadingSection, WritingSection]

# Content generation response models (now that data models are defined)
class QuestionGenerationResponse(BaseModel):
    """Response for individual question generation."""
    questions: List[GeneratedQuestion] = Field(..., description="Generated questions")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")
    status: str = Field(default="success", description="Generation status")
    count: int = Field(..., description="Number of questions generated")

class ReadingGenerationResponse(BaseModel):
    """Response for reading passage generation."""
    passages: List[ReadingPassage] = Field(..., description="Generated reading passages")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")
    status: str = Field(default="success", description="Generation status")
    count: int = Field(..., description="Number of passages generated")
    total_questions: int = Field(..., description="Total questions across all passages")

class WritingGenerationResponse(BaseModel):
    """Response for writing prompt generation."""
    prompts: List[WritingPrompt] = Field(..., description="Generated writing prompts")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")
    status: str = Field(default="success", description="Generation status")
    count: int = Field(..., description="Number of prompts generated")

# Union type for polymorphic content generation responses
ContentGenerationResponse = Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]


class ProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str = Field(..., description="Provider name")
    available: bool = Field(..., description="Whether provider is available")
    response_time: Optional[float] = Field(default=None, description="Average response time (seconds)")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")
    last_checked: datetime = Field(default_factory=datetime.now, description="Last status check time")

class ProviderStatusResponse(BaseModel):
    """Response for provider status check."""
    providers: List[ProviderInfo] = Field(..., description="Status of all providers")
    recommended: str = Field(..., description="Recommended provider to use")
    total_available: int = Field(..., description="Number of available providers")

class HealthResponse(BaseModel):
    """Response for health check."""
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    message: str = Field(..., description="Status message")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")
    database_connected: Optional[bool] = Field(default=None, description="Database connection status")
    
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier")

class WritingPromptResponse(BaseModel):
    """Writing prompt for SSAT Elementary test."""
    prompt_text: str = Field(..., description="Writing prompt text")
    instructions: str = Field(..., description="Writing instructions")
    time_limit_minutes: int = Field(default=15, description="Time limit for writing")
    visual_description: Optional[str] = Field(default=None, description="Description of visual prompt")

class ElementaryTestSectionResponse(BaseModel):
    """A section of the official SSAT Elementary test."""
    section_name: str = Field(..., description="Section name (Quantitative, Verbal, Reading)")
    section_type: str = Field(..., description="Section type (scored or unscored)")
    questions: List[GeneratedQuestion] = Field(..., description="Questions in this section")
    question_count: int = Field(..., description="Number of questions in section")
    time_limit_minutes: int = Field(..., description="Official time limit for section")
    instructions: str = Field(..., description="Section instructions")
    break_after: bool = Field(default=False, description="Whether break follows this section")

class CompleteElementaryTestResponse(BaseModel):
    """Response for complete SSAT Elementary test generation (Official Format)."""
    test: Dict[str, Any] = Field(..., description="Complete test data")  # Will contain CompleteSSATTest
    sections_summary: Dict[str, int] = Field(..., description="Question count per section")
    total_questions: int = Field(..., description="Total questions (should be 89 scored)")
    estimated_completion_time: int = Field(..., description="Total time including breaks (110 min)")
    test_instructions: Dict[str, str] = Field(..., description="Instructions per section")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")
    status: str = Field(default="success", description="Generation status")
    
    # Official test information
    test_info: Dict[str, Any] = Field(
        default_factory=lambda: {
            "test_type": "Official SSAT Elementary Level",
            "grade_levels": ["3", "4"],
            "total_scored_questions": 89,
            "total_time_minutes": 110,
            "sections": [
                {"name": "Quantitative", "questions": 30, "time": 30, "scored": True},
                {"name": "Verbal", "questions": 30, "time": 20, "scored": True},
                {"name": "Break", "questions": 0, "time": 15, "scored": False},
                {"name": "Reading", "questions": 28, "time": 30, "scored": True},
                {"name": "Writing", "questions": 1, "time": 15, "scored": False}
            ],
            "format": "Official SSAT Elementary Format with exact question counts and timing"
        },
        description="Official SSAT Elementary test specifications"
    )