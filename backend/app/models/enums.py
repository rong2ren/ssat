"""Unified enums for the SSAT Question Generator."""

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

class CognitiveLevel(str, Enum):
    """Cognitive complexity levels for questions."""
    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"

class SectionType(str, Enum):
    """SSAT test sections."""
    QUANTITATIVE = "Quantitative"
    VERBAL = "Verbal"
    READING = "Reading"
    WRITING = "Writing"