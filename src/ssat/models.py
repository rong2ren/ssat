"""Data models for SSAT questions and answers."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field,field_validator

class QuestionType(str, Enum):
    """Types of SSAT questions."""
    MATH = "math"
    READING = "reading"
    VERBAL = "verbal"
    ANALOGY = "analogy"
    SYNONYM = "synonym"
    WRITING = "writing"


class DifficultyLevel(str, Enum):
    """Difficulty levels for elementary SSAT."""
    STANDARD = "standard"
    ADVANCED = "advanced"

class Option(BaseModel):
    """Option for multiple choice questions."""
    letter: str  # A, B, C, D
    text: str

class CognitiveLevel(str, Enum):
    REMEMBER = "REMEMBER" # Basic recall of facts, terms, or concepts
    UNDERSTAND = "UNDERSTAND" # Understanding the relationship between facts, terms, or concepts
    APPLY = "APPLY" # Applying knowledge to a new situation
    ANALYZE = "ANALYZE" # Analyzing information to draw conclusions
    EVALUATE = "EVALUATE" # Evaluating information to make judgments

class Question(BaseModel):
    """SSAT question model."""
    id: Optional[str] = None
    question_type: QuestionType
    difficulty: DifficultyLevel
    text: str
    options: List[Option] = Field(default_factory=list)
    correct_answer: str
    explanation: str
    cognitive_level: CognitiveLevel
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('options')
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError("SSAT requires exactly 4 options")
        letters = {opt.letter.upper() for opt in v}
        if letters != {'A','B','C','D'}:
            raise ValueError("Options must have letters A-D")
        return v
    
    @field_validator('correct_answer')
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