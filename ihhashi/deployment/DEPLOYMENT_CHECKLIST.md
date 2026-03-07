# Deployment Checklist

## Pre-Deployment

### Environment Variables
- [ ] Copy `.env.example` to `.env` in backend directory
- [ ] Copy `.env.example` to `.env` in frontend directory
- [ ] Generate secure `SECRET_KEY` using: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Set strong MongoDB password
- [ ] Set strong Redis password
- [ ] Configure all required API keys:
  - [ ] Supabase URL and keys
  - [ ] Paystack keys (use live keys for production)
  - [ ] Google Maps API key
  - [ ] PostHog API key
  - [ ] GlitchTip DSN

### Database
- [ ] Set up MongoDB instance (Atlas or self-hosted)
- [ ] Set up Redis instance
- [ ] Run database migrations: `python -m scripts.migrations.migrate --up`
- [ ] (Optional) Seed database: `python -m scripts.seed_database`

### SSL/TLS
- [ ] Obtain SSL certificates (Let's Encrypt recommended)
- [ ] Configure nginx with SSL
- [ ] Set up automatic certificate renewal

### Security
- [ ] Enable MongoDB authentication
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Configure CORS origins (no wildcards in production)
- [ ] Review and update security headers

## Deployment

### Render (Recommended)
1. [ ] Create Render account
2. [ ] Connect GitHub repository
3. [ ] Create new Blueprint from `deployment/render.yaml`
4. [ ] Set all environment variables
5. [ ] Deploy and verify health checks

### Vercel (Frontend)
1. [ ] Install Vercel CLI: `npm i -g vercel`
2. [ ] Run `vercel --prod` from frontend directory
3. [ ] Configure environment variables in Vercel dashboard
4. [ ] Verify deployment

### Self-Hosted (Docker)
1. [ ] Copy `deployment/docker-compose.prod.yml` to server
2. [ ] Create `.env` file with production values
3. [ ] Run: `docker-compose -f docker-compose.prod.yml up -d`
4. [ ] Verify all containers are healthy
5. [ ] Run migrations inside container

## Post-Deployment

### Verification
- [ ] Check health endpoint: `GET /health`
- [ ] Test API documentation: `GET /docs`
- [ ] Verify frontend loads
- [ ] Test authentication flow
- [ ] Test payment flow (use test cards)
- [ ] Test delivery tracking

### Monitoring
- [ ] Verify GlitchTip is receiving errors
- [ ] Verify PostHog is tracking events
- [ ] Set up alerts for health check failures
- [ ] Monitor resource usage

### Backup
- [ ] Configure MongoDB backups
- [ ] Test backup restoration
- [ ] Document backup schedule

### Documentation
- [ ] Update API documentation
- [ ] Document deployment URLs
- [ ] Update team on deployment status

## Rollback Plan

If deployment fails:
1. [ ] Check logs: `docker-compose logs backend`
2. [ ] Verify environment variables
3. [ ] Check database connectivity
4. [ ] Rollback to previous version if needed
5. [ ] Notify team of issues

## Emergency Contacts

- **Backend Issues**: backend-team@ihhashi.co.za
- **Frontend Issues**: frontend-team@ihhashi.co.za
- **Infrastructure**: devops@ihhashi.co.za
