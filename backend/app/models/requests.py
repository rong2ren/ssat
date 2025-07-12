"""Request models for the SSAT Question Generator API."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from enum import Enum

class QuestionType(str, Enum):
    """Types of SSAT questions."""
    QUANTITATIVE = "quantitative"
    READING = "reading"
    VERBAL = "verbal"
    ANALOGY = "analogy"
    SYNONYM = "synonym"
    WRITING = "writing"

class DifficultyLevel(str, Enum):
    """Difficulty levels for elementary SSAT."""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class LLMProvider(str, Enum):
    """Available LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"

class QuestionGenerationRequest(BaseModel):
    """Request model for generating individual questions."""
    
    question_type: QuestionType = Field(
        ..., 
        description="Type of questions to generate"
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM,
        description="Difficulty level of questions"
    )
    topic: Optional[str] = Field(
        default=None,
        description="Specific topic to focus on (optional)",
        max_length=100
    )
    count: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Number of questions to generate (1-20)"
    )
    provider: Optional[LLMProvider] = Field(
        default=None,
        description="Preferred LLM provider (uses best available if not specified)"
    )
    level: str = Field(
        default="elementary",
        description="Educational level (elementary, middle, high)"
    )
    
    @validator('topic')
    def validate_topic(cls, v):
        """Validate topic input."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v

class CompleteTestRequest(BaseModel):
    """Request model for generating a complete SSAT practice test."""
    
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM,
        description="Overall difficulty level for the test"
    )
    provider: Optional[LLMProvider] = Field(
        default=None,
        description="Preferred LLM provider (uses best available if not specified)"
    )
    include_sections: List[QuestionType] = Field(
        default=[QuestionType.QUANTITATIVE, QuestionType.VERBAL, QuestionType.READING, QuestionType.WRITING],
        description="Sections to include in the complete test"
    )
    custom_counts: Optional[dict] = Field(
        default=None,
        description="Custom question counts per section (e.g., {'math': 10, 'verbal': 8})"
    )
    
    @validator('include_sections')
    def validate_sections(cls, v):
        """Ensure at least one section is included."""
        if not v or len(v) == 0:
            raise ValueError("At least one section must be included")
        return v
    
    @validator('custom_counts')
    def validate_custom_counts(cls, v, values):
        """Validate custom counts if provided."""
        if v is not None:
            if 'include_sections' in values:
                # Ensure all included sections have counts
                for section in values['include_sections']:
                    if section.value not in v:
                        raise ValueError(f"Custom count missing for section: {section.value}")
                
                # Ensure counts are reasonable
                for section, count in v.items():
                    if not isinstance(count, int) or count < 1 or count > 25:
                        raise ValueError(f"Invalid count for {section}: must be 1-25")
        return v

class CompleteElementaryTestRequest(BaseModel):
    """Request model for generating complete SSAT Elementary test (Official Format)."""
    
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM,
        description="Overall difficulty level for the entire test"
    )
    include_experimental: bool = Field(
        default=False,
        description="Whether to include experimental section (not part of official format)"
    )
    student_grade: Optional[Literal["3", "4"]] = Field(
        default=None,
        description="Target student grade level (3 or 4)"
    )
    test_focus: Optional[str] = Field(
        default=None,
        description="Optional topic focus across all sections",
        max_length=100
    )
    
    @validator('test_focus')
    def validate_test_focus(cls, v):
        """Validate test focus input."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v