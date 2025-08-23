# Frontend Environment Setup

This document provides detailed instructions for setting up the frontend environment for the SSAT Question Generator.

## 🚀 Quick Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Edit .env.local with your actual values
# (see Environment Variables section below)

# Start development server
npm run dev
```

## ⚙️ Environment Variables

The frontend requires the following environment variables to be set in `.env.local`:

### Required Variables

| Variable                        | Description            | Example                                   |
| ------------------------------- | ---------------------- | ----------------------------------------- |
| `NEXT_PUBLIC_BACKEND_URL`       | Backend API server URL | `http://localhost:8000`                   |
| `NEXT_PUBLIC_SUPABASE_URL`      | Supabase project URL   | `https://your-project.supabase.co`        |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |

### Environment Variable Details

#### `NEXT_PUBLIC_BACKEND_URL`
- **Development**: `http://localhost:8000`
- **Production**: `https://your-backend-domain.com`
- **Purpose**: URL of the backend API server that the frontend communicates with

#### `NEXT_PUBLIC_SUPABASE_URL`
- **Source**: Supabase Dashboard → Settings → API → Project URL
- **Purpose**: Your Supabase project URL for authentication and database access

#### `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Source**: Supabase Dashboard → Settings → API → anon public key
- **Purpose**: Anonymous key for client-side Supabase operations
- **Security**: Safe to expose to the browser (has limited permissions)

### Optional Variables

```env
# Custom configuration (optional)
NEXT_PUBLIC_APP_NAME=SSAT Question Generator
NEXT_PUBLIC_APP_VERSION=1.0.0
```

## 🔧 Setup Instructions

### 1. Create Environment File

```bash
cd frontend
touch .env.local
```

### 2. Add Environment Variables

Copy the following template to your `.env.local` file:

```env
# Backend API URL (required)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Supabase Configuration (required)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

### 3. Replace Placeholder Values

1. **Get Supabase Credentials:**
   - Go to your Supabase project dashboard
   - Navigate to Settings → API
   - Copy the "Project URL" and "anon public" key
   - Replace the placeholder values in your `.env.local` file

2. **Set Backend URL:**
   - For development: `http://localhost:8000`
   - For production: Your deployed backend URL

## 🔍 Environment Variable Rules

### `NEXT_PUBLIC_*` Prefix
- **Purpose**: Variables with this prefix are exposed to the browser
- **Usage**: Can be used in client-side code (React components, API routes)
- **Security**: Only use for non-sensitive data that's safe to expose

### Variables Without `NEXT_PUBLIC_`
- **Purpose**: Server-side only variables
- **Usage**: Can only be used in API routes and server-side code
- **Security**: Safe for sensitive data (API keys, secrets)

## 🌐 Current Usage

### API Routes
All frontend API routes use `NEXT_PUBLIC_BACKEND_URL` to communicate with the backend:

```typescript
// Example from src/app/api/generate/route.ts
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
```

### Authentication
Supabase client uses the Supabase environment variables:

```typescript
// Example from src/lib/supabase.ts
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
```

## 🚀 Production Deployment

### Environment Variables for Production

Update your production environment variables:

```env
# Production backend URL
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com

# Supabase configuration (same as development)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Deployment Platforms

#### Vercel
1. Go to your Vercel project settings
2. Navigate to Environment Variables
3. Add each variable with the exact same names

#### Netlify
1. Go to Site settings → Environment variables
2. Add each variable with the exact same names

#### Railway
1. Go to your project settings
2. Navigate to Variables
3. Add each variable with the exact same names

## 🐛 Troubleshooting

### Common Issues

#### 1. "Missing Supabase environment variables"
```bash
# Check if .env.local exists
ls -la frontend/.env.local

# Verify variables are set
cat frontend/.env.local
```

#### 2. "Failed to connect to backend"
- Verify backend server is running on port 8000
- Check `NEXT_PUBLIC_BACKEND_URL` is correct
- Ensure CORS is configured in backend

#### 3. "Authentication errors"
- Verify Supabase project is active
- Check Supabase URL and keys are correct
- Ensure email confirmation is enabled in Supabase

### Debug Mode
```bash
# Enable debug logging
DEBUG=* npm run dev
```

### Environment Variable Validation
```bash
# Check if environment variables are loaded
npm run dev
# Look for any error messages about missing variables
```

## 📚 Additional Resources

- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
- [Supabase Documentation](https://supabase.com/docs)
- [Frontend README](../frontend/README.md)
- [Backend README](../backend/README.md)

## 🔄 Migration from Previous Versions

If you're updating from a previous version:

1. **Backup your current `.env.local`**
2. **Compare with `.env.example`** to see new required variables
3. **Add any missing variables** to your `.env.local`
4. **Test the application** to ensure everything works

---

**Note**: Never commit your `.env.local` file to version control. The `.env.example` file serves as a template for other developers. 