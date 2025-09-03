"""
Test configuration and fixtures for both unit and integration tests.

This file provides shared fixtures for:
- Database connections
- User authentication
- Test data setup/teardown
"""

import pytest
import pytest_asyncio
import asyncio
import os
from typing import Dict, Any
from uuid import uuid4
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Import the FastAPI app
try:
    from app.main import app
except ImportError:
    app = None

# Load environment variables from .env
load_dotenv()

# Test configuration
TEST_USER_EMAIL = "test_user@example.com"
TEST_ADMIN_EMAIL = "test_admin@example.com"
TEST_PASSWORD = "test_password_123"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """Get FastAPI test client for integration tests."""
    if app is None:
        pytest.skip("FastAPI app not available - cannot run integration tests")
    
    return TestClient(app)


@pytest.fixture(scope="session")
def supabase_client() -> Client:
    """Get Supabase client for integration tests."""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        pytest.skip("SUPABASE_URL or SUPABASE_KEY not set - skipping integration test")
    
    return create_client(supabase_url, supabase_key)


@pytest.fixture(scope="session")  
def admin_supabase_client() -> Client:
    """Get Supabase admin client for integration tests."""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Fixed: was SUPABASE_SERVICE_KEY
    
    if not supabase_url or not supabase_service_key:
        pytest.skip("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set - skipping admin integration test")
    
    return create_client(supabase_url, supabase_service_key)


@pytest_asyncio.fixture(scope="session")
async def test_user_token(supabase_client: Client) -> str:
    """Create and authenticate a test user, return JWT token."""
    try:
        # Try to sign up the test user (may already exist)
        try:
            auth_response = supabase_client.auth.sign_up({
                "email": TEST_USER_EMAIL,
                "password": TEST_PASSWORD,
                "options": {
                    "data": {
                        "full_name": "Test User",
                        "role": "free"
                    }
                }
            })
        except Exception:
            # User might already exist, that's fine
            pass
        
        # Sign in to get token
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": TEST_USER_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if auth_response.session and auth_response.session.access_token:
            return auth_response.session.access_token
        else:
            pytest.skip("Failed to authenticate test user")
            
    except Exception as e:
        pytest.skip(f"Failed to create/authenticate test user: {e}")


@pytest_asyncio.fixture(scope="session")
async def test_admin_token(admin_supabase_client: Client) -> str:
    """Create and authenticate a test admin user, return JWT token."""
    try:
        # Create admin user using admin client
        try:
            admin_response = admin_supabase_client.auth.admin.create_user({
                "email": TEST_ADMIN_EMAIL,
                "password": TEST_PASSWORD,
                "user_metadata": {
                    "full_name": "Test Admin",
                    "role": "admin"
                },
                "email_confirm": True  # Auto-confirm email
            })
        except Exception:
            # User might already exist, that's fine
            pass
        
        # Update user to ensure admin role
        users = admin_supabase_client.auth.admin.list_users()
        admin_user = next((u for u in users if u.email == TEST_ADMIN_EMAIL), None)
        
        if admin_user:
            admin_supabase_client.auth.admin.update_user_by_id(
                admin_user.id,
                {"user_metadata": {"full_name": "Test Admin", "role": "admin"}}
            )
        
        # Sign in with regular client to get token
        regular_client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        
        auth_response = regular_client.auth.sign_in_with_password({
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if auth_response.session and auth_response.session.access_token:
            return auth_response.session.access_token
        else:
            pytest.skip("Failed to authenticate test admin user")
            
    except Exception as e:
        pytest.skip(f"Failed to create/authenticate test admin user: {e}")


@pytest.fixture
def auth_headers_user(test_user_token: str) -> Dict[str, str]:
    """Get authorization headers for regular test user."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture  
def auth_headers_admin(test_admin_token: str) -> Dict[str, str]:
    """Get authorization headers for test admin user."""
    return {"Authorization": f"Bearer {test_admin_token}"}


@pytest.fixture
def api_keys_available() -> Dict[str, bool]:
    """Check which API keys are available for testing."""
    return {
        "openai": bool(os.getenv('OPENAI_API_KEY')),
        "gemini": bool(os.getenv('GEMINI_API_KEY')),
        "deepseek": bool(os.getenv('DEEPSEEK_API_KEY'))
    }


@pytest.fixture
def skip_if_no_api_keys(api_keys_available: Dict[str, bool]):
    """Skip test if no LLM API keys are available."""
    if not any(api_keys_available.values()):
        pytest.skip("No LLM API keys available - skipping LLM integration test")


@pytest.fixture
def skip_if_no_openai(api_keys_available: Dict[str, bool]):
    """Skip test if OpenAI API key not available."""
    if not api_keys_available["openai"]:
        pytest.skip("OPENAI_API_KEY not set - skipping OpenAI integration test")


@pytest.fixture
def skip_if_no_gemini(api_keys_available: Dict[str, bool]):
    """Skip test if Gemini API key not available."""
    if not api_keys_available["gemini"]:
        pytest.skip("GEMINI_API_KEY not set - skipping Gemini integration test")


@pytest.fixture
def skip_if_no_deepseek(api_keys_available: Dict[str, bool]):
    """Skip test if DeepSeek API key not available."""
    if not api_keys_available["deepseek"]:
        pytest.skip("DEEPSEEK_API_KEY not set - skipping DeepSeek integration test")


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(supabase_client: Client):
    """Cleanup test data after each test (runs automatically)."""
    yield  # Run the test
    
    # Cleanup after test
    try:
        # Clean up any test-specific data if needed
        # For now, we'll leave the test users as they can be reused
        pass
    except Exception as e:
        # Don't fail tests due to cleanup issues
        print(f"Warning: Test cleanup failed: {e}")


@pytest.fixture
def test_session_id() -> str:
    """Generate a unique session ID for test isolation."""
    return f"test_session_{uuid4()}"