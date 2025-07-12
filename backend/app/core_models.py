"""Data models for SSAT questions and answers."""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

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


class Option(BaseModel):
    """Option for multiple choice questions."""
    letter: str  # A, B, C, D
    text: str


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

# ===============================
# Complete SSAT Test Models
# ===============================

class TestSection(BaseModel):
    """Individual section of a complete SSAT test"""
    section_name: str  # "Quantitative", "Verbal", "Reading", "Writing"
    section_type: str  # "scored" or "unscored"
    questions: List[Question] = Field(default_factory=list)
    question_count: int
    time_limit_minutes: int
    instructions: str
    break_after: bool = False  # Whether to include break after this section

    @field_validator('section_name')
    def validate_section_name(cls, v):
        valid_sections = {"Quantitative", "Verbal", "Reading", "Writing"}
        if v not in valid_sections:
            raise ValueError(f"Section name must be one of {valid_sections}")
        return v

    @field_validator('section_type')
    def validate_section_type(cls, v):
        if v not in {"scored", "unscored"}:
            raise ValueError("Section type must be 'scored' or 'unscored'")
        return v

class WritingPrompt(BaseModel):
    """Writing section prompt for SSAT Elementary"""
    prompt_text: str
    prompt_type: str = "picture_story"  # Elementary uses picture prompts
    instructions: str
    time_limit_minutes: int = 15
    visual_description: Optional[str] = None  # Description of the picture prompt

    @field_validator('prompt_text')
    def validate_prompt_text(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Writing prompt must be at least 10 characters")
        return v.strip()

class CompleteSSATTest(BaseModel):
    """Complete SSAT Elementary Level test"""
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    test_type: str = "Elementary Level SSAT"
    sections: List[TestSection]
    writing_prompt: WritingPrompt
    total_scored_questions: int = 88  # Official count: 30+30+28 (writing is unscored)
    total_time_minutes: int = 110  # 30+20+15+30+15
    difficulty: DifficultyLevel
    grade_level: str = "3-4"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('total_scored_questions')
    def validate_total_scored_questions(cls, v):
        if v != 88:
            raise ValueError("Official SSAT Elementary must have exactly 88 scored questions")
        return v

    @field_validator('total_time_minutes')
    def validate_total_time(cls, v):
        if v != 110:
            raise ValueError("Official SSAT Elementary must be exactly 110 minutes")
        return v

    @field_validator('sections')
    def validate_sections_structure(cls, v):
        # Validate we have the correct sections
        section_names = [section.section_name for section in v]
        expected_sections = ["Quantitative", "Verbal", "Reading"]
        
        for expected in expected_sections:
            if expected not in section_names:
                raise ValueError(f"Missing required section: {expected}")
        
        # Validate question counts
        section_counts = {section.section_name: section.question_count for section in v}
        expected_counts = {"Quantitative": 30, "Verbal": 30, "Reading": 28}
        
        for section_name, expected_count in expected_counts.items():
            if section_counts.get(section_name) != expected_count:
                actual = section_counts.get(section_name, 0)
                raise ValueError(f"Section {section_name} must have {expected_count} questions, got {actual}")
        
        return v