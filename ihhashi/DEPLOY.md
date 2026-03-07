# iHhashi Deployment Guide

Complete deployment guide for the iHhashi food delivery platform.

## Quick Start

### Option 1: Automatic Deployment (Git Push)

1. Push to `main` or `master` branch:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. GitHub Actions will automatically:
   - Run tests
   - Deploy backend to Railway
   - Deploy frontend to Netlify

### Option 2: Manual Deployment

Deploy both backend and frontend:
```bash
./deployment/scripts/full-deploy.sh
```

Deploy only backend:
```bash
./deployment/scripts/deploy-railway.sh
```

Deploy only frontend:
```bash
./deployment/scripts/deploy-netlify.sh --prod
```

## Prerequisites

### Required Accounts

1. **Railway** (Backend hosting): https://railway.app
2. **Netlify** (Frontend hosting): https://netlify.com
3. **MongoDB Atlas** (Database): https://mongodb.com/atlas
4. **Supabase** (Authentication): https://supabase.com

### Required Tools

```bash
# Install Railway CLI
npm install -g @railway/cli

# Install Netlify CLI
npm install -g netlify-cli

# Verify installations
railway --version
netlify --version
```

## Environment Setup

### 1. Backend Environment Variables (Railway)

Go to Railway Dashboard → Your Project → Variables

**Required:**
```env
MONGODB_URL=mongodb+srv://<user>:<password>@cluster.mongodb.net/ihhashi
SECRET_KEY=your-32-char-secret-key
ENVIRONMENT=production
DEBUG=false
```

**Authentication (Supabase):**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**CORS (Your Netlify URL):**
```env
CORS_ORIGINS=https://your-app.netlify.app,https://www.yourdomain.com
```

**Optional but Recommended:**
```env
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_PUBLIC_KEY=pk_live_...
GOOGLE_MAPS_API_KEY=your-maps-key
REDIS_URL=your-redis-url
GLITCHTIP_DSN=your-glitchtip-dsn
```

### 2. Frontend Environment Variables (Netlify)

Go to Netlify Dashboard → Your Site → Site Settings → Environment Variables

**Required:**
```env
VITE_API_URL=https://your-railway-app.up.railway.app
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

**Optional:**
```env
VITE_PAYSTACK_PUBLIC_KEY=pk_live_...
VITE_GOOGLE_MAPS_API_KEY=your-maps-key
VITE_POSTHOG_KEY=your-posthog-key
VITE_SENTRY_DSN=your-sentry-dsn
```

### 3. GitHub Secrets (for CI/CD)

Go to GitHub Repo → Settings → Secrets and Variables → Actions

Add these secrets:

| Secret | Description | Get From |
|--------|-------------|----------|
| `RAILWAY_TOKEN` | Railway API token | Railway Dashboard → Tokens |
| `NETLIFY_AUTH_TOKEN` | Netlify API token | Netlify User Settings → Applications |
| `NETLIFY_SITE_ID` | Netlify site ID | Site Settings → General |
| `VITE_API_URL` | Backend URL | Your Railway domain |
| `VITE_SUPABASE_URL` | Supabase project URL | Supabase Settings |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key | Supabase Settings |

## Deployment Configuration

### Railway Configuration (`backend/railway.toml`)

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-2}"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

### Netlify Configuration (`netlify.toml`)

```toml
[build]
  base = "frontend"
  publish = "dist"
  command = "npm run build"

[build.environment]
  NODE_VERSION = "20"
  NPM_FLAGS = "--legacy-peer-deps"

# API redirects
[[redirects]]
  from = "/api/*"
  to = "https://your-railway-app.up.railway.app/api/:splat"
  status = 200

# SPA fallback
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

## Local Development with Docker

### Start All Services

```bash
# Start backend, frontend, MongoDB, and Redis
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Start with Monitoring (GlitchTip)

```bash
docker compose --profile monitoring up -d
```

### Individual Services

```bash
# Only database
docker compose up -d mongodb redis

# Backend only
docker compose up -d backend

# Frontend only
docker compose up -d frontend
```

## Troubleshooting

### Backend Issues

**502 Bad Gateway on Railway:**
1. Check health endpoint: `curl https://your-app.up.railway.app/health`
2. Verify `PORT` environment variable is not hardcoded
3. Check Railway logs: `railway logs`

**MongoDB Connection Failed:**
1. Verify `MONGODB_URL` is correct
2. Check IP whitelist in MongoDB Atlas
3. Test connection locally with same URL

**CORS Errors:**
1. Update `CORS_ORIGINS` in Railway with your Netlify URL
2. Include `https://` prefix
3. No trailing slash

### Frontend Issues

**Build Fails:**
```bash
cd frontend
rm -rf node_modules dist
npm ci --legacy-peer-deps
npm run build
```

**API Calls Failing:**
1. Check `VITE_API_URL` is set correctly in Netlify
2. Verify CORS_ORIGINS includes your Netlify domain
3. Check browser console for CORS errors

### CI/CD Issues

**GitHub Actions Failing:**
1. Verify all secrets are set in GitHub
2. Check workflow file syntax
3. Review action logs in GitHub

**Railway Deployment Failing:**
1. Check `RAILWAY_TOKEN` is valid
2. Verify project is linked: `cd backend && railway status`
3. Check Railway build logs

## Health Checks

### Backend Health Endpoint

```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": {"status": "healthy"},
  "redis": "connected",
  "environment": "production",
  "timestamp": "2024-..."
}
```

### Frontend Health

```bash
curl https://your-site.netlify.app/health
```

## Security Checklist

- [ ] `SECRET_KEY` is at least 32 characters in production
- [ ] `DEBUG=false` in production
- [ ] `ENVIRONMENT=production` in production
- [ ] CORS_ORIGINS doesn't include localhost in production
- [ ] Using test payment keys in staging
- [ ] GlitchTip/Sentry configured for error tracking
- [ ] Rate limiting enabled

## Production Checklist

Before going live:

- [ ] Database indexes created
- [ ] Admin user created
- [ ] Payment webhooks configured
- [ ] SMS provider configured (Twilio)
- [ ] Push notifications configured (Firebase)
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active
- [ ] Monitoring dashboards set up
- [ ] Backup strategy in place

## Support

- **Railway Docs**: https://docs.railway.app
- **Netlify Docs**: https://docs.netlify.com
- **GitHub Actions**: https://docs.github.com/actions
- **iHhashi Issues**: https://github.com/your-repo/issues
