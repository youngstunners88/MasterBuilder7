# Frontend Dockerfile for iHhashi
# Multi-stage build for optimized production image

# ============================================
# Build Stage
# ============================================
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies first (for better caching)
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Build arguments for environment variables
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_POSTHOG_KEY
ARG VITE_POSTHOG_HOST
ARG VITE_GOOGLE_MAPS_API_KEY
ARG VITE_PAYSTACK_PUBLIC_KEY
ARG VITE_SENTRY_DSN
ARG VITE_APP_ENV=production
ARG VITE_APP_VERSION

# Set environment variables for build
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY} \
    VITE_POSTHOG_KEY=${VITE_POSTHOG_KEY} \
    VITE_POSTHOG_HOST=${VITE_POSTHOG_HOST} \
    VITE_GOOGLE_MAPS_API_KEY=${VITE_GOOGLE_MAPS_API_KEY} \
    VITE_PAYSTACK_PUBLIC_KEY=${VITE_PAYSTACK_PUBLIC_KEY} \
    VITE_SENTRY_DSN=${VITE_SENTRY_DSN} \
    VITE_APP_ENV=${VITE_APP_ENV} \
    VITE_APP_VERSION=${VITE_APP_VERSION}

# Build the application
RUN npm run build

# ============================================
# Production Stage (Nginx)
# ============================================
FROM nginx:alpine as production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create cache directories
RUN mkdir -p /var/cache/nginx /var/run /var/log/nginx && \
    chown -R nginx:nginx /var/cache/nginx /var/run /var/log/nginx /usr/share/nginx/html

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
