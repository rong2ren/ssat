"""Base models and common components."""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from .enums import QuestionType, DifficultyLevel, CognitiveLevel

class Option(BaseModel):
    """Option for multiple choice questions."""
    letter: str = Field(..., description="Option letter (A, B, C, D)")
    text: str = Field(..., description="Option text")

class Question(BaseModel):
    """Core SSAT question model."""
    id: Optional[str] = Field(default=None, description="Question ID")
    question_type: QuestionType = Field(..., description="Type of question")
    difficulty: DifficultyLevel = Field(..., description="Difficulty level")
    text: str = Field(..., description="Question text")
    options: List[Option] = Field(default_factory=list, description="Answer options")
    correct_answer: str = Field(..., description="Correct answer (A, B, C, or D)")
    explanation: str = Field(..., description="Detailed explanation")
    cognitive_level: CognitiveLevel = Field(default=CognitiveLevel.UNDERSTAND, description="Cognitive complexity level")
    tags: List[str] = Field(default_factory=list, description="Descriptive tags")
    visual_description: Optional[str] = Field(default=None, description="Visual elements description")
    subsection: Optional[str] = Field(default=None, description="AI-determined subsection")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

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
    """Request for generating questions."""
    question_type: QuestionType = Field(..., description="Type of questions to generate")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="Difficulty level")
    topic: Optional[str] = Field(default=None, description="Specific topic focus")
    count: int = Field(default=1, ge=1, le=50, description="Number of questions to generate")
    level: Optional[str] = Field(default="elementary", description="Grade level")

    def model_post_init(self, __context):
        """Post-initialization processing."""
        if self.id is None:
            self.id = str(uuid.uuid4())