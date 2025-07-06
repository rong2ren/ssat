# Scrape SSAT questions
Use tools like Scrapy to gather publicly available SSAT practice questions from forums (e.g., Reddit’s r/SSAT), educational blogs, and free test-prep sites.

# Data Labeling
Metadata Tagging: Label questions with:
- Difficulty level (Easy/Medium/Hard).
- Section (Verbal, Math, Reading).
- Skill tested (e.g., “vocabulary-in-context”, “algebraic equations”).

Bias Mitigation: Use tools like Hugging Face’s datasets to flag biased language (e.g., gender stereotypes in word problems).

# Fine-Tuning LLM:

Phase 1: General question generation (e.g., “Generate 5th-grade math questions”).

Phase 2: SSAT-specific tuning (e.g., reading comprehension with 250-word passages).

Phase 3: Bias mitigation using DebiasBERT to filter culturally insensitive content.

# Evaluation Metrics:

Use BLEU score for linguistic quality and RUBRIC (rule-based metric) for SSAT alignment.