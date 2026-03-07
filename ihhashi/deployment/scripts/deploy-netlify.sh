#!/bin/bash
set -e

PROD_DEPLOY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            PROD_DEPLOY=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./deploy-netlify.sh [--prod]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== iHhashi Netlify Deployment ==="

if [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 18 ]; then
    echo "Warning: Node.js v18+ recommended"
fi

if ! command -v netlify > /dev/null 2>&1; then
    npm install -g netlify-cli
fi

cd "$(dirname "$0")/../../frontend"

if [ ! -d node_modules ]; then
    npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps
fi

# Check environment variables
VITE_API_URL=${VITE_API_URL:-}
if [ -z "$VITE_API_URL" ] && [ -f .env.local ]; then
    VITE_API_URL=$(grep "^VITE_API_URL=" .env.local 2>/dev/null | cut -d= -f2- || echo "")
fi

echo "Checking environment variables..."

if [ -z "$VITE_API_URL" ] || [ "$VITE_API_URL" = "http://localhost:8000" ]; then
    echo "  x VITE_API_URL not set or using localhost"
    if [ ! -f .env.local ]; then
        echo "VITE_API_URL=https://your-railway-app.up.railway.app" > .env.local
        echo "Created .env.local template"
    fi
    echo "Continue with build? y/N:"
    read -r continue_build
    if [[ ! $continue_build =~ ^[Yy]$ ]]; then
        echo "Please set VITE_API_URL and try again"
        exit 1
    fi
else
    echo "  + VITE_API_URL: $VITE_API_URL"
    export VITE_API_URL
fi

echo ""
echo "Building frontend..."
rm -rf dist
export VITE_APP_ENV=production
VITE_APP_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
export VITE_APP_VERSION
npm run build

if [ ! -d dist ]; then
    echo "Build failed"
    exit 1
fi

echo "Build successful"

if [ ! -f .netlify/state.json ]; then
    echo "Site not linked to Netlify"
    echo "Link to existing site? Y/n:"
    read -r link_site
    if [[ ! $link_site =~ ^[Nn]$ ]]; then
        netlify link
    else
        echo "Create new site? y/N:"
        read -r create_site
        if [[ $create_site =~ ^[Yy]$ ]]; then
            netlify sites:create
            netlify link
        else
            echo "Cannot deploy without linked site"
            exit 1
        fi
    fi
fi

echo ""
echo "Deploying to Netlify..."
if [ "$PROD_DEPLOY" = true ]; then
    netlify deploy --prod --dir=dist
else
    netlify deploy --dir=dist
fi

echo ""
echo "Frontend deployed!"
echo "Netlify: https://app.netlify.com"
echo "Railway: https://railway.app/dashboard"
