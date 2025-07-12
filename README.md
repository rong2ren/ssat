# SSAT Question Generator

An AI-powered SSAT question generator for elementary level students. This monorepo contains independent frontend, backend, and utility projects.

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
python test_connection.py        # Test database
python upload_data.py            # Upload training data
```

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

## 📚 Project Documentation

- `backend/README.md` - Backend API documentation
- `frontend/README.md` - Frontend setup and development
- `scripts/README.md` - DevOps utilities documentation
- `docs/` - Additional project documentation

## 🤝 Contributing

1. Choose your area: Frontend (npm), Backend (uv), or Scripts (pip)
2. Follow the setup instructions for that project
3. Make changes and test in isolation
4. Submit pull requests

## 📋 Development Commands Summary

```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --reload

# Frontend  
cd frontend && npm install && npm run dev

# Scripts
cd scripts && pip install -r requirements.txt && python script_name.py

# Database
cd scripts && python test_connection.py
```

Each project is independent and can be developed, tested, and deployed separately while maintaining coordination through the shared API contract.