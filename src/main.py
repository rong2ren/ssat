"""Main entry point for SSAT question generator CLI."""

import json
import argparse

from ssat.models import QuestionType, DifficultyLevel, QuestionRequest
from ssat.generator import generate_questions
from loguru import logger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="SSAT Question Generator CLI")
    parser.add_argument(
        "--type",
        choices=[qt.value for qt in QuestionType],
        default=QuestionType.MATH.value,
        help="Type of question to generate (math, reading, verbal, analogy, synonym, writing)"
    )
    parser.add_argument(
        "--difficulty",
        choices=[dl.value for dl in DifficultyLevel],
        default=DifficultyLevel.STANDARD.value,
        help="Difficulty level (standard, advanced)"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Specific topic for the question (optional, e.g. 'fractions', 'geometry')"
    )
    parser.add_argument(
        "--count", 
        type=int, 
        default=1,
        help="Number of questions to generate"
    )
    parser.add_argument(
        "--level", 
        type=str, 
        default="elementary",
        choices=["elementary", "middle", "high"],
        help="Level of questions to generate (elementary, middle, high)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        help="Output file path for JSON result (if not specified, prints to console)"
    )
    
    return parser.parse_args()


def main():
    """Run the question generator CLI."""
    args = parse_args()
    
    
    
    # Create request
    request = QuestionRequest(
        question_type=args.type,
        difficulty=args.difficulty,
        topic=args.topic,
        count=args.count,
        level=args.level
    )
    
    try:
        # Generate questions
        logger.debug(f"Request details: {request}")
        # questions = generator.generate_questions(request)
        questions = generate_questions(request)
        logger.info(f"Successfully generated {len(questions)} questions")
        
        # Convert to dict for JSON serialization
        questions_json = [q.model_dump() for q in questions]
        
        if args.output:
            # Write to file
            with open(args.output, "w") as f:
                json.dump(questions_json, f, indent=2)
            logger.info(f"Questions saved to {args.output}")
        else:
            # Print to console
            print(json.dumps(questions_json, indent=2))
    
    except Exception as e:
        logger.exception(f"Error generating questions: {e}")


if __name__ == "__main__":
    main()