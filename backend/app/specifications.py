"""Official SSAT Elementary Level test specifications and business rules"""

from typing import Dict, List
from dataclasses import dataclass

# ========================================
# STANDARDIZED QUANTITATIVE SUBSECTIONS
# Single source of truth for all quantitative question categorization
# ========================================

QUANTITATIVE_SUBSECTIONS = [
    # Number Operations (40% of questions)
    "Number Sense", "Arithmetic", "Fractions", "Decimals", "Percentages",
    # Algebra Functions (20% of questions)  
    "Patterns", "Sequences", "Algebra", "Variables",
    # Geometry Spatial (25% of questions)
    "Area", "Perimeter", "Shapes", "Spatial",
    # Measurement (10% of questions)
    "Measurement", "Time", "Money",
    # Probability Data (5% of questions)
    "Probability", "Data", "Graphs"
]

def validate_quantitative_subsection(subsection: str) -> bool:
    """Validate that a subsection is one of the standardized options."""
    return subsection in QUANTITATIVE_SUBSECTIONS

# ========================================
# EXISTING SPECIFICATIONS
# ========================================

@dataclass
class SectionSpec:
    """Specification for a single test section"""
    name: str
    question_count: int
    time_minutes: int
    section_type: str  # "scored" or "unscored"
    break_after: bool
    instructions: str
    question_types: List[str]

# OFFICIAL SSAT Elementary Level Specifications (Exact Match)
OFFICIAL_ELEMENTARY_SPECS = {
    "sections": [
        SectionSpec(
            name="Quantitative",
            question_count=30,
            time_minutes=30,
            section_type="scored",
            break_after=False,
            instructions="Solve each problem and select the best answer. You may NOT use a calculator.",
            question_types=["quantitative"]
        ),
        SectionSpec(
            name="Verbal", 
            question_count=30,
            time_minutes=20,
            section_type="scored",
            break_after=True,  # 15-minute break after Verbal
            instructions="Choose the word that is most similar in meaning to the word in capital letters, or complete the analogy.",
            question_types=["synonym", "analogy"]
        ),
        SectionSpec(
            name="Reading",
            question_count=28,  # Exactly 7 passages × 4 questions each
            time_minutes=30,
            section_type="scored", 
            break_after=False,
            instructions="Read each passage carefully and answer the questions that follow.",
            question_types=["reading"]
        ),
        SectionSpec(
            name="Writing",
            question_count=1,
            time_minutes=15,
            section_type="unscored",
            break_after=False,
            instructions="Look at the picture and write a story with a beginning, middle, and end.",
            question_types=["writing"]
        )
    ],
    "total_scored_questions": 88,  # 30+30+28 (writing is unscored)
    "total_time": 110,  # 30+20+15+30+15 minutes
    "scored_sections": ["Quantitative", "Verbal", "Reading"],
    "break_schedule": {
        "after_verbal": 15  # 15-minute break after Verbal section
    },
    
    # Official Question Distribution
    "quantitative_distribution": {
        "number_operations": 0.40,    # 12 questions - arithmetic, number sense
        "algebra_functions": 0.20,    # 6 questions - patterns, basic algebra  
        "geometry_spatial": 0.25,     # 7-8 questions - shapes, spatial reasoning
        "measurement": 0.10,          # 3 questions - length, weight, time
        "probability_data": 0.05      # 1-2 questions - simple probability, data analysis
    },
    
    "verbal_distribution": {
        "synonyms": 0.60,    # 18 questions - word meaning similarity
        "analogies": 0.40    # 12 questions - word relationship patterns
    },
    
    "reading_structure": {
        "passages": 7,
        "questions_per_passage": 4,
        "total_questions": 28,  # 7 × 4 = 28
        "passage_types": ["fiction", "non_fiction", "poetry"],  # Mix of types
        "passage_length": 450,  # Target word count for reading passages
        "comprehension_skills": [
            "main_idea",
            "supporting_details", 
            "inference",
            "vocabulary_in_context",
            "author_purpose",
            "sequence_of_events"
        ]
    }
}

# Elementary-appropriate writing prompts (picture-based storytelling)
ELEMENTARY_WRITING_PROMPTS = [
    {
        "prompt": "Look at this picture of children building a treehouse. Write a story about their adventure.",
        "visual_description": "Children working together with wood and tools to build a treehouse",
        "grade_level": "3-4",

    },
    {
        "prompt": "You find a magic key that can open any door. Write a story about where you go and what you discover.",
        "visual_description": "An ornate, glowing key lying on a wooden table",
        "grade_level": "3-4",

    },
    {
        "prompt": "A friendly robot appears in your backyard. Write a story about what happens next.",
        "visual_description": "Small, colorful robot with friendly LED eyes standing in a garden",
        "grade_level": "3-4",

    },
    {
        "prompt": "You wake up to find your pet can talk for one day. Write a story about your conversations.",
        "visual_description": "Child sitting with a dog that appears to be speaking",
        "grade_level": "3-4",

    },
    {
        "prompt": "Your family goes camping and you discover a hidden cave. Write a story about what you find inside.",
        "visual_description": "Family with flashlights near the entrance of a mysterious cave",
        "grade_level": "3-4",

    },
    {
        "prompt": "A new student joins your class who is from another planet. Write a story about your friendship.",
        "visual_description": "Two children sitting together, one looking slightly unusual with kind eyes",
        "grade_level": "3-4",

    },
    {
        "prompt": "You find an old treasure map in your grandmother's attic. Write a story about following the map.",
        "visual_description": "An aged, folded map with an X marking a location",
        "grade_level": "3-4", 

    },
    {
        "prompt": "The animals in the zoo can talk to you for one hour. Write a story about what they tell you.",
        "visual_description": "Child standing in front of various zoo animals who appear to be speaking",
        "grade_level": "3-4",

    }
]

# Math topic keywords for question generation
MATH_TOPIC_KEYWORDS = {
    "number_operations": [
        "addition", "subtraction", "multiplication", "division",
        "number sense", "place value", "rounding", "estimation",
        "fractions", "decimals", "order of operations"
    ],
    "algebra_functions": [
        "patterns", "sequences", "missing numbers", "number relationships",
        "simple equations", "input output tables", "function machines"
    ],
    "geometry_spatial": [
        "shapes", "polygons", "angles", "lines", "symmetry",
        "area", "perimeter", "volume", "3d shapes", "coordinate plane",
        "transformations", "spatial reasoning"
    ],
    "measurement": [
        "length", "weight", "capacity", "time", "temperature",
        "units of measurement", "converting units", "elapsed time",
        "money", "measuring tools"
    ],
    "probability_data": [
        "probability", "likelihood", "certain", "impossible",
        "graphs", "charts", "data analysis", "surveys",
        "mean", "mode", "range"
    ]
}

# Verbal topic keywords for question generation  
VERBAL_TOPIC_KEYWORDS = {
    "synonyms": [
        "vocabulary", "word meaning", "similar words", "definitions",
        "context clues", "elementary vocabulary", "grade level words"
    ],
    "analogies": [
        "word relationships", "patterns", "comparisons", "connections",
        "part to whole", "synonyms", "antonyms", "category relationships"
    ]
}

# Validation functions
def validate_test_structure(sections: List[Dict]) -> bool:
    """Validate that test sections match official SSAT Elementary structure"""
    required_sections = {"Quantitative": 30, "Verbal": 30, "Reading": 28}
    
    section_counts = {}
    for section in sections:
        section_counts[section["section_name"]] = section["question_count"]
    
    for name, expected_count in required_sections.items():
        if section_counts.get(name) != expected_count:
            return False
    
    return True

def get_section_by_name(section_name: str) -> SectionSpec:
    """Get section specification by name"""
    for section in OFFICIAL_ELEMENTARY_SPECS["sections"]:
        if section.name == section_name:
            return section
    raise ValueError(f"Unknown section: {section_name}")

def calculate_total_time() -> int:
    """Calculate total test time including breaks"""
    total = 0
    for section in OFFICIAL_ELEMENTARY_SPECS["sections"]:
        total += section.time_minutes
    
    # Add break time (15 minutes after Verbal)
    total += OFFICIAL_ELEMENTARY_SPECS["break_schedule"]["after_verbal"]
    
    return total

def get_question_distribution(section_name: str) -> Dict[str, float]:
    """Get question distribution for a section"""
    if section_name == "Quantitative":
        return OFFICIAL_ELEMENTARY_SPECS["quantitative_distribution"]
    elif section_name == "Verbal":
        return OFFICIAL_ELEMENTARY_SPECS["verbal_distribution"]
    else:
        return {}

def get_official_question_counts() -> Dict[str, int]:
    """Get the official SSAT Elementary Level question counts for each section type.
    
    Returns:
        Dict mapping section type to official question count
        Note: For reading, this returns the number of PASSAGES (7), not questions (28)
    """
    return {
        "quantitative": 30,
        "analogy": 12,  # Part of Verbal section (40% of 30)
        "synonym": 18,  # Part of Verbal section (60% of 30)
        "reading": 7,   # 7 passages (each with 4 questions = 28 total questions)
        "writing": 1
    }

def get_official_question_counts_by_section() -> Dict[str, int]:
    """Get the official SSAT Elementary Level question counts by section name.
    
    Returns:
        Dict mapping section name to official question count
    """
    return {
        "Quantitative": 30,
        "Verbal": 30,  # Total verbal (synonyms + analogies)
        "Reading": 28,  # 7 passages × 4 questions each
        "Writing": 1
    }

# Test configuration integrity
def validate_config():
    """Validate that configuration is internally consistent"""
    specs = OFFICIAL_ELEMENTARY_SPECS
    
    # Check total scored questions
    total_scored = sum(
        section.question_count 
        for section in specs["sections"] 
        if section.section_type == "scored"
    )
    
    assert total_scored == 88, f"Expected 88 scored questions, got {total_scored}"  # 30+30+28
    
    # Check total time
    calculated_time = calculate_total_time()
    assert calculated_time == specs["total_time"], f"Time mismatch: {calculated_time} vs {specs['total_time']}"
    
    # Check question distributions sum to 1.0
    for section_name in ["quantitative_distribution", "verbal_distribution"]:
        if section_name in specs:
            distribution = specs[section_name]
            total = sum(distribution.values())
            assert abs(total - 1.0) < 0.01, f"{section_name} distribution doesn't sum to 1.0: {total}"
    
    print("✅ Configuration validation passed")

if __name__ == "__main__":
    validate_config()