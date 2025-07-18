# SSAT Question Generator

An AI-powered SSAT question generator for elementary level students. This monorepo contains independent frontend, backend, and utility projects.

## 📋 Table of Contents

- [🏗️ Project Structure](#️-project-structure)
- [🚀 Quick Start](#-quick-start)
- [🔧 Technology Stack](#-technology-stack)
- [📦 Key Features](#-key-features)
- [🏛️ Architecture](#️-architecture)
- [🗃️ Database Setup](#️-database-setup)
- [🔑 Environment Variables](#-environment-variables)
- [🎯 Development Workflow](#-development-workflow)
- [🏭 Production Deployment](#-production-deployment)

## 🏗️ Project Structure

```
ssat/
├── backend/          # Python FastAPI backend (UV)
├── frontend/         # React/Next.js frontend (npm)  
├── scripts/          # DevOps utilities (pip)
├── data/             # Training data and examples
├── sql/              # Database schema
└── docs/             # Documentation
```

## 🚀 Quick Start

Each project uses its optimal tooling:

### Backend (Python + UV)
```bash
cd backend
uv sync                # Install dependencies
uv run uvicorn app.main:app --reload  # Start API server
```

### Frontend (Node.js + npm)
```bash
cd frontend
npm install            # Install dependencies
npm run dev            # Start development server
```

### Scripts (Python + pip)
```bash
cd scripts
pip install -r requirements.txt  # Install dependencies
python upload_data.py            # Upload training data
```

## 🔧 Technology Stack

| Project | Language | Package Manager | Framework |
|---------|----------|----------------|-----------|
| **Backend** | Python 3.11+ | UV | FastAPI |
| **Frontend** | TypeScript | npm | Next.js 15 |
| **Scripts** | Python 3.11+ | pip | - |

## 📦 Key Features

- **AI Question Generation** - Multiple LLM providers (OpenAI, Gemini, DeepSeek)
- **Real SSAT Training** - Uses actual SSAT questions for few-shot learning
- **Complete Test Generation** - Official SSAT Elementary format (88 questions)
- **Modern Frontend** - React 19, TypeScript, Tailwind CSS
- **Training Data Pipeline** - PDF extraction, embedding generation, database upload

## 🏛️ Architecture

### Content Generation Modes

The system supports **3 generation modes**:

1. **📝 Individual Question Generation** - Generate 1-20 questions of specific types
2. **⚡ Progressive Test Generation** - Complete tests with real-time progress tracking  
3. **🎯 Practice Sessions** - Focused practice on specific question types

### Educational Section Structure

Clean, educationally-aligned sections that match SSAT content areas:

```python
# Mathematics section
class QuantitativeSection:
    section_type: Literal[QuestionType.QUANTITATIVE]
    questions: List[GeneratedQuestion]  # Arithmetic, fractions, geometry

# Vocabulary section  
class SynonymSection:
    section_type: Literal[QuestionType.SYNONYM]
    questions: List[GeneratedQuestion]  # Word meaning questions

# Word relationship section
class AnalogySection:
    section_type: Literal[QuestionType.ANALOGY] 
    questions: List[GeneratedQuestion]  # "cat is to meow as dog is to ___"

# Reading comprehension section
class ReadingSection:
    section_type: Literal[QuestionType.READING]
    passages: List[ReadingPassage]      # Each passage has ~4 questions

# Creative writing section
class WritingSection:
    section_type: Literal[QuestionType.WRITING]
    prompt: WritingPrompt               # Creative writing tasks
```

### API Architecture

**Type-Specific Responses:**
```python
# Individual questions (math, vocabulary, word relationships)
QuestionGenerationResponse: { questions: List[GeneratedQuestion] }

# Reading comprehension (passages with questions)  
ReadingGenerationResponse: { passages: List[ReadingPassage] }

# Writing prompts (creative writing tasks)
WritingGenerationResponse: { prompts: List[WritingPrompt] }
```

### Training Data Alignment

Maps to actual SSAT database structure:
```python
"quantitative": ("Quantitative", None)        # Pure math section
"synonym": ("Verbal", "Synonyms")            # Verbal → Synonyms subsection  
"analogy": ("Verbal", "Analogies")           # Verbal → Analogies subsection
"reading": ("Reading", None)                 # Reading comprehension
"writing": ("Writing", None)                 # Writing prompts
```

### API Usage Examples

```bash
# Generate math questions
POST /generate {"question_type": "quantitative", "count": 10}
→ Returns QuantitativeSection with 10 math questions

# Generate vocabulary questions  
POST /generate {"question_type": "synonym", "count": 8}
→ Returns SynonymSection with 8 vocabulary questions

# Start complete test generation
POST /generate/complete-test/start {
  "include_sections": ["quantitative", "synonym", "analogy", "reading"],
  "custom_counts": {"quantitative": 15, "synonym": 12}
}
→ Returns job_id for progress polling

# Check test generation progress  
GET /generate/complete-test/{job_id}/status
→ Returns progress and completed sections
```

## 🗃️ Database Setup

1. **Setup Supabase** (see `docs/SUPABASE_SETUP.md`)
2. **Run schema**: Execute `sql/schema.sql` in Supabase SQL editor
3. **Upload data**: `cd scripts && python upload_data.py`
4. **Test connection**: `cd scripts && python test_connection.py`

## 🔑 Environment Variables

Each project needs environment variables:

### Backend & Scripts (.env)
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
GEMINI_API_KEY=your_gemini_key      # Recommended (free tier)
DEEPSEEK_API_KEY=your_deepseek_key  # Affordable alternative
OPENAI_API_KEY=your_openai_key      # Premium option
```

### Frontend
Environment variables handled via Next.js configuration.

## 🎯 Development Workflow

**Full Stack Development:**
```bash
# Terminal 1: Backend API
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2: Frontend  
cd frontend && npm run dev

# Terminal 3: Scripts (when needed)
cd scripts && python upload_data.py
```

## 🏭 Production Deployment

Each project deploys independently:

### Backend Deployment
```bash
cd backend
uv build              # Create wheel package
# Deploy to AWS Lambda, Docker, etc.
```

### Frontend Deployment  
```bash
cd frontend
npm run build          # Create static build
# Deploy to Vercel, Netlify, CDN
```

### Scripts Usage
```bash
cd scripts
pip install -r requirements.txt
# Run in CI/CD pipelines or developer machines
```

## 📚 Additional Documentation

- `backend/README.md` - Backend API details and development setup
- `frontend/README.md` - Frontend development and component structure  
- `scripts/README.md` - DevOps utilities and data pipeline
- `docs/` - Supabase setup, quality improvements, and LLM configuration

---

Each project is independent and can be developed, tested, and deployed separately while maintaining coordination through the shared API contract.