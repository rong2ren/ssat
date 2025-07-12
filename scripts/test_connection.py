#!/usr/bin/env python3
"""Test database connection and show question statistics."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ssat.generator import SSATGenerator
from ssat.config import settings
from loguru import logger

def test_database_connection():
    """Test the database connection and show statistics."""
    print("=== SSAT Database Connection Test ===\n")
    
    # Check environment variables
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("❌ ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return False
    
    print("✓ Environment variables configured")
    
    try:
        # Initialize generator to test connection
        generator = SSATGenerator()
        
        # Test connection by getting stats from each table
        math_verbal_response = generator.supabase.table('ssat_questions').select('id', count='exact').execute()
        reading_passages_response = generator.supabase.table('reading_passages').select('id', count='exact').execute()
        reading_questions_response = generator.supabase.table('reading_questions').select('id', count='exact').execute()
        writing_prompts_response = generator.supabase.table('writing_prompts').select('id', count='exact').execute()
        
        stats = {
            'math_verbal_questions': math_verbal_response.count or 0,
            'reading_passages': reading_passages_response.count or 0,
            'reading_questions': reading_questions_response.count or 0,
            'writing_prompts': writing_prompts_response.count or 0
        }
        
        if stats:
            print("✓ Database connection successful!\n")
            print("=== Question Statistics ===")
            print(f"Math/Verbal questions: {stats.get('math_verbal_questions', 0)}")
            print(f"Reading passages: {stats.get('reading_passages', 0)}")
            print(f"Reading questions: {stats.get('reading_questions', 0)}")
            print(f"Writing prompts: {stats.get('writing_prompts', 0)}")
            
            total_questions = (
                stats.get('math_verbal_questions', 0) + 
                stats.get('reading_questions', 0) + 
                stats.get('writing_prompts', 0)
            )
            print(f"\nTotal questions available: {total_questions}")
            
            if total_questions > 0:
                print("\n✓ Questions available for AI training!")
                return True
            else:
                print("\n⚠️  No questions found. Run the upload script first:")
                print("   uv run python scripts/upload_data.py")
                return False
                
        else:
            print("❌ Failed to get database statistics")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_training_examples():
    """Test getting training examples."""
    print("\n=== Testing Training Examples ===")
    
    try:
        generator = SSATGenerator()
        
        # Test math examples using direct RPC calls
        math_response = generator.supabase.rpc('get_training_examples_by_section', {
            'section_filter': 'Quantitative',
            'difficulty_filter': 'Medium',
            'limit_count': 3
        }).execute()
        
        math_examples = math_response.data if math_response.data else []
        print(f"Math examples found: {len(math_examples)}")
        if math_examples:
            print(f"Sample math question: {math_examples[0]['question'][:100]}...")
        
        # Test verbal examples
        verbal_response = generator.supabase.rpc('get_training_examples_by_section', {
            'section_filter': 'Verbal',
            'difficulty_filter': 'Medium',
            'limit_count': 3
        }).execute()
        
        verbal_examples = verbal_response.data if verbal_response.data else []
        print(f"Verbal examples found: {len(verbal_examples)}")
        if verbal_examples:
            print(f"Sample verbal question: {verbal_examples[0]['question'][:100]}...")
        
        # Test reading examples
        reading_response = generator.supabase.rpc('get_reading_training_examples', {
            'limit_count': 1
        }).execute()
        
        reading_examples = reading_response.data if reading_response.data else []
        print(f"Reading examples found: {len(reading_examples)}")
        if reading_examples:
            print(f"Sample reading passage: {reading_examples[0]['passage'][:100]}...")
            print(f"Sample reading question: {reading_examples[0]['question'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get training examples: {e}")
        return False

def main():
    """Run all database tests."""
    success = True
    
    # Test basic connection
    if not test_database_connection():
        success = False
    
    # Test training examples if we have data
    if success:
        if not test_training_examples():
            success = False
    
    print(f"\n=== Test Results ===")
    if success:
        print("✓ All tests passed! Your database is ready for AI training.")
        print("\nNext steps:")
        print("1. Generate questions: uv run python src/main.py --type math --count 3")
        print("2. Questions will use real SSAT examples for training!")
    else:
        print("❌ Some tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure your .env file has SUPABASE_URL and SUPABASE_KEY")
        print("2. Run the schema: psql -f supabase_schema.sql")
        print("3. Upload questions: uv run python scripts/upload_data.py")

if __name__ == "__main__":
    main()