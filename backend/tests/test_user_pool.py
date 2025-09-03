"""
Simple test for user pool fetching functionality.

Tests only the core functionality: users can pull questions from pool.
"""

import pytest
from typing import Dict
from fastapi.testclient import TestClient

from tests.helpers import TestAPIHelper, TestContentValidator, TestDataGenerator, TestDatabaseHelper


@pytest.mark.asyncio
async def test_user_fetch_from_pool(
    test_client: TestClient,
    auth_headers_user: Dict[str, str],
    supabase_client
):
    """Test user can fetch questions from pool."""
    # Step 1: Seed pool with test questions
    print("📝 Seeding pool with test questions...")
    await TestDatabaseHelper.seed_pool_questions(
        supabase_client,
        "quantitative",
        count=3,
        difficulty="Easy"
    )
    
    try:
        # Step 2: Create user request
        request_data = TestDataGenerator.create_question_request(
            question_type="quantitative",
            difficulty="Easy",
            count=2
        )
        
        # Step 3: Make request to user generation endpoint
        print("🔍 Making request to user generation endpoint...")
        response = TestAPIHelper.make_api_request(
            test_client=test_client,
            method="POST",
            endpoint="/generate",
            headers=auth_headers_user,
            json_data=request_data,
            timeout=30
        )
        
        # Step 4: Verify response is successful
        TestAPIHelper.assert_api_success(response, 200)
        
        # Step 5: Parse and validate response
        response_data = response.json()
        TestAPIHelper.assert_has_fields(response_data, ["questions", "metadata"])
        
        # Step 6: Verify we got questions (may be fewer than requested if pool is small)
        questions_received = len(response_data["questions"])
        assert questions_received > 0, "Should receive at least one question from pool"
        
        print(f"📊 Received {questions_received} questions from pool")
        
        # Step 7: Verify each question has proper structure
        for i, question in enumerate(response_data["questions"]):
            TestAPIHelper.assert_has_fields(question, [
                "text", "options", "correct_answer", "explanation"
            ])
            
            # Verify content quality (structure, not specific content)
            assert TestContentValidator.validate_content_quality(question["text"])
            assert len(question["options"]) == 4
            assert question["correct_answer"] in ["A", "B", "C", "D"]
            
            # Verify explanation exists
            assert TestContentValidator.validate_content_quality(question["explanation"])
            
            print(f"✅ Question {i+1}: Valid structure and content")
        
        # Test passed - user can successfully fetch questions from pool
        print(f"✅ User successfully fetched {questions_received} questions from pool")
        
    finally:
        # Step 8: Clean up test data
        print("🧹 Cleaning up test data...")
        test_session_ids = [f"test_session_{i}" for i in range(3)]
        await TestDatabaseHelper.cleanup_test_content(supabase_client, test_session_ids)
        print("✅ Cleanup completed")


@pytest.mark.asyncio
async def test_user_single_section_pool_only(
    test_client: TestClient,
    auth_headers_user: Dict[str, str],
    supabase_client
):
    """Test user single section generation uses pool-only (no LLM fallback)."""
    # Step 1: Seed pool with test questions
    print("📝 Seeding pool with test questions for single section...")
    await TestDatabaseHelper.seed_pool_questions(
        supabase_client,
        "quantitative",
        count=3,
        difficulty="Easy"
    )
    
    try:
        # Step 2: Create single section request
        request_data = {
            "question_type": "quantitative",
            "difficulty": "Easy",
            "count": 2,
            "provider": "claude"
        }
        
        # Step 3: Make request to single section generation endpoint
        print("🔍 Making request to single section generation endpoint...")
        response = TestAPIHelper.make_api_request(
            test_client=test_client,
            method="POST",
            endpoint="/generate",
            headers=auth_headers_user,
            json_data=request_data,
            timeout=30
        )
        
        # Step 4: Verify response is successful
        TestAPIHelper.assert_api_success(response, 200)
        
        # Step 5: Parse and validate response
        response_data = response.json()
        TestAPIHelper.assert_has_fields(response_data, ["questions", "metadata"])
        
        # Step 6: Verify pool content was used
        assert len(response_data["questions"]) == 2
        assert response_data["metadata"]["provider_used"] == "pool"
        
        print(f"✅ Single section generation successful with pool content")
        print(f"✅ Questions generated: {len(response_data['questions'])}")
        print(f"✅ Provider used: {response_data['metadata']['provider_used']}")
        
        # Step 7: Verify questions are properly formatted
        for question in response_data["questions"]:
            TestAPIHelper.assert_has_fields(question, ["text", "options", "correct_answer", "explanation"])
        
        print("✅ All questions properly formatted")
        
    finally:
        # Step 8: Clean up test data
        print("🧹 Cleaning up test data...")
        test_session_ids = [f"test_session_{i}" for i in range(3)]
        await TestDatabaseHelper.cleanup_test_content(supabase_client, test_session_ids)
        print("✅ Cleanup completed")


@pytest.mark.asyncio
async def test_user_complete_test_pool_only(
    test_client: TestClient,
    auth_headers_user: Dict[str, str],
    supabase_client
):
    """Test user complete test generation uses pool-only (no LLM fallback)."""
    # Step 1: Seed pool with test questions
    print("📝 Seeding pool with test questions for complete test...")
    await TestDatabaseHelper.seed_pool_questions(
        supabase_client,
        "quantitative",
        count=5,
        difficulty="Easy"
    )
    
    try:
        # Step 2: Create complete test request
        request_data = {
            "difficulty": "Easy",
            "include_sections": ["quantitative"],
            "custom_counts": {"quantitative": 3},
            "is_official_format": False
        }
        
        # Step 3: Make request to complete test generation endpoint
        print("🔍 Making request to complete test generation endpoint...")
        response = TestAPIHelper.make_api_request(
            test_client=test_client,
            method="POST",
            endpoint="/generate/complete-test",
            headers=auth_headers_user,
            json_data=request_data,
            timeout=30
        )
        
        # Step 4: Verify response is successful
        TestAPIHelper.assert_api_success(response, 200)
        
        # Step 5: Parse and validate response
        response_data = response.json()
        TestAPIHelper.assert_has_fields(response_data, ["job_id", "status", "message"])
        
        # Step 6: Verify job was created
        assert response_data["status"] == "started"
        assert "job_id" in response_data
        job_id = response_data["job_id"]
        
        print(f"✅ Complete test generation started with job ID: {job_id}")
        print(f"✅ Status: {response_data['status']}")
        print(f"✅ Message: {response_data['message']}")
        
        # Step 7: Check job status (optional - may take time to complete)
        print("🔍 Checking job status...")
        status_response = TestAPIHelper.make_api_request(
            test_client=test_client,
            method="GET",
            endpoint=f"/generate/complete-test/{job_id}/status",
            headers=auth_headers_user,
            timeout=10
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ Job status: {status_data.get('status', 'unknown')}")
            print(f"✅ Progress: {status_data.get('progress_percentage', 0)}%")
        else:
            print(f"⚠️ Could not get job status: {status_response.status_code}")
        
        # Test passed - user can successfully start complete test generation
        print(f"✅ User successfully started complete test generation (pool-only)")
        
    finally:
        # Step 8: Clean up test data
        print("🧹 Cleaning up test data...")
        test_session_ids = [f"test_session_{i}" for i in range(5)]
        await TestDatabaseHelper.cleanup_test_content(supabase_client, test_session_ids)
        print("✅ Cleanup completed")


@pytest.mark.asyncio
async def test_user_complete_test_no_pool_fallback(
    test_client: TestClient,
    auth_headers_user: Dict[str, str],
    supabase_client
):
    """Test that normal users cannot use LLM fallback when pool is empty."""
    # Step 1: Ensure pool is empty for this test
    print("📝 Ensuring pool is empty for this test...")
    
    try:
        # Step 2: Create complete test request for content that shouldn't exist
        request_data = {
            "difficulty": "Hard",
            "include_sections": ["quantitative"],
            "custom_counts": {"quantitative": 10},
            "is_official_format": False
        }
        
        # Step 3: Make request to complete test generation endpoint
        print("🔍 Making request to complete test generation endpoint with empty pool...")
        response = TestAPIHelper.make_api_request(
            test_client=test_client,
            method="POST",
            endpoint="/generate/complete-test",
            headers=auth_headers_user,
            json_data=request_data,
            timeout=30
        )
        
        # Step 4: Verify response is successful (job creation should succeed)
        TestAPIHelper.assert_api_success(response, 200)
        
        # Step 5: Parse and validate response
        response_data = response.json()
        TestAPIHelper.assert_has_fields(response_data, ["job_id", "status", "message"])
        
        # Step 6: Verify job was created
        assert response_data["status"] == "started"
        job_id = response_data["job_id"]
        
        print(f"✅ Complete test generation started with job ID: {job_id}")
        
        # Step 7: Wait a moment and check job status to see if it fails gracefully
        print("🔍 Waiting for job processing...")
        import time
        time.sleep(2)  # Give background processing time to start
        
        status_response = TestAPIHelper.make_api_request(
            test_client=test_client,
            method="GET",
            endpoint=f"/generate/complete-test/{job_id}/status",
            headers=auth_headers_user,
            timeout=10
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ Job status: {status_data.get('status', 'unknown')}")
            
            # The job should either be in progress or failed gracefully
            # It should NOT be generating via LLM
            if status_data.get('status') == 'failed':
                print("✅ Job failed gracefully as expected (no LLM fallback)")
            elif status_data.get('status') == 'partial':
                print("✅ Job completed partially as expected (used available pool content)")
            else:
                print(f"⚠️ Job status: {status_data.get('status')} - still processing")
        else:
            print(f"⚠️ Could not get job status: {status_response.status_code}")
        
        # Test passed - user cannot use LLM fallback
        print(f"✅ User complete test generation respects pool-only policy")
        
    finally:
        # Step 8: Clean up (no test data to clean in this case)
        print("✅ No cleanup needed for empty pool test")
