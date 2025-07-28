# Deployment Guide

This guide covers deploying both the frontend (Vercel) and backend (Google Cloud Run) for the SSAT Practice application.

## Prerequisites

- Google Cloud account with billing enabled
- Vercel account
- GitHub repository with your code
- Domain name (optional): `ssat.schoolbase.org`

## Backend Deployment (Google Cloud Run)

### 1. Install Google Cloud CLI

**macOS (Recommended):**
```bash
brew install --cask google-cloud-sdk
```

**Alternative (Official installer):**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install google-cloud-cli
```

**Linux (Red Hat/Fedora/CentOS):**
```bash
sudo dnf install google-cloud-cli
```

### 2. Authenticate and Setup

```bash
# Authenticate with Google Cloud
gcloud auth login

# List your projects
gcloud projects list

# Set your project (replace with your actual project ID)
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 3. Deploy Backend

```bash
# Navigate to backend directory
cd backend

# Deploy to Google Cloud Run
gcloud run deploy ssat-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars "SUPABASE_URL=your_supabase_url,SUPABASE_KEY=your_supabase_service_role_key,OPENAI_API_KEY=your_openai_key,ANTHROPIC_API_KEY=your_anthropic_key"
```

### 4. Alternative: Deploy in Steps

```bash
# Step 1: Deploy without environment variables
gcloud run deploy ssat-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080

# Step 2: Update with environment variables
gcloud run services update ssat-backend \
  --region us-central1 \
  --set-env-vars "SUPABASE_URL=your_supabase_url,SUPABASE_KEY=your_supabase_service_role_key,OPENAI_API_KEY=your_openai_key,ANTHROPIC_API_KEY=your_anthropic_key"
```

### 5. Get Your Backend URL

After deployment, you'll receive a URL like:
```
https://ssat-backend-xxxxx-uc.a.run.app
```

**Save this URL - you'll need it for frontend configuration!**

## Future Backend Deployments

### Simple Redeploy (Recommended)
After your first deployment, for future code updates, you only need:
```bash
cd backend
gcloud run deploy ssat-backend --source . --region us-central1
```
**No need to specify environment variables again** - they persist between deployments!

### Environment Variable Management

**View current environment variables:**
```bash
gcloud run services describe ssat-backend --region us-central1
```

**Update specific environment variables:**
```bash
gcloud run services update ssat-backend \
  --region us-central1 \
  --set-env-vars "NEW_VAR=value,EXISTING_VAR=new_value"
```

**Add new environment variables:**
```bash
gcloud run services update ssat-backend \
  --region us-central1 \
  --update-env-vars "NEW_API_KEY=sk-123456"
```

**Remove environment variables:**
```bash
gcloud run services update ssat-backend \
  --region us-central1 \
  --remove-env-vars "OLD_VAR"
```

**Replace all environment variables:**
```bash
gcloud run services update ssat-backend \
  --region us-central1 \
  --set-env-vars "VAR1=value1,VAR2=value2,VAR3=value3"
```

## Frontend Deployment (Vercel)

### 1. Deploy via Vercel Web Interface

1. **Go to [vercel.com](https://vercel.com)** and sign in
2. **Click "New Project"**
3. **Import your GitHub repository**
4. **Configure the project:**
   - **Framework**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)

### 2. Set Environment Variables

In your Vercel project settings, add these environment variables:

```
NEXT_PUBLIC_BACKEND_URL=https://your-backend-url.com
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 3. Deploy

Click "Deploy" and wait for the build to complete.

## Environment Variables Reference

### Backend Environment Variables (Google Cloud Run)

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_KEY` | Supabase service role key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |

### Frontend Environment Variables (Vercel)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_BACKEND_URL` | Your backend URL from Google Cloud Run | `https://ssat-backend-xxxxx-uc.a.run.app` |
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL | `https://your-project.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |

## Custom Domain Setup

### Frontend Domain (Vercel)

1. In Vercel project settings, go to "Domains"
2. Add your domain: `ssat.schoolbase.org`
3. Update your DNS records as instructed by Vercel

### Backend Domain (Google Cloud Run)

1. In Google Cloud Console, go to Cloud Run
2. Select your service
3. Go to "Manage Custom Domains"
4. Add domain: `api.ssat.schoolbase.org`
5. Update DNS records

## Testing Your Deployment

### Test Backend
```bash
# Test the backend API
curl https://your-backend-url.com/docs

# Should show FastAPI documentation
```

### Test Frontend
1. Visit your frontend URL
2. Try registering/logging in
3. Test generating questions

## Troubleshooting

### Common Issues

**Backend Issues:**
- **"Permission denied"**: Make sure you're authenticated and have the right project selected
- **"API not enabled"**: Run the enable commands for required APIs
- **"Environment variables missing"**: Check that all required env vars are set

**Frontend Issues:**
- **"Cannot connect to backend"**: Verify `NEXT_PUBLIC_BACKEND_URL` is correct
- **"Build failed"**: Check that all dependencies are in `package.json`

### Useful Commands

```bash
# Check backend status
gcloud run services describe ssat-backend --region us-central1

# View backend logs
gcloud run services logs read ssat-backend --region us-central1

# Update backend
gcloud run services update ssat-backend --region us-central1 --set-env-vars "NEW_VAR=value"

# List all services
gcloud run services list --region us-central1
```

## Cost Optimization

### Google Cloud Run Free Tier
- **2 million requests per month**
- **360,000 vCPU-seconds** (100 hours of 1 vCPU)
- **180,000 GiB-seconds** (50 hours of 1GB memory)
- **1GB network egress per month**

### Vercel Free Tier
- **100GB bandwidth per month**
- **100GB storage**
- **Unlimited personal projects**

## Security Notes

- Never commit API keys to your repository
- Use environment variables for all sensitive data
- Enable HTTPS for all domains
- Regularly rotate API keys
- Monitor usage to stay within free tiers

## Next Steps

After deployment:
1. Test all functionality
2. Set up monitoring and logging
3. Configure custom domains
4. Set up CI/CD for automatic deployments
5. Monitor costs and usage

## Support

- **Google Cloud**: [Cloud Run Documentation](https://cloud.google.com/run/docs)
- **Vercel**: [Vercel Documentation](https://vercel.com/docs)
- **Supabase**: [Supabase Documentation](https://supabase.com/docs) 