# iHhashi Deployment Guide

This guide will help you deploy the iHhashi food delivery app to production.

## Quick Start

```bash
# Run the full deployment
./deployment/scripts/deploy-all.sh

# Or step by step:
./deployment/scripts/setup-env.sh      # Set up environment variables
./deployment/scripts/deploy-railway.sh  # Deploy backend
./deployment/scripts/deploy-netlify.sh  # Deploy frontend
```

## Prerequisites

1. **Railway CLI**: `npm install -g @railway/cli`
2. **Netlify CLI**: `npm install -g netlify-cli`
3. **MongoDB Database**: MongoDB Atlas account (free tier works)
4. **Supabase Account**: For phone OTP authentication

## Deployment Steps

### 1. Setup Environment Variables

Run the setup script to generate secrets and see what variables you need:

```bash
./deployment/scripts/setup-env.sh
```

### 2. Deploy Backend to Railway

```bash
./deployment/scripts/deploy-railway.sh
```

Or manually:

```bash
cd backend
railway login
railway link  # Create or select project
railway up
```

**Required Railway Environment Variables:**
- `MONGODB_URL` - Your MongoDB connection string
- `SECRET_KEY` - Generate with: `openssl rand -base64 32`
- `SUPABASE_URL` - From Supabase project settings
- `SUPABASE_ANON_KEY` - From Supabase project settings
- `SUPABASE_SERVICE_ROLE_KEY` - From Supabase project settings
- `CORS_ORIGINS` - Your Netlify frontend URL(s)

### 3. Deploy Frontend to Netlify

```bash
./deployment/scripts/deploy-netlify.sh
```

Or manually:

```bash
cd frontend
npm ci
npm run build
netlify login
netlify link  # Create or select site
netlify deploy --prod --dir=dist
```

**Required Frontend Environment Variables:**
- `VITE_API_URL` - Your Railway backend URL (e.g., `https://ihhashi-api.up.railway.app`)
- `VITE_SUPABASE_URL` - From Supabase
- `VITE_SUPABASE_ANON_KEY` - From Supabase

Set these in:
- Netlify Dashboard: Site Settings > Environment Variables
- OR create `frontend/.env.local` file

### 4. Update CORS Origins

After first deployment, update `CORS_ORIGINS` in Railway with your actual Netlify URL:

```
CORS_ORIGINS=https://your-app.netlify.app,https://your-app-123.netlify.app
```

## Troubleshooting

### Backend Won't Start

1. **Check logs**: `railway logs --follow`
2. **Verify environment variables** are set correctly
3. **Test MongoDB connection** from local machine
4. **Health endpoint**: `curl https://your-app.up.railway.app/health`

### Frontend Can't Connect to API

1. **Check CORS_ORIGINS** includes your Netlify URL
2. **Verify VITE_API_URL** is set correctly
3. **Check browser console** for CORS errors
4. **Test API directly**: `curl https://your-api.up.railway.app/`

### Database Connection Issues

1. **Whitelist Railway IPs** in MongoDB Atlas:
   - Go to Network Access > Add IP Address
   - Add `0.0.0.0/0` (allow from anywhere) OR Railway's specific IPs
2. **Check connection string** format:
   ```
   mongodb+srv://user:password@cluster.mongodb.net/ihhashi?retryWrites=true&w=majority
   ```

### Build Failures

**Backend:**
```bash
cd backend
python -m pip install -r requirements.txt
# Test locally: uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm ci
npm run build
# Check for TypeScript errors: npm run typecheck
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Netlify       │────▶│    Railway      │────▶│   MongoDB       │
│   (Frontend)    │     │   (Backend)     │     │   (Database)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Supabase Auth  │     │   Redis Cache   │
└─────────────────┘     └─────────────────┘
```

## Monitoring

- **Railway Dashboard**: https://railway.app/dashboard
- **Netlify Dashboard**: https://app.netlify.com
- **Health Check**: `GET /health` on your backend

## Support

If deployment fails:
1. Check the specific service logs
2. Verify all environment variables are set
3. Test locally first: `docker-compose up`
