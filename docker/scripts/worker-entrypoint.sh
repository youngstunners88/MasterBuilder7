#!/bin/bash
# =============================================================================
# MasterBuilder7 Agent Worker Entrypoint
# Handles different worker modes
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
APP_HOME=${APP_HOME:-/app}
WORKER_TYPE=${WORKER_TYPE:-agent}
WORKER_CONCURRENCY=${WORKER_CONCURRENCY:-4}
LOG_LEVEL=${LOG_LEVEL:-INFO}

cd "$APP_HOME"

log_info "MasterBuilder7 Agent Worker Entrypoint"
log_info "Worker Type: $WORKER_TYPE"
log_info "Concurrency: $WORKER_CONCURRENCY"

# Wait for dependencies
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=${4:-30}
    
    log_info "Waiting for $service_name at $host:$port..."
    
    attempt=1
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            log_error "$service_name is not available after $max_attempts attempts"
            return 1
        fi
        log_warn "Attempt $attempt/$max_attempts: $service_name not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_success "$service_name is ready!"
    return 0
}

# Wait for Redis
if [ -n "$REDIS_URL" ]; then
    if [[ $REDIS_URL =~ redis://([^:/]+):?([0-9]+)? ]]; then
        REDIS_HOST="${BASH_REMATCH[1]}"
        REDIS_PORT="${BASH_REMATCH[2]:-6379}"
        wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" || exit 1
    fi
fi

# Wait for Database
if [ -n "$DATABASE_URL" ]; then
    if [[ $DATABASE_URL =~ @([^:/]+):?([0-9]+)? ]]; then
        DB_HOST="${BASH_REMATCH[1]}"
        DB_PORT="${BASH_REMATCH[2]:-5432}"
        wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" || exit 1
    fi
fi

# Wait for MCP Server if worker depends on it
if [ -n "$MCP_SERVER_URL" ]; then
    log_info "Checking MCP Server availability..."
    # Extract host from URL
    if [[ $MCP_SERVER_URL =~ http://([^:/]+) ]]; then
        MCP_HOST="${BASH_REMATCH[1]}"
        wait_for_service "$MCP_HOST" "8080" "MCP Server" || log_warn "MCP Server not available, continuing..."
    fi
fi

# Shutdown handler
shutdown_handler() {
    log_warn "Received shutdown signal, stopping worker gracefully..."
    if [ -n "$WORKER_PID" ]; then
        kill -TERM "$WORKER_PID" 2>/dev/null || true
        wait "$WORKER_PID" 2>/dev/null || true
    fi
    exit 0
}

trap shutdown_handler SIGTERM SIGINT

# Main command handler
case "${1:-agent-worker}" in
    "agent-worker")
        log_info "Starting Agent Worker (concurrency: $WORKER_CONCURRENCY)..."
        
        # Import and run the agent worker loop
        exec python -c "
import asyncio
import sys
sys.path.insert(0, '$APP_HOME')

from apex.agents.task_queue import WorkerPool

async def main():
    pool = WorkerPool(concurrency=$WORKER_CONCURRENCY)
    await pool.start()

if __name__ == '__main__':
    asyncio.run(main())
"
        ;;
        
    "celery-worker")
        log_info "Starting Celery Worker..."
        CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://redis:6379/1}
        CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://redis:6379/2}
        CELERY_QUEUE=${CELERY_QUEUE:-default}
        CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-INFO}
        
        exec celery -A apex.agents.task_queue worker \
            --loglevel="${CELERY_LOG_LEVEL,,}" \
            --concurrency="$WORKER_CONCURRENCY" \
            --queues="$CELERY_QUEUE" \
            --hostname="worker@%h" \
            --without-gossip \
            --without-mingle \
            --without-heartbeat \
            -Ofair
        ;;
        
    "flower")
        log_info "Starting Flower Monitor..."
        CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://redis:6379/1}
        FLOWER_PORT=${FLOWER_PORT:-5555}
        
        if [ -n "$FLOWER_BASIC_AUTH" ]; then
            exec celery -A apex.agents.task_queue flower \
                --port="$FLOWER_PORT" \
                --broker="$CELERY_BROKER_URL" \
                --basic_auth="$FLOWER_BASIC_AUTH"
        else
            exec celery -A apex.agents.task_queue flower \
                --port="$FLOWER_PORT" \
                --broker="$CELERY_BROKER_URL"
        fi
        ;;
        
    "shell"|"bash"|"sh")
        log_info "Starting interactive shell..."
        exec /bin/bash
        ;;
        
    "python")
        log_info "Starting Python..."
        exec python "${@:2}"
        ;;
        
    *)
        log_info "Executing custom command: $@"
        exec "$@"
        ;;
esac
