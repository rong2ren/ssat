# SSAT Question Generator

An AI-powered SSAT question generator for elementary level students. This monorepo contains independent frontend, backend, and utility projects.

## 📋 Table of Contents

- [🏗️ Project Structure](#️-project-structure)
- [🚀 Quick Start](#-quick-start)
- [🔧 Prerequisites](#-prerequisites)
- [⚙️ Installation & Setup](#️-installation--setup)
- [🔧 Technology Stack](#-technology-stack)
- [📦 Key Features](#-key-features)
- [🏛️ Architecture](#️-architecture)
- [🗃️ Database Setup](#️-database-setup)
- [🔑 Environment Variables](#-environment-variables)
- [🎯 Development Workflow](#-development-workflow)
- [🏭 Production Deployment](#-production-deployment)
- [🐛 Troubleshooting](#-troubleshooting)

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

After completing the setup steps below, you can start the development servers:

```bash
# Terminal 1: Backend API
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend  
cd frontend && npm run dev
```

## 🔧 Prerequisites

Before you begin, ensure you have the following installed:

### Required Software
- **Node.js** (v18 or higher) - [Download here](https://nodejs.org/)
- **Python** (3.11 or higher) - [Download here](https://www.python.org/downloads/)
- **Git** - [Download here](https://git-scm.com/downloads)

### Optional but Recommended
- **Homebrew** (macOS) - [Install here](https://brew.sh/)
- **Docker** - [Download here](https://www.docker.com/products/docker-desktop/)

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ssat.git
cd ssat
```

### 2. Install UV (Python Package Manager)
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using Homebrew (macOS)
brew install uv

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Backend Setup
```bash
cd backend

# Install dependencies
uv sync

# Create environment file
cp .env.example .env  # If .env.example exists
# Or create .env manually (see Environment Variables section)
```

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create environment file
touch .env.local
# Add required environment variables (see Environment Variables section)
```

### 5. Database Setup (Supabase)
1. **Create Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and API keys

2. **Run Database Schema**
   - In Supabase Dashboard → SQL Editor
   - Execute the contents of `sql/schema.sql`

3. **Upload Training Data**
   ```bash
   cd scripts
   pip install -r requirements.txt
   python upload_data.py
   ```

## 🔧 Technology Stack

### 🏗️ **Backend Stack**
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

### 🎨 **Frontend Stack**
| Component            | Technology      | Version  | Purpose                         |
| -------------------- | --------------- | -------- | ------------------------------- |
| **Framework**        | Next.js         | 15.3.5   | React framework with App Router |
| **Language**         | TypeScript      | 5+       | Type-safe JavaScript            |
| **UI Library**       | React           | 19.0.0   | Component library               |
| **Styling**          | Tailwind CSS    | 4.0+     | Utility-first CSS framework     |
| **UI Components**    | Radix UI        | Latest   | Accessible component primitives |
| **Icons**            | Lucide React    | 0.525.0  | Icon library                    |
| **State Management** | React Context   | Built-in | Global state management         |
| **Authentication**   | Supabase Client | 2.52.0   | Client-side auth                |
| **HTTP Client**      | Fetch API       | Built-in | API communication               |
| **Build Tool**       | Turbopack       | Built-in | Fast bundler                    |

### 🗄️ **Database & Infrastructure**
| Component              | Technology           | Purpose                                 |
| ---------------------- | -------------------- | --------------------------------------- |
| **Database**           | Supabase PostgreSQL  | Primary data storage                    |
| **Vector Extensions**  | pgvector             | Embedding storage and similarity search |
| **Real-time**          | Supabase Realtime    | Live updates                            |
| **Row Level Security** | Supabase RLS         | Data access control                     |
| **Functions**          | PostgreSQL Functions | Complex queries and business logic      |
| **Storage**            | Supabase Storage     | File storage (images, PDFs)             |

### 🤖 **AI & Machine Learning**
| Component             | Technology                          | Purpose                     |
| --------------------- | ----------------------------------- | --------------------------- |
| **LLM Integration**   | OpenAI API, Google AI, DeepSeek API | Question generation         |
| **Embedding Model**   | all-MiniLM-L6-v2                    | Text embedding generation   |
| **Semantic Search**   | Vector similarity (cosine)          | Finding similar questions   |
| **Few-shot Learning** | Custom prompts with examples        | Quality question generation |
| **Content Pool**      | Pre-generated question database     | Instant delivery system     |

### 🛠️ **Development Tools**
| Component                      | Technology                  | Purpose                           |
| ------------------------------ | --------------------------- | --------------------------------- |
| **Package Manager (Backend)**  | UV                          | Fast Python dependency management |
| **Package Manager (Frontend)** | npm                         | Node.js package management        |
| **Linting (Frontend)**         | ESLint                      | Code quality and consistency      |
| **Type Checking**              | TypeScript                  | Static type checking              |
| **Hot Reload**                 | FastAPI reload, Next.js dev | Development experience            |
| **API Documentation**          | FastAPI auto-docs           | Interactive API documentation     |

### 📊 **Monitoring & Logging**
| Component            | Technology            | Purpose                        |
| -------------------- | --------------------- | ------------------------------ |
| **Backend Logging**  | Loguru                | Structured application logging |
| **Frontend Logging** | Console + API routes  | Client-side event tracking     |
| **Error Tracking**   | Custom error handlers | Error monitoring               |
| **Performance**      | Built-in timing       | Response time monitoring       |
| **Health Checks**    | Custom endpoints      | System health monitoring       |

### 🔒 **Security & Authentication**
| Component             | Technology              | Purpose               |
| --------------------- | ----------------------- | --------------------- |
| **Authentication**    | Supabase Auth           | User authentication   |
| **Authorization**     | JWT tokens              | API access control    |
| **Role-based Access** | Custom role system      | User permissions      |
| **CORS**              | FastAPI CORS middleware | Cross-origin security |
| **Input Validation**  | Pydantic models         | Data sanitization     |
| **Rate Limiting**     | Custom implementation   | API abuse prevention  |

### 🚀 **Deployment & DevOps**
| Component                  | Technology               | Purpose                  |
| -------------------------- | ------------------------ | ------------------------ |
| **Backend Deployment**     | Docker, AWS Lambda, etc. | Server deployment        |
| **Frontend Deployment**    | Vercel, Netlify          | Static site hosting      |
| **Environment Management** | .env files               | Configuration management |
| **Database Migration**     | SQL scripts              | Schema management        |
| **CI/CD**                  | GitHub Actions (planned) | Automated deployment     |

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

### 1. Supabase Project Setup
1. **Create Project**
   - Go to [supabase.com](https://supabase.com)
   - Click "New Project"
   - Choose organization and enter project name
   - Set database password (save this!)
   - Choose region closest to your users

2. **Get API Keys**
   - Go to Settings → API
   - Copy:
     - Project URL
     - anon public key
     - service_role key (keep this secret!)

3. **Enable Extensions**
   - Go to SQL Editor
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

### 2. Database Schema
1. **Execute Schema**
   - In Supabase SQL Editor
   - Copy and paste contents of `sql/schema.sql`
   - Click "Run" to execute

2. **Verify Setup**
   - Check Tables section in Supabase Dashboard
   - Should see: users, questions, embeddings, etc.

### 3. Upload Training Data
```bash
cd scripts
pip install -r requirements.txt

# Set environment variables first
export SUPABASE_URL="your_supabase_url"
export SUPABASE_KEY="your_service_role_key"

# Upload data
python upload_data.py
```

### 4. Test Connection
```bash
cd scripts
python test_connection.py
```

## 🔑 Environment Variables

### Backend Environment (.env)
Create `backend/.env`:
```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# AI API Keys (at least one required)
GEMINI_API_KEY=your_gemini_key          # Recommended (free tier)
DEEPSEEK_API_KEY=your_deepseek_key      # Affordable alternative
OPENAI_API_KEY=your_openai_key          # Premium option

# Optional: Logging
LOG_LEVEL=INFO
```

### Frontend Environment (.env.local)
Create `frontend/.env.local`:
```env
# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_public_key
```

### Scripts Environment
For scripts that need database access:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

## 🎯 Development Workflow

### Starting Development Servers
```bash
# Terminal 1: Backend API
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend  
cd frontend
npm run dev

# Terminal 3: Scripts (when needed)
cd scripts
python upload_data.py
```

### Development URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Common Development Tasks
```bash
# Backend
cd backend
uv sync                    # Install/update dependencies
uv run pytest             # Run tests
uv run black .            # Format code
uv run mypy .             # Type checking

# Frontend
cd frontend
npm install               # Install dependencies
npm run build            # Build for production
npm run lint             # Lint code
npm run type-check       # TypeScript checking
```

## 🏭 Production Deployment

### Backend Deployment Options

#### Option 1: Docker Deployment
```bash
cd backend

# Build Docker image
docker build -t ssat-backend .

# Run container
docker run -p 8000:8000 --env-file .env ssat-backend
```

#### Option 2: Railway Deployment
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
cd backend
railway login
railway init
railway up
```

#### Option 3: Render Deployment
1. Connect GitHub repository to Render
2. Set build command: `uv sync && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables in Render dashboard

#### Option 4: AWS Lambda (Serverless)
```bash
cd backend
uv build
# Use AWS SAM or Serverless Framework for deployment
```

### Frontend Deployment Options

#### Option 1: Vercel (Recommended)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel
```

#### Option 2: Netlify
```bash
cd frontend
npm run build
# Drag and drop dist folder to Netlify
```

#### Option 3: Railway
```bash
cd frontend
railway login
railway init
railway up
```

### Environment Variables for Production

#### Backend Production (.env)
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key
LOG_LEVEL=WARNING
CORS_ORIGINS=https://your-frontend-domain.com
```

#### Frontend Production (.env.production)
```env
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_public_key
```

### Database Migration
```bash
# For schema changes
cd sql
# Update schema.sql and run in Supabase SQL Editor
```

### Monitoring & Logging
- **Backend**: Loguru logs to stdout/stderr
- **Frontend**: Console logs + API route logging
- **Database**: Supabase dashboard monitoring

## 🐛 Troubleshooting

### Common Issues

#### 1. UV Command Not Found
```bash
# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart terminal
```

#### 2. Node Modules Issues
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### 3. Python Dependencies Issues
```bash
cd backend
rm -rf .venv
uv sync
```

#### 4. Supabase Connection Issues
- Verify environment variables are correct
- Check Supabase project is active
- Ensure service role key has proper permissions

#### 5. CORS Issues
- Verify `NEXT_PUBLIC_BACKEND_URL` is correct
- Check backend CORS configuration
- Ensure frontend and backend ports match

#### 6. AI API Issues
- Verify API keys are valid
- Check API quotas and limits
- Ensure at least one AI provider is configured

### Debug Mode
```bash
# Backend debug
cd backend
uv run uvicorn app.main:app --reload --log-level debug

# Frontend debug
cd frontend
DEBUG=* npm run dev
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000/api/health
```

### Logs
```bash
# Backend logs
cd backend
uv run uvicorn app.main:app --reload --log-level debug

# Frontend logs
cd frontend
npm run dev
# Check browser console and terminal output
```

---

## 📚 Additional Documentation

- `backend/README.md` - Backend API details and development setup
- `frontend/README.md` - Frontend development and component structure  
- `scripts/README.md` - DevOps utilities and data pipeline
- `docs/` - Supabase setup, quality improvements, and LLM configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Each project is independent and can be developed, tested, and deployed separately while maintaining coordination through the shared API contract.