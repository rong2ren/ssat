"""
Shared test utilities for both unit and integration tests.

Provides common functions for:
- Authentication helpers
- Database operations
- Content validation
- API response assertions
"""

from typing import Dict, Any, List, Optional, Union
from supabase import Client
from fastapi.testclient import TestClient
from fastapi import Response
import httpx

from app.models.responses import QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse


class TestAuthHelper:
    """Helper class for authentication in tests."""
    
    @staticmethod
    def create_auth_headers(token: str) -> Dict[str, str]:
        """Create authorization headers from JWT token."""
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    async def get_user_from_token(supabase_client: Client, token: str) -> Optional[Dict[str, Any]]:
        """Extract user data from JWT token."""
        try:
            user_response = supabase_client.auth.get_user(token)
            if user_response and user_response.user:
                return user_response.user.__dict__
            return None
        except Exception:
            return None


class TestDatabaseHelper:
    """Helper class for database operations in tests."""
    
    @staticmethod
    async def seed_pool_questions(
        supabase_client: Client, 
        question_type: str,
        count: int = 5,
        difficulty: str = "Easy"
    ) -> List[str]:
        """Seed test questions in the pool and return their IDs."""
        questions = []
        
        for i in range(count):
            question_data = {
                "question": f"Test {question_type} question {i + 1}?",
                "choices": [f"Option {j}" for j in ["A", "B", "C", "D"]],
                "answer": 0,  # A
                "explanation": f"This is explanation for question {i + 1}",
                "difficulty": difficulty,
                "section": question_type.title(),
                "subsection": f"Test {question_type}",
                "tags": ["test", question_type.lower()],
                "generation_session_id": f"test_session_{i}"
            }
            
            # Insert into appropriate table based on question type
            if question_type.lower() == "quantitative":
                response = supabase_client.table("ai_generated_questions").insert(question_data).execute()
            else:
                response = supabase_client.table("ai_generated_questions").insert(question_data).execute()
            
            if response.data:
                questions.append(response.data[0]["id"])
        
        return questions
    
    @staticmethod
    async def seed_reading_pool(
        supabase_client: Client,
        count: int = 2
    ) -> List[str]:
        """Seed test reading passages in the pool and return their IDs."""
        passage_ids = []
        
        for i in range(count):
            # Create passage
            passage_data = {
                "passage": f"This is test reading passage {i + 1}. It contains educational content about various topics to help students practice reading comprehension skills.",
                "passage_type": "fiction" if i % 2 == 0 else "non_fiction",
                "generation_session_id": f"test_reading_session_{i}"
            }
            
            passage_response = supabase_client.table("ai_generated_reading_passages").insert(passage_data).execute()
            
            if passage_response.data:
                passage_id = passage_response.data[0]["id"]
                passage_ids.append(passage_id)
                
                # Create questions for this passage
                for j in range(2):  # 2 questions per passage
                    question_data = {
                        "passage_id": passage_id,
                        "question": f"Question {j + 1} for passage {i + 1}?",
                        "choices": [f"Answer {k}" for k in ["A", "B", "C", "D"]],
                        "answer": j % 4,  # Cycle through A, B, C, D
                        "explanation": f"Explanation for question {j + 1}",
                        "difficulty": "Easy"
                    }
                    
                    supabase_client.table("ai_generated_reading_questions").insert(question_data).execute()
        
        return passage_ids
    
    @staticmethod
    async def seed_writing_pool(
        supabase_client: Client,
        count: int = 3
    ) -> List[str]:
        """Seed test writing prompts in the pool and return their IDs."""
        prompt_ids = []
        
        for i in range(count):
            prompt_data = {
                "prompt": f"Test writing prompt {i + 1}: Write a creative story about adventure.",
                "visual_description": f"A picture showing an exciting adventure scene {i + 1}",
                "grade_level": "4-5",
                "prompt_type": "picture_story",
                "subsection": "Creative Writing",
                "tags": ["test", "creative", "adventure"],
                "generation_session_id": f"test_writing_session_{i}"
            }
            
            response = supabase_client.table("ai_generated_writing_prompts").insert(prompt_data).execute()
            
            if response.data:
                prompt_ids.append(response.data[0]["id"])
        
        return prompt_ids
    
    @staticmethod
    async def cleanup_test_content(supabase_client: Client, session_ids: List[str]):
        """Clean up test content by session IDs."""
        try:
            # Clean up questions
            supabase_client.table("ai_generated_questions").delete().in_("generation_session_id", session_ids).execute()
            
            # Clean up reading content
            supabase_client.table("ai_generated_reading_questions").delete().in_("passage_id", 
                supabase_client.table("ai_generated_reading_passages").select("id").in_("generation_session_id", session_ids).execute().data
            ).execute()
            supabase_client.table("ai_generated_reading_passages").delete().in_("generation_session_id", session_ids).execute()
            
            # Clean up writing prompts
            supabase_client.table("ai_generated_writing_prompts").delete().in_("generation_session_id", session_ids).execute()
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")


class TestContentValidator:
    """Helper class for validating generated content."""
    
    @staticmethod
    def validate_question_response(response: QuestionGenerationResponse) -> bool:
        """Validate a question generation response structure."""
        if not response or not response.questions:
            return False
        
        for question in response.questions:
            # Check required fields
            if not all([
                question.text,
                question.options,
                question.correct_answer,
                question.explanation
            ]):
                return False
            
            # Check options structure
            if len(question.options) != 4:
                return False
            
            # Check correct answer format
            if question.correct_answer not in ["A", "B", "C", "D"]:
                return False
        
        return True
    
    @staticmethod
    def validate_reading_response(response: ReadingGenerationResponse) -> bool:
        """Validate a reading generation response structure."""
        if not response or not response.passages:
            return False
        
        for passage in response.passages:
            # Check required fields
            if not all([
                passage.text,
                passage.questions
            ]):
                return False
            
            # Check questions structure
            for question in passage.questions:
                if not all([
                    question.text,
                    question.options,
                    question.correct_answer,
                    question.explanation
                ]):
                    return False
        
        return True
    
    @staticmethod
    def validate_writing_response(response: WritingGenerationResponse) -> bool:
        """Validate a writing generation response structure."""
        if not response or not response.prompts:
            return False
        
        for prompt in response.prompts:
            # Check required fields
            if not prompt.prompt_text:
                return False
        
        return True
    
    @staticmethod
    def validate_content_quality(content: str) -> bool:
        """Basic content quality validation."""
        if not content or len(content.strip()) < 10:
            return False
        
        # Check for obvious AI artifacts or errors
        error_indicators = [
            "I cannot",
            "I'm not able to",
            "As an AI",
            "[ERROR]",
            "undefined"
        ]
        
        for indicator in error_indicators:
            if indicator.lower() in content.lower():
                return False
        
        return True


class TestAPIHelper:
    """Helper class for API testing."""
    
    @staticmethod
    def make_api_request(
        test_client: Optional[TestClient] = None,
        method: str = "GET",
        endpoint: Optional[str] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Union[Response, httpx.Response]:
        """Make an API request using either FastAPI TestClient or direct HTTP request."""
        # Handle both endpoint (for TestClient) and url (for direct HTTP) parameters
        if endpoint and url:
            raise ValueError("Cannot specify both endpoint and url")
        
        if not endpoint and not url:
            raise ValueError("Must specify either endpoint or url")
        
        # If using TestClient (preferred for integration tests)
        if test_client and endpoint:
            # Remove the base URL since TestClient handles it
            if endpoint.startswith("http://"):
                # Extract just the path from full URL
                endpoint = "/" + endpoint.split("/", 3)[-1]
            
            if method.upper() == "GET":
                return test_client.get(endpoint, headers=headers)
            elif method.upper() == "POST":
                return test_client.post(endpoint, headers=headers, json=json_data)
            elif method.upper() == "PUT":
                return test_client.put(endpoint, headers=headers, json=json_data)
            elif method.upper() == "DELETE":
                return test_client.delete(endpoint, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        # If using direct HTTP requests (fallback)
        elif url:
            import httpx
            with httpx.Client(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = client.post(url, headers=headers, json=json_data)
                elif method.upper() == "PUT":
                    response = client.put(url, headers=headers, json=json_data)
                elif method.upper() == "DELETE":
                    response = client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Convert httpx.Response to a compatible format
                from fastapi.responses import Response as FastAPIResponse
                return FastAPIResponse(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
        
        else:
            raise ValueError("Must provide either test_client with endpoint or url for direct HTTP request")
    
    @staticmethod
    def assert_api_success(response: Union[Response, httpx.Response], expected_status: int = 200):
        """Assert API response is successful."""
        response_text = response.text if hasattr(response, 'text') else str(response.content)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response_text}"
    
    @staticmethod
    def assert_api_error(response: Union[Response, httpx.Response], expected_status: int):
        """Assert API response has expected error status."""
        response_text = response.text if hasattr(response, 'text') else str(response.content)
        assert response.status_code == expected_status, f"Expected error {expected_status}, got {response.status_code}: {response_text}"
    
    @staticmethod
    def assert_has_fields(data: Dict[str, Any], required_fields: List[str]):
        """Assert response data has required fields."""
        missing_fields = [field for field in required_fields if field not in data]
        assert not missing_fields, f"Missing required fields: {missing_fields}"


class TestDataGenerator:
    """Helper class for generating test data."""
    
    @staticmethod
    def create_question_request(
        question_type: str = "quantitative",
        difficulty: str = "Easy", 
        count: int = 2,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a question generation request payload."""
        return {
            "question_type": question_type,
            "difficulty": difficulty,
            "count": count,
            "topic": topic or f"Test {question_type.title()}",
            "use_custom_examples": False
        }
    
    @staticmethod
    def create_complete_test_request(
        difficulty: str = "Easy",
        include_sections: Optional[List[str]] = None,
        is_official_format: bool = False
    ) -> Dict[str, Any]:
        """Create a complete test generation request payload."""
        return {
            "difficulty": difficulty,
            "include_sections": include_sections or ["quantitative", "reading", "writing"],
            "is_official_format": is_official_format,
            "custom_counts": {
                "quantitative": 5,
                "reading": 2,
                "writing": 1
            } if not is_official_format else None
        }