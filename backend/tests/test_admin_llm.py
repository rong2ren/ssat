"""
Simple test for admin LLM generation functionality.

Tests only the core functionality: admin can generate questions using LLM.
"""

from typing import Dict
from fastapi.testclient import TestClient

from tests.helpers import TestAPIHelper, TestContentValidator, TestDataGenerator


def test_admin_generate_quantitative_questions(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can generate quantitative questions using LLM."""
    # Create simple request
    request_data = TestDataGenerator.create_question_request(
        question_type="quantitative",
        difficulty="Easy",
        count=2,
        topic="Number Sense"
    )
    
    # Make request to admin generation endpoint
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/generate",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=60
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["session_id", "generation_time_ms", "provider_used", "content"])
    
    # Verify we got the requested number of questions
    content = response_data["content"]
    TestAPIHelper.assert_has_fields(content, ["questions", "metadata"])
    assert len(content["questions"]) == 2
    
    # Verify each question has proper structure
    for question in content["questions"]:
        TestAPIHelper.assert_has_fields(question, [
            "text", "options", "correct_answer", "explanation"
        ])
        
        # Verify content quality (structure, not specific content)
        assert TestContentValidator.validate_content_quality(question["text"])
        assert len(question["options"]) == 4
        assert question["correct_answer"] in ["A", "B", "C", "D"]
        
        # Verify explanation exists
        assert TestContentValidator.validate_content_quality(question["explanation"])
    
    # Test passed - admin can successfully generate questions using LLM
    print(f"✅ Admin successfully generated {len(content['questions'])} questions")
    print(f"✅ Session ID: {response_data['session_id']}")
    print(f"✅ Generation time: {response_data['generation_time_ms']}ms")
    print(f"✅ Provider used: {response_data['provider_used']}")
    
    # Print the actual generated questions
    print("\n" + "="*80)
    print("🎯 ACTUALLY GENERATED QUESTIONS:")
    print("="*80)
    
    for i, question in enumerate(content['questions'], 1):
        print(f"\n📝 Question {i}:")
        print(f"   Text: {question['text']}")
        print(f"   Options:")
        for option in question['options']:
            print(f"     {option['letter']}. {option['text']}")
        print(f"   Correct Answer: {question['correct_answer']}")
        print(f"   Explanation: {question['explanation']}")
        if 'subsection' in question:
            print(f"   Subsection: {question['subsection']}")
        if 'tags' in question:
            print(f"   Tags: {', '.join(question['tags'])}")
        print("-" * 60)
    
    print("="*80)
    
    # Verify questions are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION:")
    print("="*80)
    
    # Query the database to verify questions were saved
    db_response = supabase_client.table("ai_generated_questions").select("*").eq("generation_session_id", response_data['session_id']).execute()
    
    if db_response.data:
        print(f"✅ Found {len(db_response.data)} questions in database for session {response_data['session_id']}")
        
        for i, db_question in enumerate(db_response.data, 1):
            print(f"\n📊 Database Question {i}:")
            print(f"   ID: {db_question.get('id', 'N/A')}")
            print(f"   Question: {db_question.get('question', 'N/A')}")
            print(f"   Choices: {db_question.get('choices', 'N/A')}")
            print(f"   Answer: {db_question.get('answer', 'N/A')}")
            print(f"   Explanation: {db_question.get('explanation', 'N/A')}")
            print(f"   Difficulty: {db_question.get('difficulty', 'N/A')}")
            print(f"   Section: {db_question.get('section', 'N/A')}")
            print(f"   Subsection: {db_question.get('subsection', 'N/A')}")
            print(f"   Tags: {db_question.get('tags', 'N/A')}")
            print(f"   Generation Session ID: {db_question.get('generation_session_id', 'N/A')}")
            print(f"   Created At: {db_question.get('created_at', 'N/A')}")
            print(f"   Updated At: {db_question.get('updated_at', 'N/A')}")
            
            # Verify all required fields are populated
            required_fields = ['question', 'choices', 'answer', 'explanation', 'difficulty', 'section', 'subsection', 'tags']
            missing_fields = [field for field in required_fields if not db_question.get(field)]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields populated")
            
            print("-" * 60)
    else:
        print(f"❌ No questions found in database for session {response_data['session_id']}")
    
    print("="*80)


def test_admin_save_training_examples_quantitative(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can save quantitative training examples."""
    # Create training examples request
    request_data = {
        "section_type": "quantitative",
        "examples_text": """Question: What is 15 + 27?
Choices: A) 40, B) 42, C) 41, D) 43
Correct Answer: B
Explanation: 15 + 27 = 42. This is basic addition.
Difficulty: Easy
Tags: basic-addition, arithmetic, number-sense

Question: If a rectangle has length 8 and width 6, what is its area?
Choices: A) 14, B) 48, C) 28, D) 24
Correct Answer: B
Explanation: Area = length × width = 8 × 6 = 48.
Difficulty: Medium
Tags: geometry, area, multiplication""",
        "input_format": "full"
    }
    
    # Make request to save training examples
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=30
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "quantitative"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] > 0
    
    print(f"✅ Admin successfully saved {response_data['saved_count']} quantitative training examples")
    print(f"✅ Total parsed: {response_data['total_parsed']}")
    
    # Verify examples are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION (QUANTITATIVE TRAINING):")
    print("="*80)
    
    # Query the ssat_questions table for recently saved examples
    db_response = supabase_client.table("ssat_questions").select("*").eq("source_file", "custom_training_examples").eq("section", "Quantitative").order("created_at", desc=True).limit(5).execute()
    
    if db_response.data:
        print(f"✅ Found {len(db_response.data)} recent quantitative training examples in database")
        
        for i, db_question in enumerate(db_response.data, 1):
            print(f"\n📊 Database Training Example {i}:")
            print(f"   ID: {db_question.get('id', 'N/A')}")
            print(f"   Question: {db_question.get('question', 'N/A')}")
            print(f"   Choices: {db_question.get('choices', 'N/A')}")
            print(f"   Answer: {db_question.get('answer', 'N/A')}")
            print(f"   Explanation: {db_question.get('explanation', 'N/A')}")
            print(f"   Difficulty: {db_question.get('difficulty', 'N/A')}")
            print(f"   Section: {db_question.get('section', 'N/A')}")
            print(f"   Subsection: {db_question.get('subsection', 'N/A')}")
            print(f"   Tags: {db_question.get('tags', 'N/A')}")
            print(f"   Source File: {db_question.get('source_file', 'N/A')}")
            print(f"   Created At: {db_question.get('created_at', 'N/A')}")
            
            # Verify all required fields are populated
            required_fields = ['question', 'choices', 'answer', 'explanation', 'difficulty', 'section', 'subsection', 'tags']
            missing_fields = [field for field in required_fields if not db_question.get(field)]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields populated")
            
            print("-" * 60)
    else:
        print(f"❌ No quantitative training examples found in database")
    
    print("="*80)


def test_admin_save_training_examples_synonym_simple(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can save synonym training examples using the special simple word list mode."""
    # Create training examples request with simple word list format
    request_data = {
        "section_type": "synonym",
        "examples_text": "happy, enormous, beautiful, quick, friendly",
        "input_format": "simple"  # This triggers the special LLM generation mode
    }
    
    # Make request to save training examples
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=60  # Longer timeout for LLM generation
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "synonym"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] == 5  # Should match the number of words we provided
    
    print(f"✅ Admin successfully saved {response_data['saved_count']} synonym training examples")
    print(f"✅ Total words parsed: {response_data['total_parsed']}")
    print(f"✅ Special simple mode: LLM generated questions from word list")
    
    # Verify examples are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION (SYNONYM TRAINING - SIMPLE MODE):")
    print("="*80)
    
    # Query the ssat_questions table for recently saved synonym examples
    db_response = supabase_client.table("ssat_questions").select("*").eq("source_file", "custom_training_examples").eq("section", "Verbal").eq("subsection", "Synonyms").order("created_at", desc=True).limit(5).execute()
    
    if db_response.data:
        print(f"✅ Found {len(db_response.data)} recent synonym training examples in database")
        
        for i, db_question in enumerate(db_response.data, 1):
            print(f"\n📊 Database Synonym Training Example {i}:")
            print(f"   ID: {db_question.get('id', 'N/A')}")
            print(f"   Question: {db_question.get('question', 'N/A')}")
            print(f"   Choices: {db_question.get('choices', 'N/A')}")
            print(f"   Answer: {db_question.get('answer', 'N/A')}")
            print(f"   Explanation: {db_question.get('explanation', 'N/A')}")
            print(f"   Difficulty: {db_question.get('difficulty', 'N/A')}")
            print(f"   Section: {db_question.get('section', 'N/A')}")
            print(f"   Subsection: {db_question.get('subsection', 'N/A')}")
            print(f"   Tags: {db_question.get('tags', 'N/A')}")
            print(f"   Source File: {db_question.get('source_file', 'N/A')}")
            print(f"   Created At: {db_question.get('created_at', 'N/A')}")
            
            # Verify all required fields are populated
            required_fields = ['question', 'choices', 'answer', 'explanation', 'difficulty', 'section', 'subsection', 'tags']
            missing_fields = [field for field in required_fields if not db_question.get(field)]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields populated")
            
            print("-" * 60)
    else:
        print(f"❌ No synonym training examples found in database")
    
    print("="*80)


def test_admin_save_training_examples_synonym_full(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can save synonym training examples using the full format."""
    # Create training examples request with full format
    request_data = {
        "section_type": "synonym",
        "examples_text": """Question: Which word means the same as "happy"?
Choices: A) sad, B) joyful, C) angry, D) tired
Correct Answer: B
Explanation: "Joyful" is a synonym for "happy" - both mean feeling pleasure or contentment.
Difficulty: Easy
Tags: basic-synonyms, emotion-words

Question: What is a synonym for "enormous"?
Choices: A) tiny, B) huge, C) small, D) medium
Correct Answer: B
Explanation: "Huge" is a synonym for "enormous" - both mean very large in size.
Difficulty: Medium
Tags: size-descriptors, vocabulary-building""",
        "input_format": "full"
    }
    
    # Make request to save training examples
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=30
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "synonym"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] > 0
    
    print(f"✅ Admin successfully saved {response_data['saved_count']} synonym training examples")
    print(f"✅ Total parsed: {response_data['total_parsed']}")
    print(f"✅ Full format: Direct parsing from structured text")
    
    # Verify examples are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION (SYNONYM TRAINING - FULL FORMAT):")
    print("="*80)
    
    # Query the ssat_questions table for recently saved synonym examples
    db_response = supabase_client.table("ssat_questions").select("*").eq("source_file", "custom_training_examples").eq("section", "Verbal").eq("subsection", "Synonyms").order("created_at", desc=True).limit(5).execute()
    
    if db_response.data:
        print(f"✅ Found {len(db_response.data)} recent synonym training examples in database")
        
        for i, db_question in enumerate(db_response.data, 1):
            print(f"\n📊 Database Synonym Training Example {i}:")
            print(f"   ID: {db_question.get('id', 'N/A')}")
            print(f"   Question: {db_question.get('question', 'N/A')}")
            print(f"   Choices: {db_question.get('choices', 'N/A')}")
            print(f"   Answer: {db_question.get('answer', 'N/A')}")
            print(f"   Explanation: {db_question.get('explanation', 'N/A')}")
            print(f"   Difficulty: {db_question.get('difficulty', 'N/A')}")
            print(f"   Section: {db_question.get('section', 'N/A')}")
            print(f"   Subsection: {db_question.get('subsection', 'N/A')}")
            print(f"   Tags: {db_question.get('tags', 'N/A')}")
            print(f"   Source File: {db_question.get('source_file', 'N/A')}")
            print(f"   Created At: {db_question.get('created_at', 'N/A')}")
            
            # Verify all required fields are populated
            required_fields = ['question', 'choices', 'answer', 'explanation', 'difficulty', 'section', 'subsection', 'tags']
            missing_fields = [field for field in required_fields if not db_question.get(field)]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields populated")
            
            print("-" * 60)
    else:
        print(f"❌ No synonym training examples found in database")
    
    print("="*80)


def test_admin_save_training_examples_reading(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can save reading training examples."""
    # Create training examples request
    request_data = {
        "section_type": "reading",
        "examples_text": """PASSAGE:
The ancient city of Rome was founded in 753 BCE and grew to become one of 
the most powerful empires in history. The Romans were known for their 
advanced engineering, including the construction of roads, aqueducts, and 
impressive buildings like the Colosseum. They also developed a sophisticated 
legal system that influenced modern law. The Roman Empire reached its peak 
around 117 CE, covering most of Europe, North Africa, and parts of Asia.

PASSAGE TYPE: History Non-Fiction
DIFFICULTY: Medium

QUESTION: When was Rome founded?
CHOICES: A) 753 BCE; B) 753 CE; C) 117 BCE; D) 117 CE
CORRECT ANSWER: A
EXPLANATION: The passage states that Rome was founded in 753 BCE.

QUESTION: What was one of the Romans' most notable achievements?
CHOICES: A) Writing poetry; B) Advanced engineering; C) Painting; D) Music
CORRECT ANSWER: B
EXPLANATION: The passage mentions that Romans were known for their advanced engineering.

QUESTION: What type of building is mentioned in the passage?
CHOICES: A) Library; B) Temple; C) Colosseum; D) Bridge
CORRECT ANSWER: C
EXPLANATION: The passage specifically mentions the Colosseum as an example of Roman engineering.

QUESTION: Around what year did the Roman Empire reach its peak?
CHOICES: A) 753 BCE; B) 753 CE; C) 117 BCE; D) 117 CE
CORRECT ANSWER: D
EXPLANATION: The passage states the empire reached its peak around 117 CE.""",
        "input_format": "full"
    }
    
    # Make request to save training examples
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=30
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "reading"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] > 0
    
    print(f"✅ Admin successfully saved {response_data['saved_count']} reading training examples")
    print(f"✅ Total parsed: {response_data['total_parsed']}")
    
    # Verify examples are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION (READING TRAINING):")
    print("="*80)
    
    # Query the reading_passages table for recently saved examples
    passages_response = supabase_client.table("reading_passages").select("*").eq("source_file", "custom_training_examples").order("created_at", desc=True).limit(3).execute()
    
    if passages_response.data:
        print(f"✅ Found {len(passages_response.data)} recent reading passages in database")
        
        for i, db_passage in enumerate(passages_response.data, 1):
            print(f"\n📊 Database Reading Passage {i}:")
            print(f"   ID: {db_passage.get('id', 'N/A')}")
            print(f"   Passage: {db_passage.get('passage', 'N/A')[:100]}...")
            print(f"   Passage Type: {db_passage.get('passage_type', 'N/A')}")
            print(f"   Difficulty: {db_passage.get('difficulty', 'N/A')}")
            print(f"   Source File: {db_passage.get('source_file', 'N/A')}")
            print(f"   Created At: {db_passage.get('created_at', 'N/A')}")
            
            # Query questions for this passage
            passage_id = db_passage.get('id')
            if passage_id:
                questions_response = supabase_client.table("reading_questions").select("*").eq("passage_id", passage_id).execute()
                if questions_response.data:
                    print(f"   📝 Questions: {len(questions_response.data)} questions found")
                    for j, db_question in enumerate(questions_response.data, 1):
                        print(f"      Question {j}: {db_question.get('question', 'N/A')}")
                        print(f"      Answer: {db_question.get('answer', 'N/A')}")
                        print(f"      Explanation: {db_question.get('explanation', 'N/A')}")
                else:
                    print(f"   ❌ No questions found for this passage")
            
            print("-" * 60)
    else:
        print(f"❌ No reading training examples found in database")
    
    print("="*80)


def test_admin_save_training_examples_writing(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can save writing training examples."""
    # Create training examples request
    request_data = {
        "section_type": "writing",
        "examples_text": """Prompt: Look at this picture of children building a treehouse. Write a story about their adventure.
Visual Description: Children working together with wood and tools to build a treehouse in a backyard
Image Path: writing_prompts/treehouse_children.jpeg
Tags: character-development, visual-inspiration, adventure-elements

Prompt: You find a magic key that can open any door. Write a story about where you go and what you discover.
Visual Description: An ornate, glowing key lying on a wooden table with mysterious symbols
Image Path: writing_prompts/magic_key.jpeg
Tags: imaginative-thinking, creative-problem-solving, discovery-learning""",
        "input_format": "full"
    }
    
    # Make request to save training examples
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=30
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "writing"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] > 0
    
    print(f"✅ Admin successfully saved {response_data['saved_count']} writing training examples")
    print(f"✅ Total parsed: {response_data['total_parsed']}")
    
    # Verify examples are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION (WRITING TRAINING):")
    print("="*80)
    
    # Query the writing_prompts table for recently saved examples
    db_response = supabase_client.table("writing_prompts").select("*").eq("source_file", "custom_training_examples").order("created_at", desc=True).limit(5).execute()
    
    if db_response.data:
        print(f"✅ Found {len(db_response.data)} recent writing prompts in database")
        
        for i, db_prompt in enumerate(db_response.data, 1):
            print(f"\n📊 Database Writing Prompt {i}:")
            print(f"   ID: {db_prompt.get('id', 'N/A')}")
            print(f"   Prompt: {db_prompt.get('prompt', 'N/A')}")
            print(f"   Visual Description: {db_prompt.get('visual_description', 'N/A')}")
            print(f"   Image Path: {db_prompt.get('image_path', 'N/A')}")
            print(f"   Grade Level: {db_prompt.get('grade_level', 'N/A')}")
            print(f"   Prompt Type: {db_prompt.get('prompt_type', 'N/A')}")
            print(f"   Subsection: {db_prompt.get('subsection', 'N/A')}")
            print(f"   Tags: {db_prompt.get('tags', 'N/A')}")
            print(f"   Source File: {db_prompt.get('source_file', 'N/A')}")
            print(f"   Created At: {db_prompt.get('created_at', 'N/A')}")
            
            # Verify all required fields are populated
            required_fields = ['prompt', 'visual_description', 'grade_level', 'prompt_type', 'subsection', 'tags']
            missing_fields = [field for field in required_fields if not db_prompt.get(field)]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields populated")
            
            print("-" * 60)
    else:
        print(f"❌ No writing training examples found in database")
    
    print("="*80)


def test_admin_save_training_examples_synonym_questions(
    test_client: TestClient,
    auth_headers_admin: Dict[str, str],
    supabase_client,
    skip_if_no_api_keys
):
    """Test admin can generate synonym questions using LLM from word list."""
    # Create training examples request with simple word list format
    request_data = {
        "section_type": "synonym",
        "examples_text": "happy, enormous, beautiful, quick, friendly",
        "input_format": "simple"  # This triggers the special LLM generation mode
    }
    
    # Make request to save training examples
    response = TestAPIHelper.make_api_request(
        test_client=test_client,
        method="POST",
        endpoint="/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=60  # Longer timeout for LLM generation
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "synonym"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] == 5  # Should match the number of words we provided
    
    print(f"✅ Admin successfully saved {response_data['saved_count']} synonym training examples")
    print(f"✅ Total words parsed: {response_data['total_parsed']}")
    print(f"✅ Special simple mode: LLM generated questions from word list")
    
    # Verify examples are saved in database
    print("\n" + "="*80)
    print("🗄️ DATABASE VERIFICATION (SYNONYM TRAINING - SIMPLE MODE):")
    print("="*80)
    
    # Query the ssat_questions table for recently saved synonym examples
    db_response = supabase_client.table("ssat_questions").select("*").eq("source_file", "custom_training_examples").eq("section", "Verbal").eq("subsection", "Synonyms").order("created_at", desc=True).limit(5).execute()
    
    if db_response.data:
        print(f"✅ Found {len(db_response.data)} recent synonym training examples in database")
        
        for i, db_question in enumerate(db_response.data, 1):
            print(f"\n📊 Database Synonym Training Example {i}:")
            print(f"   ID: {db_question.get('id', 'N/A')}")
            print(f"   Question: {db_question.get('question', 'N/A')}")
            print(f"   Choices: {db_question.get('choices', 'N/A')}")
            print(f"   Answer: {db_question.get('answer', 'N/A')}")
            print(f"   Explanation: {db_question.get('explanation', 'N/A')}")
            print(f"   Difficulty: {db_question.get('difficulty', 'N/A')}")
            print(f"   Section: {db_question.get('section', 'N/A')}")
            print(f"   Subsection: {db_question.get('subsection', 'N/A')}")
            print(f"   Tags: {db_question.get('tags', 'N/A')}")
            print(f"   Source File: {db_question.get('source_file', 'N/A')}")
            print(f"   Created At: {db_question.get('created_at', 'N/A')}")
            
            # Verify all required fields are populated
            required_fields = ['question', 'choices', 'answer', 'explanation', 'difficulty', 'section', 'subsection', 'tags']
            missing_fields = [field for field in required_fields if not db_question.get(field)]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields populated")
            
            print("-" * 60)
    else:
        print(f"❌ No synonym training examples found in database")
    
    print("="*80)


def test_admin_save_training_examples_questions_http(
    auth_headers_admin: Dict[str, str],
    skip_if_no_api_keys
):
    """Test admin can save training examples via actual HTTP requests."""
    # Create training examples request
    request_data = {
        "section_type": "synonym",
        "examples_text": "happy, enormous, beautiful, quick, friendly",
        "input_format": "simple"  # This triggers the special LLM generation mode
    }
    
    # Make actual HTTP request to save training examples
    # This will show up in your backend logs!
    response = TestAPIHelper.make_api_request(
        method="POST",
        url="http://localhost:8000/admin/save-training-examples",
        headers=auth_headers_admin,
        json_data=request_data,
        timeout=60
    )
    
    # Verify response is successful
    TestAPIHelper.assert_api_success(response, 200)
    
    # Parse response
    response_data = response.json()
    TestAPIHelper.assert_has_fields(response_data, ["saved_count", "total_parsed", "section_type"])
    
    # Verify we got the expected results
    assert response_data["section_type"] == "synonym"
    assert response_data["saved_count"] > 0
    assert response_data["total_parsed"] == 5  # Should match the number of words we provided
    
    print(f"✅ HTTP request test: Admin successfully saved {response_data['saved_count']} synonym training examples")
    print(f"✅ This request should appear in your backend logs!")
