# SSAT Question Generator - FastAPI Backend

This is the FastAPI backend for the SSAT Question Generator web application.

## Features

- **Individual Question Generation**: Generate specific types of SSAT questions
- **Complete Test Generation**: Create full SSAT practice tests with all sections
- **Multiple LLM Providers**: Support for OpenAI, Gemini, and DeepSeek
- **Real SSAT Training**: Uses authentic SSAT questions for training examples
- **Export-Ready Format**: Structured output perfect for printing/PDF generation

## API Endpoints

### Core Endpoints

- `POST /generate` - Generate individual questions
- `POST /generate/complete-test/start` - Start progressive complete test generation
- `GET /generate/complete-test/{jobId}/status` - Get test generation progress
- `GET /providers/status` - Check LLM provider availability
- `GET /health` - API health check
- `GET /topics/suggestions?question_type=quantitative` - Get topic suggestions

### Example Requests

#### Generate Quantitative Questions
```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "question_type": "quantitative",
    "difficulty": "Medium", 
    "topic": "fractions",
    "count": 5,
    "provider": "deepseek"
  }'
```

#### Start Progressive Complete Test
```bash
# Start test generation
curl -X POST "http://localhost:8000/generate/complete-test/start" \
  -H "Content-Type: application/json" \
  -d '{
    "difficulty": "Medium",
    "include_sections": ["quantitative", "analogy", "synonym", "reading"],
    "custom_counts": {"quantitative": 15, "analogy": 8, "synonym": 12, "reading": 5}
  }'

# Poll for progress (replace {job_id} with returned job ID)
curl -X GET "http://localhost:8000/generate/complete-test/{job_id}/status"
```

## Setup & Development

### Prerequisites
- Python 3.8+
- Environment variables configured (see main project .env)

### Installation
```bash
# Install dependencies (creates .venv automatically)
uv sync
```

### Development Server
```bash
# Run with auto-reload
uv run uvicorn app.main:app --reload --port 8000

# Or on different port
uv run uvicorn app.main:app --reload --port 8001
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── models/
│   │   ├── requests.py      # Request models
│   │   └── responses.py     # Response models
│   └── services/
│       ├── question_service.py  # Question generation logic
│       └── llm_service.py       # LLM provider management
└── README.md
```

## Deployment Options

### Option 1: Vercel Serverless Functions
- Fast deployment
- Auto-scaling
- 10-second execution limit

### Option 2: Railway/Render
- No execution time limits
- Always-on service
- Better for heavy LLM processing

## Environment Variables

Uses the same `.env` file as the main project:

```bash
# Required
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# At least one LLM provider
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key
```

## Response Format

All responses include:
- Generated questions with detailed explanations
- Metadata (generation time, provider used, etc.)
- Status information
- Export-friendly structure

Perfect for frontend integration and PDF generation!