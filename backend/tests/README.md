# SSAT Backend Test Suite

This directory contains comprehensive tests for the SSAT backend application. The test suite covers all major components including models, services, utilities, and integration points.

## 📁 Test Structure

```
tests/
├── __init__.py
├── README.md                           # This file
├── conftest.py                         # Pytest fixtures and configuration
├── helpers.py                          # Shared test utilities
├── test_models.py                      # Data models and validation tests
├── test_generator.py                   # SSAT Generator core logic tests
├── test_llm.py                         # LLM service and client tests
├── test_embedding_service.py           # Embedding service tests
├── test_utils.py                       # Utility functions tests
├── test_content_generation_service.py  # Content generation service tests
├── test_integration_admin_llm.py       # Admin LLM generation integration tests
├── test_integration_user_pool.py       # User pool fetching integration tests
├── test_integration_auth_roles.py      # Role-based access control integration tests
└── test_runner_comprehensive.py        # Comprehensive test runner
```

## 🚀 Quick Start

### Prerequisites

1. **Python Environment**: Ensure you're using Python 3.11+
2. **Package Manager**: Install UV package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Dependencies**: Install dependencies using UV
   ```bash
   cd backend
   uv sync
   ```

4. **Environment Variables**: Set up `.env` file with required variables
   ```bash
   # Required for all tests
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   
   # Required for integration tests (at least one)
   OPENAI_API_KEY=your_openai_key
   GEMINI_API_KEY=your_gemini_key  
   DEEPSEEK_API_KEY=your_deepseek_key
   ```

### Running Tests

#### 1. All Tests (Unit + Integration)

```bash
# Run all tests using UV
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=app
```

#### 2. Unit Tests Only (Fast, Mocked Dependencies)

```bash
# Run only unit tests (excludes integration tests)
uv run pytest tests/ -k "not integration"

# Run specific unit test files
uv run pytest tests/test_models.py -v
uv run pytest tests/test_generator.py -v
uv run pytest tests/test_llm.py -v
```

#### 3. Integration Tests Only (Real Services)

```bash
# Run only integration tests (requires .env with API keys)
uv run pytest tests/ -k "integration"

# Run specific integration test categories
uv run pytest tests/test_integration_admin_llm.py -v      # Admin LLM generation
uv run pytest tests/test_integration_user_pool.py -v     # User pool fetching
uv run pytest tests/test_integration_auth_roles.py -v    # Role-based access
```

#### 2. Comprehensive Test Runner (Advanced Features)

```bash
# Run all tests with advanced features
python tests/test_runner_comprehensive.py

# Run with verbose output
python tests/test_runner_comprehensive.py --verbose

# Run with coverage
python tests/test_runner_comprehensive.py --coverage

# Check dependencies only
python tests/test_runner_comprehensive.py --check-deps

# Check environment only
python tests/test_runner_comprehensive.py --check-env
```

#### 3. Individual Test Modules

```bash
# Run specific test modules
pytest tests/test_models.py -v
pytest tests/test_generator.py -v
pytest tests/test_llm.py -v
pytest tests/test_embedding_service.py -v
pytest tests/test_utils.py -v
pytest tests/test_content_generation_service.py -v

# Run specific test methods
pytest tests/test_models.py -v -k "test_question_validation"
pytest tests/test_generator.py -v -k "test_prompt_building"
```

## 📋 Test Coverage

### 1. Models (`test_models.py`)
- **Enums**: QuestionType, DifficultyLevel, LLMProvider
- **Data Models**: Option, Question, QuestionRequest, UserProfile
- **Request/Response Models**: API request and response models
- **Validation**: Pydantic validation rules and business logic
- **Serialization**: Model serialization and deserialization

### 2. Generator (`test_generator.py`)
- **SSATGenerator Class**: Core question generation logic
- **Prompt Building**: All prompt building methods
- **Training Examples**: Parsing and validation of training examples
- **LLM Provider Selection**: Provider selection logic
- **Reading Generation**: Mode selection for reading passages
- **Question Generation**: End-to-end question generation

### 3. LLM Service (`test_llm.py`)
- **LLMClient**: Multi-provider LLM client
- **Provider Integration**: OpenAI, Gemini, DeepSeek
- **Async Support**: Async LLM calls
- **Error Handling**: Network errors, API failures
- **Retry Logic**: Automatic retries and fallbacks
- **Edge Cases**: Special characters, unicode, long prompts

### 4. Embedding Service (`test_embedding_service.py`)
- **EmbeddingService**: Text embedding generation
- **Model Initialization**: Model loading and fallbacks
- **Thread Safety**: Concurrent embedding generation
- **Error Handling**: Network errors, model failures
- **Performance**: Speed and memory usage
- **Edge Cases**: Long text, special characters

### 5. Utilities (`test_utils.py`)
- **JSON Extraction**: Robust JSON parsing from text
- **JSON Validation**: Structure validation
- **Text Processing**: Text cleaning and normalization
- **Data Validation**: Question, passage, prompt validation
- **Error Handling**: Graceful error handling
- **Performance**: Large text processing

### 6. Content Generation Service (`test_content_generation_service.py`)
- **Service Integration**: End-to-end content generation
- **Database Connection**: Connection health checks
- **Topic Suggestions**: Dynamic topic generation
- **Section Generation**: Individual section generation
- **Complete Test Generation**: Full test generation
- **Async Operations**: Async test generation

### 7. Admin LLM Integration (`test_integration_admin_llm.py`)
- **Real LLM Generation**: Actual API calls to OpenAI/Gemini/DeepSeek
- **Admin Privileges**: Unlimited generation without daily limits
- **Content Quality**: Validation of generated content structure and quality
- **Provider Testing**: Tests for each LLM provider individually
- **Complete Test Generation**: Full 88-question test generation workflow
- **Database Persistence**: Verification that content saves correctly

### 8. User Pool Integration (`test_integration_user_pool.py`)
- **Pool Question Fetching**: Real database queries for unused questions
- **Usage Tracking**: Verification that questions are marked as used
- **Pool Exhaustion**: Testing fallback to LLM when pool is empty
- **Difficulty Filtering**: Pool questions filtered by difficulty level
- **Question Uniqueness**: Ensuring users get different questions
- **Daily Limit Enforcement**: Testing rate limiting for normal users

### 9. Role-Based Access Control (`test_integration_auth_roles.py`)
- **JWT Token Validation**: Real token verification with Supabase
- **Admin Access**: Verification that admin users can access admin endpoints
- **User Restrictions**: Normal users blocked from admin endpoints
- **Role-Based Limits**: Different daily limits per user role
- **Concurrent Access**: Multiple users accessing simultaneously
- **Token Edge Cases**: Expired, malformed, and missing token handling

## 🧪 Test Types

### Unit Tests (Mocked Dependencies)
- **Files**: `test_*.py` (excluding `test_integration_*.py`)
- **Purpose**: Individual function and method testing
- **Dependencies**: All external services mocked (LLM APIs, database, etc.)
- **Speed**: Fast execution (< 1 minute total)
- **Environment**: No API keys or database connection required
- **Examples**: Model validation, prompt building, JSON parsing

### Integration Tests (Real Services)
- **Files**: `test_integration_*.py`
- **Purpose**: End-to-end functionality with real services
- **Dependencies**: Actual LLM APIs, Supabase database, authentication
- **Speed**: Slower execution (several minutes depending on API response times)
- **Environment**: Requires `.env` file with valid API keys and database connection
- **Examples**: Real LLM generation, database queries, JWT token validation

### Async Tests
- **Purpose**: Asynchronous function testing
- **Features**: Concurrent operation testing, performance testing
- **Coverage**: Both unit and integration tests include async variants

### Edge Case Tests
- **Purpose**: Error conditions and boundary testing
- **Coverage**: Invalid input handling, special characters, unicode, network failures
- **Implementation**: Present in both unit and integration test categories

## 🔧 Test Configuration

### Pytest Configuration
Tests use pytest with the following configuration:
- `pytest-asyncio` for async test support
- Verbose output with `-v` flag
- Short traceback format with `--tb=short`
- Warning suppression with `--disable-warnings`

### Mocking Strategy
- **External Services**: All external API calls are mocked
- **Database**: Supabase operations are mocked
- **File System**: File operations are mocked where needed
- **Environment**: Environment variables are mocked for testing

### Test Data
- **Fixtures**: Reusable test data and objects
- **Factories**: Dynamic test data generation
- **Edge Cases**: Invalid data, boundary conditions
- **Real Examples**: Sample SSAT questions and passages

## 📊 Test Results

### Success Criteria
- **100% Pass Rate**: All tests should pass
- **Coverage**: Aim for >80% code coverage
- **Performance**: Tests should complete within reasonable time
- **No Warnings**: Clean test output without warnings

### Exit Codes
- **0**: All tests passed
- **1**: Some tests failed (warning)
- **2**: Many tests failed (error)
- **130**: Interrupted by user

## 🐛 Debugging Tests

### Common Issues

1. **Import Errors**
   ```bash
   # Check Python path
   python -c "import sys; print(sys.path)"
   
   # Run from correct directory
   cd backend
   python tests/test_runner_comprehensive.py
   ```

2. **Missing Dependencies**
   ```bash
   # Check dependencies
   python tests/test_runner_comprehensive.py --check-deps
   
   # Install missing packages
   pip install pytest pytest-asyncio loguru numpy
   ```

3. **Environment Issues**
   ```bash
   # Check environment
   python tests/test_runner_comprehensive.py --check-env
   
   # Set environment variables
   export SUPABASE_URL="your_url"
   export SUPABASE_KEY="your_key"
   ```

4. **Individual Module Testing**
   ```bash
   # Test specific module
   python tests/test_runner_comprehensive.py --individual
   
   # Run specific test file
   pytest tests/test_models.py -v -k "test_question_validation"
   ```

### Verbose Output
```bash
# Enable verbose output for debugging
python tests/test_runner_comprehensive.py --verbose

# Run pytest with verbose output
pytest tests/test_models.py -v -s
```

## 🔄 Continuous Integration

### GitHub Actions
The test suite is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    cd backend
    pytest tests/ -v --cov=app --cov-report=term-missing

# Or use comprehensive runner for advanced features
- name: Run Comprehensive Tests
  run: |
    cd backend
    python tests/test_runner_comprehensive.py --coverage
```

### Pre-commit Hooks
Consider adding pre-commit hooks to run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: backend-tests
        name: Backend Tests
        entry: pytest tests/ -v
        language: system
        files: ^backend/
```

## 📈 Coverage Reports

### Generate Coverage Report
```bash
# Run with coverage using pytest (recommended)
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Or use comprehensive runner for advanced coverage features
python tests/test_runner_comprehensive.py --coverage
```

### Coverage Targets
- **Models**: >95%
- **Services**: >90%
- **Utilities**: >95%
- **Overall**: >85%

## 🤝 Contributing

### Adding New Tests

1. **Follow Naming Convention**: `test_*.py` for test files
2. **Use Descriptive Names**: Clear test method names
3. **Include Documentation**: Docstrings for test classes and methods
4. **Mock External Dependencies**: Don't rely on external services
5. **Test Edge Cases**: Include error conditions and boundary cases

### Test Structure
```python
class TestNewFeature:
    """Test new feature functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Initialize test data and mocks
    
    def test_feature_success(self):
        """Test successful feature operation."""
        # Arrange
        # Act
        # Assert
    
    def test_feature_error_handling(self):
        """Test feature error handling."""
        # Test error conditions
```

### Running New Tests
```bash
# Add new test module to comprehensive runner
# Edit test_runner_comprehensive.py and add to test_modules list

# Run new tests
pytest tests/test_new_feature.py -v
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

## 🆘 Support

If you encounter issues with the test suite:

1. **Check the logs**: Look for detailed error messages
2. **Verify environment**: Ensure all dependencies are installed
3. **Run individual tests**: Isolate the failing test
4. **Check documentation**: Review this README and test docstrings
5. **Create an issue**: Report bugs with detailed information

---

**Note**: This test suite is designed to be comprehensive and maintainable. All tests should run independently and not rely on external services or databases.
