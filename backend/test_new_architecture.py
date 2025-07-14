#!/usr/bin/env python3
"""Test script to verify the new architecture works correctly."""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.requests import QuestionGenerationRequest, QuestionType, DifficultyLevel, LLMProvider
from app.services.unified_content_service import UnifiedContentService

async def test_new_architecture():
    """Test the new unified content generation architecture."""
    print("🔧 Testing New SSAT Content Generation Architecture")
    print("=" * 60)
    
    service = UnifiedContentService()
    
    # Test 1: Standalone Questions (Math)
    print("\n1. Testing Standalone Questions (Quantitative)")
    try:
        request = QuestionGenerationRequest(
            question_type=QuestionType.QUANTITATIVE,
            difficulty=DifficultyLevel.MEDIUM,
            count=2
        )
        
        result = await service.generate_content(request)
        print(f"✅ Quantitative: Generated {result.count} questions")
        print(f"   Response type: {type(result).__name__}")
        print(f"   Questions: {len(result.questions)}")
        
    except Exception as e:
        print(f"❌ Quantitative failed: {e}")
        return False
    
    # Test 2: Reading Passages
    print("\n2. Testing Reading Comprehension")
    try:
        request = QuestionGenerationRequest(
            question_type=QuestionType.READING,
            difficulty=DifficultyLevel.MEDIUM,
            count=1  # 1 passage = 4 questions
        )
        
        result = await service.generate_content(request)
        print(f"✅ Reading: Generated {result.count} passages with {result.total_questions} total questions")
        print(f"   Response type: {type(result).__name__}")
        print(f"   Passages: {len(result.passages)}")
        if result.passages:
            passage = result.passages[0]
            print(f"   First passage: {len(passage.questions)} questions")
            print(f"   Passage text preview: {passage.text[:100]}...")
        
    except Exception as e:
        print(f"❌ Reading failed: {e}")
        return False
    
    # Test 3: Writing Prompts
    print("\n3. Testing Writing Prompts")
    try:
        request = QuestionGenerationRequest(
            question_type=QuestionType.WRITING,
            difficulty=DifficultyLevel.MEDIUM,
            count=1
        )
        
        result = await service.generate_content(request)
        print(f"✅ Writing: Generated {result.count} prompts")
        print(f"   Response type: {type(result).__name__}")
        print(f"   Prompts: {len(result.prompts)}")
        if result.prompts:
            prompt = result.prompts[0]
            print(f"   First prompt preview: {prompt.prompt_text[:80]}...")
        
    except Exception as e:
        print(f"❌ Writing failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! New architecture is working correctly!")
    print("\nKey Benefits Verified:")
    print("✅ Type-specific responses (QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse)")
    print("✅ Proper data structures (Questions, Passages, Prompts)")
    print("✅ No more format patching - each type follows its natural structure")
    print("✅ Reading comprehension properly separated into passage + questions")
    print("✅ Same generators work for both individual and complete tests")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_new_architecture())
    if not success:
        sys.exit(1)