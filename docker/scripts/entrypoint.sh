#!/bin/bash
# =============================================================================
# MasterBuilder7 MCP Server Entrypoint
# Handles different server modes and initialization
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Default values
APP_HOME=${APP_HOME:-/app}
MCP_SERVER_HOST=${MCP_SERVER_HOST:-0.0.0.0}
MCP_SERVER_PORT=${MCP_SERVER_PORT:-8080}
MCP_HTTP_PORT=${MCP_HTTP_PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-INFO}

log_info "MasterBuilder7 MCP Server Entrypoint"
log_info "Working directory: $APP_HOME"
log_info "Environment: ${ENVIRONMENT:-production}"

# Change to app directory
cd "$APP_HOME"

# Function to wait for dependencies
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

# Wait for database if URL is provided
if [ -n "$DATABASE_URL" ]; then
    # Extract host and port from DATABASE_URL
    if [[ $DATABASE_URL =~ @([^:/]+):?([0-9]+)? ]]; then
        DB_HOST="${BASH_REMATCH[1]}"
        DB_PORT="${BASH_REMATCH[2]:-5432}"
        wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" || exit 1
    fi
fi

# Wait for Redis if URL is provided
if [ -n "$REDIS_URL" ]; then
    # Extract host and port from REDIS_URL
    if [[ $REDIS_URL =~ redis://([^:/]+):?([0-9]+)? ]]; then
        REDIS_HOST="${BASH_REMATCH[1]}"
        REDIS_PORT="${BASH_REMATCH[2]:-6379}"
        wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" || exit 1
    fi
fi

# Run database migrations if needed
if [ "${RUN_MIGRATIONS:-false}" = "true" ] && [ -d "apex/infrastructure" ]; then
    log_info "Running database migrations..."
    python -m alembic upgrade head || log_warn "Migration failed or not configured"
fi

# Create necessary directories
mkdir -p "$APP_HOME/logs" "$APP_HOME/data" "$APP_HOME/checkpoints"

# Function to handle shutdown
shutdown_handler() {
    log_warn "Received shutdown signal, stopping gracefully..."
    if [ -n "$SERVER_PID" ]; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    exit 0
}

trap shutdown_handler SIGTERM SIGINT

# Main command handler
case "${1:-http-server}" in
    "stdio-server")
        log_info "Starting MCP STDIO Server..."
        exec python mcp_server.py
        ;;
        
    "http-server")
        log_info "Starting MCP HTTP Server on $MCP_SERVER_HOST:$MCP_HTTP_PORT..."
        if [ "$ENVIRONMENT" = "development" ]; then
            exec uvicorn mcp_http_server:app \
                --host "$MCP_SERVER_HOST" \
                --port "$MCP_HTTP_PORT" \
                --reload \
                --log-level debug \
                --access-log
        else
            exec uvicorn mcp_http_server:app \
                --host "$MCP_SERVER_HOST" \
                --port "$MCP_HTTP_PORT" \
                --workers "${UVICORN_WORKERS:-4}" \
                --log-level "${LOG_LEVEL,,}" \
                --access-log
        fi
        ;;
        
    "secure-http-server")
        log_info "Starting Secure MCP HTTP Server on $MCP_SERVER_HOST:$MCP_HTTP_PORT..."
        exec uvicorn mcp_http_server_secure:app \
            --host "$MCP_SERVER_HOST" \
            --port "$MCP_HTTP_PORT" \
            --workers "${UVICORN_WORKERS:-4}" \
            --ssl-keyfile "${SSL_KEY_PATH:-/etc/ssl/private/mb7.key}" \
            --ssl-certfile "${SSL_CERT_PATH:-/etc/ssl/certs/mb7.crt}" \
            --log-level "${LOG_LEVEL,,}"
        ;;
        
    "dev-server")
        log_info "Starting Development Server with hot reload and debugging..."
        # Start debugpy if DEBUG_PORT is set
        if [ -n "$DEBUG_PORT" ]; then
            log_info "Debugpy listening on port $DEBUG_PORT"
            python -m debugpy --listen "0.0.0.0:$DEBUG_PORT" --wait-for-client -m uvicorn mcp_http_server:app \
                --host "$MCP_SERVER_HOST" \
                --port "$MCP_HTTP_PORT" \
                --reload \
                --log-level debug &
        else
            exec uvicorn mcp_http_server:app \
                --host "$MCP_SERVER_HOST" \
                --port "$MCP_HTTP_PORT" \
                --reload \
                --log-level debug \
                --access-log
        fi
        ;;
        
    "client")
        log_info "Starting MCP Client..."
        exec python mcp_client.py "${@:2}"
        ;;
        
    "shell"|"bash"|"sh")
        log_info "Starting interactive shell..."
        exec /bin/bash
        ;;
        
    "python")
        log_info "Starting Python..."
        exec python "${@:2}"
        ;;
        
    "migrate")
        log_info "Running database migrations..."
        exec python -m alembic upgrade head
        ;;
        
    "test")
        log_info "Running tests..."
        exec pytest "${@:2}"
        ;;
        
    *)
        log_info "Executing custom command: $@"
        exec "$@"
        ;;
esac
