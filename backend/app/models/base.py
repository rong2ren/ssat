"""Base models and common components."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from .enums import QuestionType, DifficultyLevel

class Option(BaseModel):
    """Option for multiple choice questions."""
    letter: str = Field(..., description="Option letter (A, B, C, D)")
    text: str = Field(..., description="Option text")

class Question(BaseModel):
    """SSAT question model."""
    id: Optional[str] = None
    question_type: QuestionType
    difficulty: DifficultyLevel
    text: str
    options: List[Option] = Field(default_factory=list)
    correct_answer: str
    explanation: str
    cognitive_level: str
    tags: List[str] = Field(default_factory=list)
    visual_description: Optional[str] = None
    subsection: Optional[str] = None  # AI-determined subsection for better categorization
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError("SSAT requires exactly 4 options")
        letters = {opt.letter.upper() for opt in v}
        if letters != {'A','B','C','D'}:
            raise ValueError("Options must have letters A-D")
        return v
    
    @field_validator('correct_answer')
    @classmethod
    def validate_correct_answer(cls, v):
        if v.upper() not in {'A', 'B', 'C', 'D'}:
            raise ValueError("Correct answer must be one of A, B, C, or D")
        return v.upper()

class QuestionRequest(BaseModel):
    """Request model for generating questions."""
    question_type: QuestionType
    difficulty: DifficultyLevel
    topic: Optional[str] = None
    count: int = 1
    level: str = "elementary" # elementary, middle, or high school
    input_format: str = "full"  # full or simple (for synonyms only)