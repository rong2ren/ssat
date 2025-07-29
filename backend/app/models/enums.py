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

