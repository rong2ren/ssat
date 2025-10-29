# SmartSSAT - AI-Powered SSAT Practice Platform

An intelligent web application that generates personalized SSAT (Secondary School Admission Test) practice questions using advanced AI models. Built for students preparing for elementary and middle-level SSAT exams.

## 🎯 Overview

SmartSSAT leverages OpenAI GPT and Google Gemini to generate authentic, SSAT-format practice questions across all test sections. The platform provides immediate feedback, detailed explanations, and adaptive difficulty levels to help students effectively prepare for the SSAT exam.

### Key Features

- **🤖 AI-Powered Question Generation**
  - Quantitative (Math) questions with varying difficulty
  - Verbal reasoning (Synonyms & Analogies)
  - Reading comprehension with authentic passages
  - Creative writing prompts with visual aids

- **📝 Flexible Practice Modes**
  - Single section practice (targeted learning)
  - Full-length practice tests (comprehensive assessment)
  - Customizable difficulty levels and question counts
  - Topic-specific practice sessions

- **✨ Smart Features**
  - Instant answer checking with detailed explanations
  - PDF export for offline practice
  - Daily usage limits with role-based access
  - Progress tracking and statistics
  - Bilingual support (English/Chinese)

- **🔐 User Management**
  - Secure authentication via Supabase
  - Email verification
  - Password reset functionality
  - User profiles with grade level tracking
  - Admin dashboard for content management

## 🏗️ Tech Stack

### Frontend
- **Framework:** Next.js 15.3.5 (App Router)
- **Language:** TypeScript 5+
- **UI:** React 19, Tailwind CSS 4.0, Radix UI
- **State Management:** React Context API
- **Authentication:** Supabase Client
- **Deployment:** Vercel

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **AI Models:** OpenAI GPT-4, Google Gemini
- **Database:** Supabase (PostgreSQL)
- **Authentication:** Supabase Auth + JWT
- **Embeddings:** Sentence Transformers
- **Deployment:** Google Cloud Run

### Infrastructure
- **Hosting:** Vercel (Frontend), Google Cloud Run (Backend)
- **Database:** Supabase PostgreSQL
- **Storage:** Supabase Storage (images)
- **CDN:** Vercel Edge Network

## 📁 Project Structure

```
ssat/
├── frontend/              # Next.js frontend application
│   ├── src/
│   │   ├── app/          # Next.js pages and API routes
│   │   ├── components/   # React components
│   │   ├── contexts/     # React Context providers
│   │   ├── lib/          # Utilities and configurations
│   │   └── types/        # TypeScript type definitions
│   └── package.json
│
├── backend/              # FastAPI backend API
│   ├── app/
│   │   ├── routers/     # API endpoint routers
│   │   ├── services/    # Business logic services
│   │   ├── models/      # Pydantic models
│   │   ├── config/      # Configuration management
│   │   └── main.py      # FastAPI application entry
│   ├── core/            # Core utilities (DB, prompts)
│   ├── tests/           # Backend tests
│   └── pyproject.toml
│
├── docs/                # Documentation
│   ├── DEPLOY.md       # Deployment guide
│   ├── AUTH_SETUP.md   # Authentication setup
│   └── ...
│
├── sql/                 # Database schemas and migrations
└── scripts/            # Utility scripts
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase account
- OpenAI API key
- Google Cloud account (for deployment)

### Local Development

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/ssat.git
cd ssat
```

**2. Setup Backend**
```bash
cd backend

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Create .env file with your credentials
# Copy from .env.example and fill in your values
cat > .env << EOF
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional
EOF

# Setup database (create tables)
# See sql/ directory for schema files

# Start backend server
uv run uvicorn app.main:app --reload --port 8000
```

**3. Setup Frontend**
```bash
cd frontend

# Install dependencies
npm install

# Create .env.local with your credentials
cat > .env.local << EOF
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
EOF

# Start frontend server
npm run dev
```

**4. Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Environment Variables

**Backend (.env):**
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

**Getting Supabase Credentials:**
1. Go to [supabase.com](https://supabase.com) and create a project
2. Navigate to Settings → API
3. Copy "Project URL" as `SUPABASE_URL`
4. Copy "service_role" key as `SUPABASE_KEY` (backend)
5. Copy "anon public" key as `SUPABASE_ANON_KEY` (frontend)

**Getting OpenAI API Key:**
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an API key in your account settings
3. Copy the key as `OPENAI_API_KEY`

## 📦 Deployment

### Frontend (Vercel)

**Automatic Deployment (Recommended):**
1. Connect your GitHub repository to Vercel
2. Set root directory to `frontend`
3. Add environment variables in Vercel dashboard
4. Every push to `main` will auto-deploy

**Manual Deployment:**
```bash
cd frontend
npm install -g vercel
vercel --prod
```

### Backend (Google Cloud Run)

```bash
cd backend

# First time deployment
gcloud run deploy ssat-backend \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars "SUPABASE_URL=your_url,SUPABASE_KEY=your_key,OPENAI_API_KEY=your_key"

# Future deployments (environment variables persist)
gcloud run deploy ssat-backend --source . --region us-central1
```

See [docs/DEPLOY.md](docs/DEPLOY.md) for detailed deployment instructions.

## 🧪 Testing

```bash
# Backend tests
cd backend
uv run pytest tests/ -v

# Frontend tests (if configured)
cd frontend
npm test
```

## 📊 Features & Capabilities

### Question Generation
- Generate 5-50 questions per session
- Difficulty levels: Easy, Medium, Hard
- AI-powered explanations for each answer
- Support for all SSAT sections

### SSAT Sections Covered
- **Quantitative (Math):** Word problems, algebra, geometry, fractions
- **Verbal:** Synonyms, analogies, vocabulary
- **Reading:** Passages with comprehension questions
- **Writing:** Creative prompts with optional visual aids

### User Roles & Limits
- **Free Users:** 20 questions/day per section
- **Premium Users:** 100 questions/day per section  
- **Admin Users:** Unlimited access + content management

### Admin Dashboard
- View all users and their usage statistics
- Manage question pool and training examples
- Monitor system performance
- Review and approve AI-generated content

## 🛠️ Development

### Backend Development

```bash
cd backend

# Run tests
uv run pytest tests/ -v

# Run with auto-reload
uv run uvicorn app.main:app --reload

# Check code quality
uv run ruff check .
```

### Frontend Development

```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Type check
npm run type-check
```

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- **[DEPLOY.md](docs/DEPLOY.md)** - Deployment guide for Vercel and Google Cloud
- **[AUTH_SETUP.md](docs/AUTH_SETUP.md)** - Authentication configuration
- **[FRONTEND_ENVIRONMENT_SETUP.md](docs/FRONTEND_ENVIRONMENT_SETUP.md)** - Frontend setup guide
- **[POOL_IMPLEMENTATION.md](docs/POOL_IMPLEMENTATION.md)** - Question pool architecture
- **[LLM.md](docs/LLM.md)** - AI model integration details

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Backend: Follow PEP 8, use type hints
- Frontend: Follow ESLint rules, use TypeScript
- Write tests for new features
- Update documentation as needed

## 🐛 Troubleshooting

### Common Issues

**"Missing Supabase environment variables"**
- Create `.env.local` in frontend directory
- Ensure all required variables are set
- Restart dev server after changes

**"Failed to connect to backend"**
- Check if backend is running on port 8000
- Verify `NEXT_PUBLIC_BACKEND_URL` is correct
- Check for CORS errors in browser console

**"Authentication infinite spinner"**
- Clear browser localStorage: `localStorage.clear()`
- Verify Supabase URL and keys are correct
- Check browser console for errors

**"AI generation errors"**
- Verify OpenAI API key is valid and has credits
- Check API rate limits
- Review backend logs for detailed errors

See [frontend/README.md](frontend/README.md) for more troubleshooting tips.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **rong2ren** - [GitHub](https://github.com/rong2ren)

## 🙏 Acknowledgments

- OpenAI for GPT models
- Google for Gemini AI
- Supabase for authentication and database
- SSAT official materials for reference
- Open-source community for amazing tools

## 📧 Support

For questions or support:
- Open an issue on GitHub
- Email: ssat@schoolbase.org
- Check documentation in `docs/` directory

## 🔒 Security

- Never commit API keys or secrets to the repository
- Use environment variables for all sensitive data
- Keep dependencies up to date
- Report security vulnerabilities privately

## 📈 Roadmap

- [ ] Add more question types
- [ ] Implement spaced repetition algorithm
- [ ] Mobile app (React Native)
- [ ] Performance analytics dashboard
- [ ] Multi-language support expansion
- [ ] Integration with learning management systems

---

**Built with ❤️ for students preparing for the SSAT exam**
