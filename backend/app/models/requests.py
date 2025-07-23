"""Request models for the SSAT Question Generator API."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal, Dict

from .enums import QuestionType, DifficultyLevel, LLMProvider

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
        description="Number of questions to generate"
    )
    provider: Optional[LLMProvider] = Field(
        default=None,
        description="Preferred LLM provider (uses best available if not specified)"
    )
    level: str = Field(
        default="elementary",
        description="Educational level (elementary, middle, high)"
    )
    is_official_format: bool = Field(
        default=False,
        description="Whether this is for official SSAT format (allows up to 30 questions)"
    )
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v):
        """Validate topic input."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v
    
    @model_validator(mode='after')
    def validate_count_after_fields(self) -> 'QuestionGenerationRequest':
        """Validate count based on official format flag after all fields are set."""
        if self.count > 30:
            raise ValueError(f"Invalid count: must be 1-30, got {self.count}")
        elif self.is_official_format and self.count > 30:
            raise ValueError(f"Invalid count: must be 1-30 for official format, got {self.count}")
        elif not self.is_official_format and self.count > 15:
            raise ValueError(f"Invalid count: must be 1-15 for custom generation, got {self.count}")
        
        return self

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
    custom_counts: Optional[Dict[str, int]] = Field(
        default=None,
        description="Custom question counts per section (e.g., {'quantitative': 10, 'verbal': 8})"
    )
    is_official_format: bool = Field(
        default=False,
        description="Whether this is an official SSAT format test (affects question generation strategy)"
    )
    
    @field_validator('include_sections')
    @classmethod
    def validate_sections(cls, v):
        """Ensure at least one section is included."""
        if not v or len(v) == 0:
            raise ValueError("At least one section must be included")
        return v
    
    @field_validator('custom_counts')
    @classmethod
    def validate_custom_counts(cls, v, info):
        """Validate custom counts if provided."""
        if v is not None:
            if hasattr(info.data, 'include_sections'):
                # Ensure all included sections have counts
                for section in info.data['include_sections']:
                    if section.value not in v:
                        raise ValueError(f"Custom count missing for section: {section.value}")
                
                # Check if this is official format
                is_official = getattr(info.data, 'is_official_format', False)
                
                # Ensure counts are reasonable
                for section, count in v.items():
                    if not isinstance(count, int) or count < 1:
                        raise ValueError(f"Invalid count for {section}: must be at least 1")
                    
                    # For custom generation, limit to 15 questions per section
                    if not is_official and count > 15:
                        raise ValueError(f"Invalid count for {section}: must be 1-15 for custom generation")
                    
                    # For official format, allow up to 30 questions per section
                    if is_official and count > 30:
                        raise ValueError(f"Invalid count for {section}: must be 1-30 for official format")
        return v


    
