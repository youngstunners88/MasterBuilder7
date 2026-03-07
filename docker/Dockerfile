# =============================================================================
# MasterBuilder7 MCP Server - Multi-Stage Dockerfile
# Production-ready container for the MCP Server and Agent Layer
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# Install build dependencies and compile Python packages
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY apex/requirements.txt /build/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional MCP-specific dependencies
RUN pip install --no-cache-dir \
    mcp>=1.0.0 \
    httpx-sse>=0.4.0

# -----------------------------------------------------------------------------
# Stage 2: Production
# Minimal runtime image with only necessary dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    PYTHONPATH=/app

WORKDIR ${APP_HOME}

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    libssl3 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Create necessary directories
RUN mkdir -p ${APP_HOME}/logs ${APP_HOME}/data ${APP_HOME}/checkpoints && \
    chown -R appuser:appgroup ${APP_HOME}

# Copy application code
COPY --chown=appuser:appgroup apex/ ${APP_HOME}/apex/
COPY --chown=appuser:appgroup mcp_server.py ${APP_HOME}/
COPY --chown=appuser:appgroup mcp_http_server.py ${APP_HOME}/
COPY --chown=appuser:appgroup mcp_http_server_secure.py ${APP_HOME}/
COPY --chown=appuser:appgroup mcp_client.py ${APP_HOME}/
COPY --chown=appuser:appgroup mcp_config.json ${APP_HOME}/

# Copy entrypoint script
COPY --chown=appuser:appgroup docker/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080 8000

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["http-server"]

# -----------------------------------------------------------------------------
# Stage 3: Development
# Includes development tools and debugging capabilities
# -----------------------------------------------------------------------------
FROM production as development

USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    nano \
    htop \
    net-tools \
    iputils-ping \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    black \
    isort \
    flake8 \
    mypy \
    pytest \
    pytest-asyncio \
    debugpy

# Install additional debugging tools
RUN pip install --no-cache-dir \
    ipython \
    jupyter-console

USER appuser

# Override command for development
CMD ["dev-server"]
