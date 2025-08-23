# SSAT Backend

FastAPI backend for the SSAT Question Generator. This Python-based API provides AI-powered question generation, user management, and test creation capabilities.

## 🚀 Quick Start

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env  # If .env.example exists
# Or create .env manually (see Environment Variables section)

# Start development server
uv run uvicorn app.main:app --reload --port 8000
```

Access the API at http://localhost:8000 and documentation at http://localhost:8000/docs

## 🏗️ Tech Stack

| Component           | Technology                              | Version  | Purpose                                 |
| ------------------- | --------------------------------------- | -------- | --------------------------------------- |
| **Framework**       | FastAPI                                 | Latest   | High-performance async web framework    |
| **Language**        | Python                                  | 3.11+    | Core backend language                   |
| **Package Manager** | UV                                      | Latest   | Fast Python package manager             |
| **Database**        | Supabase (PostgreSQL)                   | Latest   | Primary database with vector extensions |
| **Authentication**  | Supabase Auth                           | Latest   | JWT-based authentication                |
| **LLM Providers**   | OpenAI GPT-3.5, Google Gemini, DeepSeek | Latest   | AI question generation                  |
| **Embeddings**      | Sentence Transformers                   | 4.1.0    | Text embedding for semantic search      |
| **Validation**      | Pydantic                                | 2.0+     | Data validation and serialization       |
| **Logging**         | Loguru                                  | 0.7.3    | Structured logging                      |
| **HTTP Client**     | httpx                                   | Latest   | Async HTTP client for API calls         |
| **CORS**            | FastAPI CORS                            | Built-in | Cross-origin resource sharing           |

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application and routes
│   ├── config.py              # Configuration management
│   ├── dependencies.py        # Dependency injection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py        # Request models (Pydantic)
│   │   ├── responses.py       # Response models (Pydantic)
│   │   └── database.py        # Database models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── question_service.py    # Question generation logic
│   │   ├── llm_service.py         # LLM provider management
│   │   ├── auth_service.py        # Authentication logic
│   │   ├── embedding_service.py   # Text embedding generation
│   │   └── database_service.py    # Database operations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # Authentication endpoints
│   │   │   ├── generate.py        # Question generation endpoints
│   │   │   ├── user.py            # User management endpoints
│   │   │   └── admin.py           # Admin endpoints
│   │   └── dependencies.py        # API dependencies
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # Logging configuration
│       └── helpers.py            # Utility functions
├── core/
│   ├── __init__.py
│   ├── config.py               # Core configuration
│   ├── security.py             # Security utilities
│   └── database.py             # Database connection
├── scripts/                    # Utility scripts
├── tests/                      # Test files
├── .env                        # Environment variables
├── pyproject.toml             # Project configuration
├── uv.lock                    # Dependency lock file
└── README.md                  # This file
```

## ⚙️ Environment Variables

Create a `.env` file in the backend directory:

```env
# Supabase Configuration (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# AI API Keys (at least one required)
GEMINI_API_KEY=your_gemini_key          # Recommended (free tier)
DEEPSEEK_API_KEY=your_deepseek_key      # Affordable alternative
OPENAI_API_KEY=your_openai_key          # Premium option

# Optional Configuration
LOG_LEVEL=INFO                           # Logging level (DEBUG, INFO, WARNING, ERROR)
CORS_ORIGINS=http://localhost:3000       # Allowed CORS origins
PORT=8000                               # Server port
```

### Environment Variable Details

- **`SUPABASE_URL`**: Your Supabase project URL
  - Found in Supabase Dashboard → Settings → API

- **`SUPABASE_KEY`**: Your Supabase service role key
  - Found in Supabase Dashboard → Settings → API
  - **Keep this secret** - it has admin privileges

- **`GEMINI_API_KEY`**: Google Gemini API key
  - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
  - Free tier available

- **`DEEPSEEK_API_KEY`**: DeepSeek API key
  - Get from [DeepSeek Console](https://platform.deepseek.com/)
  - Affordable pricing

- **`OPENAI_API_KEY`**: OpenAI API key
  - Get from [OpenAI Platform](https://platform.openai.com/api-keys)
  - Premium option

## 🔧 Development

### Prerequisites
- Python 3.11+
- UV package manager
- Supabase project configured
- At least one AI API key

### Installation

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment (optional, UV handles this automatically)
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Development Server

```bash
# Start with auto-reload
uv run uvicorn app.main:app --reload --port 8000

# Start with custom host
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start with debug logging
uv run uvicorn app.main:app --reload --log-level debug
```

### Available Scripts

```bash
# Development
uv run uvicorn app.main:app --reload    # Start development server
uv run pytest                          # Run tests
uv run black .                         # Format code
uv run isort .                         # Sort imports
uv run mypy .                          # Type checking
uv run ruff check .                    # Lint code

# Database
uv run python scripts/upload_data.py   # Upload training data
uv run python scripts/test_connection.py # Test database connection
```

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Lint code
uv run ruff check .
uv run ruff check --fix .

# Type checking
uv run mypy .
```

## 📡 API Endpoints

### Core Endpoints

#### Question Generation
- `POST /generate` - Generate individual questions
- `POST /generate/complete-test/start` - Start progressive complete test generation
- `GET /generate/complete-test/{job_id}/status` - Get test generation progress
- `GET /generate/complete-test/{job_id}/result` - Get completed test

#### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/forgot-password` - Password reset
- `GET /auth/me` - Get current user

#### User Management
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update user profile
- `GET /user/limits` - Get user usage limits
- `GET /user/history` - Get generation history

#### System
- `GET /health` - API health check
- `GET /providers/status` - Check LLM provider availability
- `GET /topics/suggestions` - Get topic suggestions

### Example Requests

#### Generate Quantitative Questions
```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "question_type": "quantitative",
    "difficulty": "Medium",
    "topic": "fractions",
    "count": 5,
    "provider": "deepseek"
  }'
```

#### Start Complete Test Generation
```bash
curl -X POST "http://localhost:8000/generate/complete-test/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "difficulty": "Medium",
    "include_sections": ["quantitative", "analogy", "synonym", "reading"],
    "custom_counts": {
      "quantitative": 15,
      "analogy": 8,
      "synonym": 12,
      "reading": 5
    }
  }'
```

#### Check Generation Progress
```bash
curl -X GET "http://localhost:8000/generate/complete-test/{job_id}/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🔐 Authentication

The backend uses Supabase Auth with JWT tokens:

### Features
- JWT-based authentication
- Role-based access control
- User session management
- Password reset functionality
- Email confirmation

### Implementation
- **JWT Validation**: Automatic token validation on protected routes
- **User Context**: Current user available in request context
- **Role Checking**: Admin-only endpoints with role verification
- **Session Management**: Automatic token refresh handling

## 🗄️ Database Integration

### Supabase Features Used
- **PostgreSQL**: Primary database
- **pgvector**: Vector embeddings for semantic search
- **Row Level Security (RLS)**: Data access control
- **Real-time**: Live updates for progress tracking
- **Functions**: Complex queries and business logic

### Key Tables
- `users`: User profiles and authentication
- `questions`: Generated questions and metadata
- `embeddings`: Vector embeddings for similarity search
- `generation_jobs`: Background job tracking
- `user_limits`: Usage limits and quotas

## 🤖 AI Integration

### Supported LLM Providers

#### Google Gemini (Recommended)
- **Pros**: Free tier, good quality, fast
- **Cons**: Limited context window
- **Setup**: Get API key from Google AI Studio

#### DeepSeek
- **Pros**: Affordable, good quality, large context
- **Cons**: Newer provider
- **Setup**: Get API key from DeepSeek Console

#### OpenAI
- **Pros**: Best quality, reliable
- **Cons**: Expensive
- **Setup**: Get API key from OpenAI Platform

### Question Generation Process
1. **Input Validation**: Validate request parameters
2. **Provider Selection**: Choose best available LLM
3. **Prompt Construction**: Build context-aware prompts
4. **Generation**: Generate questions with explanations
5. **Validation**: Verify question quality and format
6. **Storage**: Save to database with embeddings
7. **Response**: Return structured response

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t ssat-backend .

# Run container
docker run -p 8000:8000 --env-file .env ssat-backend

# With Docker Compose
docker-compose up -d
```

### Railway Deployment
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Render Deployment
1. Connect GitHub repository to Render
2. Set build command: `uv sync && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables in Render dashboard

### AWS Lambda (Serverless)
```bash
# Build package
uv build

# Deploy with AWS SAM or Serverless Framework
```

### Environment Variables for Production

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key
LOG_LEVEL=WARNING
CORS_ORIGINS=https://your-frontend-domain.com
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_generation.py

# Run with verbose output
uv run pytest -v
```

### Test Structure
```
tests/
├── conftest.py              # Test configuration
├── test_api/                # API endpoint tests
├── test_services/           # Service layer tests
└── test_utils/              # Utility function tests
```

## 📊 Monitoring & Logging

### Logging Configuration
- **Structured Logging**: JSON format for production
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Request Logging**: All API requests logged
- **Error Tracking**: Detailed error information

### Health Checks
- **API Health**: `/health` endpoint
- **Database Health**: Connection status
- **LLM Health**: Provider availability
- **System Metrics**: Response times, error rates

## 🐛 Troubleshooting

### Common Issues

#### 1. "UV command not found"
```bash
# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart terminal
```

#### 2. "Supabase connection failed"
- Verify environment variables are correct
- Check Supabase project is active
- Ensure service role key has proper permissions

#### 3. "LLM provider errors"
- Verify API keys are valid
- Check API quotas and limits
- Ensure at least one provider is configured

#### 4. "Import errors"
```bash
# Reinstall dependencies
rm -rf .venv
uv sync
```

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG uv run uvicorn app.main:app --reload --log-level debug
```

### Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Check provider status
curl http://localhost:8000/providers/status
```

## 📚 API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Write tests for new features
4. Update documentation
5. Use conventional commit messages

## 📄 License

This project is licensed under the MIT License.

---

For frontend setup and integration, see the [frontend README](../frontend/README.md).