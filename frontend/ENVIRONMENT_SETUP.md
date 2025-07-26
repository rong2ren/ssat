# Frontend Environment Setup

## Environment Variables

The frontend needs the following environment variables to be set:

### Required Variables

- `NEXT_PUBLIC_BACKEND_URL`: The URL of the backend API server

### Setup Instructions

1. Create a `.env.local` file in the frontend directory:
```bash
cd frontend
touch .env.local
```

2. Add the following content to `.env.local`:
```env
# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Environment Variable Rules

- **`NEXT_PUBLIC_*`**: These variables are exposed to the browser and can be used in client-side code
- **Without `NEXT_PUBLIC_`**: These variables are server-side only and not exposed to the browser

### Current Usage

All API routes in the frontend use `NEXT_PUBLIC_BACKEND_URL` to communicate with the backend server.

### Production Deployment

For production, update `NEXT_PUBLIC_BACKEND_URL` to point to your production backend URL. 