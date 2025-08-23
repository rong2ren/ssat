# SSAT Frontend

Modern React/Next.js frontend for the SSAT Question Generator. This is a TypeScript-based web application that provides an intuitive interface for generating SSAT practice questions and tests.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local  # If .env.example exists
# Or create .env.local manually (see Environment Variables section)

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## 🏗️ Tech Stack

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

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── api/               # API routes (backend proxy)
│   │   ├── auth/              # Authentication pages
│   │   ├── dashboard/         # User dashboard
│   │   ├── generate/          # Question generation pages
│   │   ├── admin/             # Admin panel
│   │   └── globals.css        # Global styles
│   ├── components/            # Reusable React components
│   │   ├── ui/               # Base UI components
│   │   ├── forms/            # Form components
│   │   ├── layout/           # Layout components
│   │   └── features/         # Feature-specific components
│   ├── contexts/             # React Context providers
│   ├── hooks/                # Custom React hooks
│   ├── lib/                  # Utility libraries
│   │   └── supabase.ts       # Supabase client configuration
│   ├── types/                # TypeScript type definitions
│   └── utils/                # Utility functions
├── public/                   # Static assets
├── .env.local               # Environment variables (create this)
├── next.config.ts           # Next.js configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── package.json             # Dependencies and scripts
```

## ⚙️ Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# Backend API URL (required)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Supabase Configuration (required)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_public_key
```

### Environment Variable Details

- **`NEXT_PUBLIC_BACKEND_URL`**: URL of the backend API server
  - Development: `http://localhost:8000`
  - Production: `https://your-backend-domain.com`

- **`NEXT_PUBLIC_SUPABASE_URL`**: Your Supabase project URL
  - Found in Supabase Dashboard → Settings → API

- **`NEXT_PUBLIC_SUPABASE_ANON_KEY`**: Your Supabase anonymous public key
  - Found in Supabase Dashboard → Settings → API
  - This is safe to expose to the browser

## 🔧 Development

### Prerequisites
- Node.js 18+ 
- Backend server running (see backend README)
- Supabase project configured

### Available Scripts

```bash
# Development
npm run dev              # Start development server
npm run build           # Build for production
npm run start           # Start production server
npm run lint            # Run ESLint
npm run type-check      # Run TypeScript type checking

# Testing (if configured)
npm run test            # Run tests
npm run test:watch      # Run tests in watch mode
```

### Development Workflow

1. **Start Backend First**
   ```bash
   cd ../backend
   uv run uvicorn app.main:app --reload --port 8000
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Code Quality

```bash
# Format code
npm run format

# Lint code
npm run lint

# Type checking
npm run type-check
```

## 🎨 UI Components

The frontend uses a component-based architecture with:

### Base Components (Radix UI)
- **Button** - Accessible button components
- **Input** - Form input components
- **Dialog** - Modal dialogs
- **Dropdown** - Dropdown menus
- **Toast** - Notification system

### Custom Components
- **QuestionCard** - Display individual questions
- **TestGenerator** - Complete test generation interface
- **AuthForm** - Authentication forms
- **Dashboard** - User dashboard layout
- **AdminPanel** - Administrative interface

## 🔐 Authentication

The frontend uses Supabase Auth for authentication:

### Features
- Email/password registration and login
- Password reset functionality
- Email confirmation
- Session management
- Protected routes

### Implementation
- **AuthContext**: Global authentication state
- **AuthGuard**: Route protection component
- **AuthForm**: Login/register forms
- **Session Management**: Automatic token refresh

## 📡 API Integration

The frontend communicates with the backend through:

### API Routes
- `/api/generate` - Question generation
- `/api/generate/complete-test/start` - Start test generation
- `/api/generate/complete-test/{id}/status` - Check generation status
- `/api/auth/*` - Authentication endpoints
- `/api/user/*` - User management

### Error Handling
- Global error boundary
- API error responses
- User-friendly error messages
- Retry mechanisms for failed requests

## 🚀 Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

### Netlify
```bash
# Build the project
npm run build

# Deploy the .next folder
```

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Environment Variables for Production

Update your production environment variables:

```env
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_public_key
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Missing Supabase environment variables"
- Ensure `.env.local` file exists in frontend directory
- Verify all required environment variables are set
- Restart the development server

#### 2. "Failed to connect to backend"
- Check if backend server is running on port 8000
- Verify `NEXT_PUBLIC_BACKEND_URL` is correct
- Check CORS configuration in backend

#### 3. "Authentication errors"
- Verify Supabase project is active
- Check Supabase URL and keys are correct
- Ensure email confirmation is enabled in Supabase

#### 4. Build errors
```bash
# Clear Next.js cache
rm -rf .next
npm run build
```

### Debug Mode
```bash
# Enable debug logging
DEBUG=* npm run dev
```

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Radix UI Documentation](https://www.radix-ui.com/docs)

## 🤝 Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Test your changes thoroughly
4. Update documentation as needed

---

For backend setup and API documentation, see the [backend README](../backend/README.md).
