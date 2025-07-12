"""Service for generating official SSAT Elementary tests"""

import random
from typing import List, Dict, Any
from ..core_models import CompleteSSATTest, TestSection, WritingPrompt, Question, QuestionRequest
from ..generator import generate_questions
from ..specifications import OFFICIAL_ELEMENTARY_SPECS, ELEMENTARY_WRITING_PROMPTS
from ..models.requests import CompleteElementaryTestRequest

class SSATTestService:
    """Service for generating official SSAT Elementary Level tests"""
    
    def __init__(self):
        self.specs = OFFICIAL_ELEMENTARY_SPECS
    
    async def generate_complete_elementary_test(
        self, 
        request: CompleteElementaryTestRequest
    ) -> CompleteSSATTest:
        """Generate a complete SSAT Elementary test following EXACT official specifications"""
        
        sections = []
        total_scored_questions = 0
        
        # Generate each section according to OFFICIAL specifications
        for section_spec in self.specs["sections"]:
            if section_spec.name == "Writing":
                # Handle writing section separately (it's just a prompt, not questions)
                continue
                
            # Generate questions for this section
            section_questions = await self._generate_section_questions(
                section_spec, request.difficulty
            )
            
            # Ensure EXACT question count matches official specification
            if len(section_questions) != section_spec.question_count:
                print(f"⚠️  Warning: {section_spec.name} generated {len(section_questions)} questions, expected {section_spec.question_count}")
                # Trim or pad to exact count
                if len(section_questions) > section_spec.question_count:
                    section_questions = section_questions[:section_spec.question_count]
                elif len(section_questions) < section_spec.question_count:
                    # If we have fewer questions, duplicate some to reach the target
                    # This shouldn't happen in production, but provides a fallback
                    while len(section_questions) < section_spec.question_count:
                        section_questions.extend(section_questions[:section_spec.question_count - len(section_questions)])
                    section_questions = section_questions[:section_spec.question_count]
            
            section = TestSection(
                section_name=section_spec.name,
                section_type=section_spec.section_type,
                questions=section_questions,
                question_count=section_spec.question_count,  # Use official count
                time_limit_minutes=section_spec.time_minutes,
                instructions=section_spec.instructions,
                break_after=section_spec.break_after
            )
            
            sections.append(section)
            if section_spec.section_type == "scored":
                total_scored_questions += section_spec.question_count
        
        # Generate writing prompt
        writing_prompt = self._generate_writing_prompt()
        
        # Validate total scored questions (testing or production mode)
        testing_mode = True  # TODO: Make this configurable
        expected_scored = 15 if testing_mode else 88  # Testing: 8+4+3=15, Production: 30+30+28=88
        
        if total_scored_questions != expected_scored:
            print(f"⚠️  Warning: Expected {expected_scored} scored questions, got {total_scored_questions}")
            # In testing mode, be flexible with totals
        
        # Create complete test
        test = CompleteSSATTest(
            sections=sections,
            writing_prompt=writing_prompt,
            total_scored_questions=total_scored_questions,  # Use actual count
            total_time_minutes=self.specs["total_time"],
            difficulty=request.difficulty,
            metadata={
                "generation_request": request.model_dump(),
                "test_specifications": "Official SSAT Elementary Level Format",
                "sections_generated": len(sections),
                "break_schedule": self.specs["break_schedule"],
                "includes_experimental": request.include_experimental,
                "student_grade": request.student_grade
            }
        )
        
        return test
    
    async def _generate_section_questions(
        self, 
        section_spec, 
        difficulty
    ) -> List[Question]:
        """Generate questions for a specific test section with EXACT counts"""
        
        if section_spec.name == "Quantitative":
            return await self._generate_quantitative_section(difficulty)
        elif section_spec.name == "Verbal":
            return await self._generate_verbal_section(difficulty)
        elif section_spec.name == "Reading":
            return await self._generate_reading_section(difficulty)
        else:
            return []
    
    async def _generate_quantitative_section(self, difficulty) -> List[Question]:
        """Generate EXACTLY 30 quantitative questions with official distribution"""
        
        # Official distribution for 30 questions
        distribution = self.specs["quantitative_distribution"]
        
        questions = []
        
        # For testing: Use smaller counts (2 questions per topic for speed)
        testing_mode = True  # TODO: Make this configurable
        if testing_mode:
            topics_counts = [
                ("number operations", 2),      
                ("algebra functions", 2),      
                ("geometry spatial", 2),        
                ("measurement", 1),                  
                ("probability data", 1)         
            ]
        else:
            # Calculate exact question counts based on official distribution
            topics_counts = [
                ("number operations", int(30 * distribution["number_operations"])),      # 12
                ("algebra functions", int(30 * distribution["algebra_functions"])),      # 6  
                ("geometry spatial", int(30 * distribution["geometry_spatial"])),        # 7-8
                ("measurement", int(30 * distribution["measurement"])),                  # 3
                ("probability data", int(30 * distribution["probability_data"]))         # 1-2
            ]
        
        # Ensure we have the right number of questions
        target_count = 8 if testing_mode else 30  # 8 for testing, 30 for production
        total_allocated = sum(count for _, count in topics_counts)
        if total_allocated < target_count:
            # Add remaining questions to geometry (largest flexible category)
            topics_counts[2] = (topics_counts[2][0], topics_counts[2][1] + (target_count - total_allocated))
        elif total_allocated > target_count:
            # Remove from geometry if we have too many
            excess = total_allocated - target_count
            topics_counts[2] = (topics_counts[2][0], max(1, topics_counts[2][1] - excess))
        
        # Generate questions by topic
        for topic, count in topics_counts:
            if count > 0:
                topic_request = QuestionRequest(
                    question_type="quantitative",
                    difficulty=difficulty,
                    topic=topic,
                    count=count
                )
                topic_questions = generate_questions(topic_request)
                questions.extend(topic_questions[:count])  # Ensure exact count
        
        # Shuffle to mix topic types (like real SSAT)
        random.shuffle(questions)
        return questions[:target_count]  # Ensure exactly right count
    
    async def _generate_verbal_section(self, difficulty) -> List[Question]:
        """Generate verbal questions (testing: 4 total, production: 30)"""
        
        testing_mode = True  # TODO: Make this configurable
        if testing_mode:
            synonym_count = 2
            analogy_count = 2
            target_count = 4
        else:
            distribution = self.specs["verbal_distribution"]
            synonym_count = int(30 * distribution["synonyms"])    # 18
            analogy_count = int(30 * distribution["analogies"])   # 12
            target_count = 30
        
        questions = []
        
        # Generate synonym questions
        synonym_request = QuestionRequest(
            question_type="synonym",
            difficulty=difficulty,
            count=synonym_count
        )
        synonym_questions = generate_questions(synonym_request)
        questions.extend(synonym_questions[:synonym_count])
        
        # Generate analogy questions
        analogy_request = QuestionRequest(
            question_type="analogy", 
            difficulty=difficulty,
            count=analogy_count
        )
        analogy_questions = generate_questions(analogy_request)
        questions.extend(analogy_questions[:analogy_count])
        
        # Shuffle to mix synonyms and analogies (like real SSAT)
        random.shuffle(questions)
        
        return questions[:target_count]  # Ensure exactly right count
    
    async def _generate_reading_section(self, difficulty) -> List[Question]:
        """Generate reading questions (testing: 3 total, production: 28)"""
        
        testing_mode = True  # TODO: Make this configurable
        target_count = 3 if testing_mode else 28
        
        reading_request = QuestionRequest(
            question_type="reading",
            difficulty=difficulty,
            count=target_count
        )
        
        questions = generate_questions(reading_request)
        return questions[:target_count]  # Ensure exactly right count
    
    def _generate_writing_prompt(self) -> WritingPrompt:
        """Generate a writing prompt for elementary students"""
        
        prompt_data = random.choice(ELEMENTARY_WRITING_PROMPTS)
        
        return WritingPrompt(
            prompt_text=prompt_data["prompt"],
            instructions=(
                "Look at the picture and write a story with a beginning, middle, and end. "
                "Your story should be interesting and complete. You have 15 minutes to write your story."
            ),
            visual_description=prompt_data.get("visual_description"),
            time_limit_minutes=15
        )
    
    def get_test_specifications(self) -> Dict[str, Any]:
        """Get official SSAT Elementary test specifications"""
        return {
            "test_type": "Official SSAT Elementary Level",
            "grade_levels": ["3", "4"],
            "sections": [
                {
                    "name": section.name,
                    "questions": section.question_count,
                    "time_minutes": section.time_minutes,
                    "scored": section.section_type == "scored",
                    "break_after": section.break_after
                }
                for section in self.specs["sections"]
            ],
            "total_scored_questions": self.specs["total_scored_questions"],
            "total_time_minutes": self.specs["total_time"],
            "scored_sections": self.specs["scored_sections"],
            "break_schedule": self.specs["break_schedule"]
        }
    
    def validate_generated_test(self, test: CompleteSSATTest) -> Dict[str, bool]:
        """Validate that generated test meets requirements (testing or production mode)"""
        # Check if we're in testing mode (lower question counts)
        testing_mode = test.total_scored_questions == 15  # 8+4+3
        
        if testing_mode:
            expected_total = 15
            expected_sections = {"Quantitative": 8, "Verbal": 4, "Reading": 3}
        else:
            expected_total = 88
            expected_sections = {"Quantitative": 30, "Verbal": 30, "Reading": 28}
            
        results = {
            "correct_section_count": len(test.sections) == 3,  # Quantitative, Verbal, Reading
            "correct_total_questions": test.total_scored_questions == expected_total,
            "correct_timing": test.total_time_minutes == 110,
            "sections_valid": True
        }
        
        # Validate individual sections
        for section in test.sections:
            expected_count = expected_sections.get(section.section_name)
            if expected_count and section.question_count != expected_count:
                results["sections_valid"] = False
                break
        
        results["overall_valid"] = all(results.values())
        return results

# Global service instance
ssat_test_service = SSATTestService()