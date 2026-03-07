#!/bin/bash
# Full deployment script for iHhashi (Backend + Frontend)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   iHhashi Full Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Parse arguments
SKIP_BACKEND=false
SKIP_FRONTEND=false
SETUP_ONLY=false
TEST_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-backend)
            SKIP_BACKEND=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --setup-only)
            SETUP_ONLY=true
            shift
            ;;
        --test)
            TEST_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-backend    Skip backend deployment"
            echo "  --skip-frontend   Skip frontend deployment"
            echo "  --setup-only      Only show setup instructions"
            echo "  --test            Run quick test build first"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run test if requested
if [ "$TEST_MODE" = true ]; then
    echo -e "${BLUE}>>> Running quick test build...${NC}"
    bash "$SCRIPT_DIR/quick-test.sh"
    echo ""
    read -p "Continue with deployment? (Y/n): " continue_deploy
    if [[ $continue_deploy =~ ^[Nn]$ ]]; then
        exit 0
    fi
    echo ""
fi

# Run setup if requested
if [ "$SETUP_ONLY" = true ]; then
    bash "$SCRIPT_DIR/setup-env.sh"
    exit 0
fi

# Deploy Backend
if [ "$SKIP_BACKEND" = false ]; then
    echo -e "${BLUE}>>> Deploying Backend to Railway...${NC}"
    echo ""
    if bash "$SCRIPT_DIR/deploy-railway.sh"; then
        echo ""
        echo -e "${GREEN}✓ Backend deployment complete${NC}"
    else
        echo ""
        echo -e "${RED}✗ Backend deployment failed${NC}"
        read -p "Continue with frontend deployment? (y/N): " continue_frontend
        if [[ ! $continue_frontend =~ ^[Yy]$ ]]; then
            exit 1
        fi
        SKIP_FRONTEND=false
    fi
    echo ""
fi

# Deploy Frontend
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${BLUE}>>> Deploying Frontend to Netlify...${NC}"
    echo ""
    if bash "$SCRIPT_DIR/deploy-netlify.sh"; then
        echo ""
        echo -e "${GREEN}✓ Frontend deployment complete${NC}"
    else
        echo ""
        echo -e "${RED}✗ Frontend deployment failed${NC}"
        exit 1
    fi
    echo ""
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Deployment Process Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test your backend health endpoint:"
echo "     curl https://your-railway-url.up.railway.app/health"
echo ""
echo "  2. Visit your Netlify URL and verify everything works"
echo ""
echo "  3. If you see CORS errors, update CORS_ORIGINS in Railway:"
echo "     - Go to https://railway.app/dashboard"
echo "     - Add your Netlify URL to CORS_ORIGINS"
echo ""
echo -e "${BLUE}Dashboards:${NC}"
echo "  Railway: https://railway.app/dashboard"
echo "  Netlify: https://app.netlify.com"
echo ""
