# MasterBuilder7 Docker Deployment

Complete Docker deployment infrastructure for MasterBuilder7 MCP Server and Agent Layer.

## Quick Start

```bash
cd /home/teacherchris37/MasterBuilder7/docker

# Development
make dev

# Production
make prod
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| mcp-server | 8080, 8000 | Main MCP API server |
| agent-workers | - | Scalable agent worker pool |
| celery-worker | - | Background task processing |
| flower | 5555 | Celery task monitor |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache/message broker |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Dashboards |
| nginx | 80, 443 | Reverse proxy |

## File Structure

```
docker/
├── docker-compose.yml           # Main compose file
├── docker-compose.prod.yml      # Production overrides
├── docker-compose.override.yml  # Development overrides
├── Dockerfile                   # Main application image
├── Dockerfile.agent             # Agent worker image
├── .dockerignore                # Build context exclusions
├── .env.example                 # Environment template
├── Makefile                     # Helper commands
├── nginx/                       # Nginx configuration
│   ├── nginx.conf
│   ├── nginx.prod.conf
│   ├── nginx.dev.conf
│   └── conf.d/
├── prometheus/                  # Prometheus configuration
│   ├── prometheus.yml
│   ├── prometheus.prod.yml
│   └── rules/
├── grafana/                     # Grafana configuration
│   ├── provisioning/
│   └── dashboards/
├── redis/                       # Redis configuration
│   └── redis.conf
├── init-scripts/                # Database init scripts
│   └── 01-init.sql
└── scripts/                     # Entrypoint scripts
    ├── entrypoint.sh
    └── worker-entrypoint.sh
```

## Usage

### Development

```bash
# Start with hot reload
make dev

# View logs
make logs

# Open shell
make shell

# Run tests
make test

# Stop
make dev-down
```

### Production

```bash
# Copy and edit environment file
cp .env.example .env
vim .env

# Deploy
make prod

# Check status
make status
```

### Docker Compose Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Scale workers
docker-compose up -d --scale agent-workers=5

# View logs
docker-compose logs -f mcp-server

# Execute commands
docker-compose exec mcp-server python -c "print('Hello')"
```

## Environment Variables

See `.env.example` for all available options.

### Required
- `API_KEY` - API authentication key
- `SECRET_KEY` - Application secret
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Optional
- `LOG_LEVEL` - Logging level (default: INFO)
- `UVICORN_WORKERS` - Number of workers (default: 4)
- `SENTRY_DSN` - Sentry error tracking

## Health Checks

All services include health checks:
- MCP Server: `http://localhost:8080/health`
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- Nginx: `http://localhost/health`

## Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Flower**: http://localhost:5555

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Reset everything
make clean-all
make dev
```

### Database connection issues
```bash
# Wait for postgres to be ready
docker-compose exec postgres pg_isready

# Run migrations manually
docker-compose exec mcp-server python -m alembic upgrade head
```

### Port conflicts
```bash
# Check what's using port 8080
lsof -i :8080

# Edit docker-compose.override.yml to change ports
```
