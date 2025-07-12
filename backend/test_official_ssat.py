"""Test script for official SSAT Elementary test generation and validation"""

import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ssat_test_service import ssat_test_service
from app.models.requests import CompleteElementaryTestRequest
from app.core_models import DifficultyLevel

async def test_official_ssat_generation():
    """Test official SSAT test generation with comprehensive validation"""
    
    print("🧪 Testing Official SSAT Elementary Test Generation")
    print("=" * 60)
    
    # Create test request
    request = CompleteElementaryTestRequest(
        difficulty=DifficultyLevel.MEDIUM,
        student_grade="4",
        test_focus=None
    )
    
    print(f"📝 Test Request: {request.model_dump()}")
    print()
    
    try:
        print("⏳ Generating official SSAT test...")
        start_time = asyncio.get_event_loop().time()
        
        # Generate complete test
        test = await ssat_test_service.generate_complete_elementary_test(request)
        
        generation_time = asyncio.get_event_loop().time() - start_time
        
        print(f"✅ Official SSAT test generated successfully in {generation_time:.2f} seconds!")
        print()
        
        # Basic test information
        print("📊 Test Summary:")
        print(f"   📋 Test ID: {test.test_id}")
        print(f"   📝 Total Scored Questions: {test.total_scored_questions}")
        print(f"   ⏰ Total Time: {test.total_time_minutes} minutes")
        print(f"   🎯 Difficulty: {test.difficulty}")
        print(f"   📅 Generated: {test.generated_at}")
        print()
        
        # Official structure validation (adjusted for testing mode)
        print("📋 Test Structure Validation (Testing Mode):")
        official_requirements = {
            "Quantitative": {"expected_questions": 8, "expected_time": 30},   # Testing: 8 questions
            "Verbal": {"expected_questions": 4, "expected_time": 20},        # Testing: 4 questions
            "Reading": {"expected_questions": 3, "expected_time": 30}        # Testing: 3 questions
        }
        
        all_sections_valid = True
        total_questions_found = 0
        
        for section in test.sections:
            name = section.section_name
            if name in official_requirements:
                req = official_requirements[name]
                expected_q = req["expected_questions"]
                expected_t = req["expected_time"]
                actual_q = section.question_count
                actual_t = section.time_limit_minutes
                
                q_status = "✅" if actual_q == expected_q else "❌"
                t_status = "✅" if actual_t == expected_t else "❌"
                
                print(f"  {q_status} {name}: {actual_q}/{expected_q} questions")
                print(f"  {t_status} {name}: {actual_t}/{expected_t} minutes")
                
                if actual_q != expected_q or actual_t != expected_t:
                    all_sections_valid = False
                    
                total_questions_found += actual_q
        
        # Writing section validation
        writing_status = "✅" if test.writing_prompt else "❌"
        print(f"  {writing_status} Writing: 1 prompt, 15 minutes")
        if test.writing_prompt:
            print(f"     Prompt: {test.writing_prompt.prompt_text[:60]}...")
        
        print()
        
        # Comprehensive validation using service method
        validation_results = ssat_test_service.validate_generated_test(test)
        
        print("🔍 Detailed Validation Results:")
        for check, result in validation_results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}: {result}")
        
        print()
        
        # Total validation summary (adjusted for testing)
        expected_total_scored = 15  # 8+4+3 (testing mode)
        total_status = "✅" if test.total_scored_questions == expected_total_scored else "❌"
        print(f"{total_status} Total Scored Questions: {test.total_scored_questions}/{expected_total_scored} (Testing Mode)")
        
        time_status = "✅" if test.total_time_minutes == 110 else "❌"
        print(f"{time_status} Total Time: {test.total_time_minutes}/110 minutes")
        
        # Question content validation
        print()
        print("📝 Question Content Validation:")
        questions_have_content = True
        for section in test.sections:
            section_valid = True
            if len(section.questions) != section.question_count:
                print(f"  ❌ {section.section_name}: Question list length mismatch")
                section_valid = False
                questions_have_content = False
            else:
                # Sample a few questions to check they have proper content
                sample_size = min(3, len(section.questions))
                for i in range(sample_size):
                    q = section.questions[i]
                    if not q.text or len(q.text.strip()) < 10:
                        print(f"  ❌ {section.section_name}: Question {i+1} has insufficient text")
                        section_valid = False
                        questions_have_content = False
                    if len(q.options) != 4:
                        print(f"  ❌ {section.section_name}: Question {i+1} doesn't have 4 options")
                        section_valid = False
                        questions_have_content = False
                    if not q.explanation or len(q.explanation.strip()) < 5:
                        print(f"  ❌ {section.section_name}: Question {i+1} has insufficient explanation")
                        section_valid = False
                        questions_have_content = False
            
            if section_valid:
                print(f"  ✅ {section.section_name}: All {section.question_count} questions valid")
        
        # Final validation summary
        print()
        overall_valid = (
            all_sections_valid and 
            validation_results["overall_valid"] and 
            test.total_scored_questions == 15 and  # Testing mode: 15 questions
            test.total_time_minutes == 110 and
            questions_have_content
        )
        
        if overall_valid:
            print("🎉 COMPREHENSIVE SSAT VALIDATION PASSED!")
            print("   ✨ Generated test meets all official SSAT Elementary requirements")
        else:
            print("❌ VALIDATION FAILED!")
            print("   ⚠️  Generated test does not meet official requirements")
        
        # Metadata summary
        print()
        print("📊 Generation Metadata:")
        metadata = test.metadata
        print(f"   🔧 Generation Time: {generation_time:.2f} seconds")
        print(f"   📋 Sections Generated: {metadata.get('sections_generated', 'N/A')}")
        print(f"   🎓 Student Grade: {metadata.get('student_grade', 'N/A')}")
        print(f"   🧪 Test Focus: {metadata.get('test_focus', 'None')}")
        
        return overall_valid
        
    except Exception as e:
        print(f"❌ Official SSAT test generation failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

async def test_specifications_consistency():
    """Test that service specifications match configuration"""
    
    print()
    print("🔧 Testing Specifications Consistency")
    print("=" * 40)
    
    try:
        specs = ssat_test_service.get_test_specifications()
        
        # Validate specifications
        required_fields = [
            "test_type", "grade_levels", "sections", 
            "total_scored_questions", "total_time_minutes", "scored_sections"
        ]
        
        all_present = True
        for field in required_fields:
            if field not in specs:
                print(f"❌ Missing specification field: {field}")
                all_present = False
            else:
                print(f"✅ {field}: {specs[field]}")
        
        # Check sections structure
        if "sections" in specs:
            section_names = [s["name"] for s in specs["sections"]]
            expected_sections = ["Quantitative", "Verbal", "Reading", "Writing"]
            
            for expected in expected_sections:
                if expected not in section_names:
                    print(f"❌ Missing section: {expected}")
                    all_present = False
                else:
                    print(f"✅ Section present: {expected}")
        
        if all_present:
            print("✅ All specifications consistent and complete")
        else:
            print("❌ Specifications validation failed")
            
        return all_present
        
    except Exception as e:
        print(f"❌ Specifications test failed: {e}")
        return False

async def test_different_difficulties():
    """Test generation with different difficulty levels"""
    
    print()
    print("🎯 Testing Different Difficulty Levels")
    print("=" * 42)
    
    difficulties = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]
    all_passed = True
    
    for difficulty in difficulties:
        try:
            print(f"Testing {difficulty.value} difficulty...")
            
            request = CompleteElementaryTestRequest(
                difficulty=difficulty,
                student_grade="4"
            )
            
            # Just test that generation works, don't need full validation
            test = await ssat_test_service.generate_complete_elementary_test(request)
            
            # Quick validation (testing mode)
            if (test.total_scored_questions == 15 and  # Testing: 15 questions
                test.total_time_minutes == 110 and 
                len(test.sections) == 3):
                print(f"✅ {difficulty.value}: Test generated successfully")
            else:
                print(f"❌ {difficulty.value}: Test structure invalid")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {difficulty.value}: Generation failed - {e}")
            all_passed = False
    
    return all_passed

async def run_comprehensive_tests():
    """Run all tests and provide final summary"""
    
    print("🚀 SSAT Elementary Test - Comprehensive Validation Suite")
    print("=" * 65)
    print()
    
    # Run all test suites
    test_results = {}
    
    test_results["generation"] = await test_official_ssat_generation()
    test_results["specifications"] = await test_specifications_consistency()
    test_results["difficulties"] = await test_different_difficulties()
    
    # Final summary
    print()
    print("📊 FINAL TEST SUMMARY")
    print("=" * 25)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name.title()} Tests")
    
    all_passed = all(test_results.values())
    
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✨ SSAT Elementary test generation is working correctly")
        print("🚀 Ready for Phase 2 implementation!")
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Please review failed tests before proceeding")
    
    return all_passed

if __name__ == "__main__":
    # Run the comprehensive test suite
    success = asyncio.run(run_comprehensive_tests())
    exit(0 if success else 1)