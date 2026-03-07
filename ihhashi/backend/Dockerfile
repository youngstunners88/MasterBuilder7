# Backend Dockerfile for iHhashi
# Multi-stage build for optimized production image

# ============================================
# Build Stage
# ============================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Production Stage
# ============================================
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r ihhashi && useradd -r -g ihhashi -s /bin/bash ihhashi

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs && \
    chown -R ihhashi:ihhashi /app

# Copy application code
COPY --chown=ihhashi:ihhashi . .

# Switch to non-root user
USER ihhashi

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Expose port
EXPOSE 8000

# Health check - matches Railway healthcheckPath
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
# Railway provides PORT env var; default to 8000 for local
# Use --workers based on available CPUs (Railway sets this via WORKERS env var)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-2} --proxy-headers"]

# ============================================
# Development Stage (for local development)
# ============================================
FROM builder as development

WORKDIR /app

# Install additional dev dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black ruff httpx

# Copy application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Run with auto-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
