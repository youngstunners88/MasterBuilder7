#!/bin/bash
# Full deployment script for iHhashi (Backend + Frontend)
# Usage: ./deployment/scripts/full-deploy.sh [OPTIONS]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
SKIP_BACKEND=false
SKIP_FRONTEND=false
SETUP_ONLY=false
TEST_MODE=false
VERBOSE=false

# Parse arguments
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
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Deploy iHhashi backend (Railway) and frontend (Netlify)"
            echo ""
            echo "Options:"
            echo "  --skip-backend    Skip backend deployment to Railway"
            echo "  --skip-frontend   Skip frontend deployment to Netlify"
            echo "  --setup-only      Only show setup instructions"
            echo "  --test            Run quick test build before deploying"
            echo "  --verbose, -v     Show detailed output"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Full deployment"
            echo "  $0 --skip-frontend                    # Backend only"
            echo "  $0 --test                             # Test then deploy"
            echo "  $0 --skip-backend --verbose           # Frontend only with verbose output"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   iHhashi Full Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verbose mode
if [ "$VERBOSE" = true ]; then
    set -x
fi

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi
NODE_VERSION=$(node -v)
echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

echo ""

# Run test if requested
if [ "$TEST_MODE" = true ]; then
    echo -e "${BLUE}>>> Running quick test build...${NC}"
    if bash "$SCRIPT_DIR/quick-test.sh"; then
        echo ""
        read -p "Continue with deployment? (Y/n): " continue_deploy
        if [[ $continue_deploy =~ ^[Nn]$ ]]; then
            echo -e "${YELLOW}Deployment cancelled${NC}"
            exit 0
        fi
    else
        echo -e "${RED}Tests failed. Fix issues before deploying.${NC}"
        exit 1
    fi
    echo ""
fi

# Run setup if requested
if [ "$SETUP_ONLY" = true ]; then
    bash "$SCRIPT_DIR/setup-env.sh"
    exit 0
fi

# Track deployment status
BACKEND_STATUS="skipped"
FRONTEND_STATUS="skipped"

# Deploy Backend
if [ "$SKIP_BACKEND" = false ]; then
    echo -e "${BLUE}>>> Deploying Backend to Railway...${NC}"
    echo ""
    if bash "$SCRIPT_DIR/deploy-railway.sh"; then
        BACKEND_STATUS="success"
        echo ""
        echo -e "${GREEN}✓ Backend deployment complete${NC}"
    else
        BACKEND_STATUS="failed"
        echo ""
        echo -e "${RED}✗ Backend deployment failed${NC}"
        read -p "Continue with frontend deployment? (y/N): " continue_frontend
        if [[ ! $continue_frontend =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    echo ""
fi

# Deploy Frontend
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${BLUE}>>> Deploying Frontend to Netlify...${NC}"
    echo ""
    if bash "$SCRIPT_DIR/deploy-netlify.sh"; then
        FRONTEND_STATUS="success"
        echo ""
        echo -e "${GREEN}✓ Frontend deployment complete${NC}"
    else
        FRONTEND_STATUS="failed"
        echo ""
        echo -e "${RED}✗ Frontend deployment failed${NC}"
    fi
    echo ""
fi

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Deployment Process Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Deployment Status:"
echo -e "  Backend (Railway):  ${BACKEND_STATUS == "success" && echo -e "${GREEN}✓ $BACKEND_STATUS${NC}" || ( [ "$BACKEND_STATUS" == "failed" ] && echo -e "${RED}✗ $BACKEND_STATUS${NC}" || echo -e "${YELLOW}- $BACKEND_STATUS${NC}" )}"
echo -e "  Frontend (Netlify): ${FRONTEND_STATUS == "success" && echo -e "${GREEN}✓ $FRONTEND_STATUS${NC}" || ( [ "$FRONTEND_STATUS" == "failed" ] && echo -e "${RED}✗ $FRONTEND_STATUS${NC}" || echo -e "${YELLOW}- $FRONTEND_STATUS${NC}" )}"
echo ""

if [ "$BACKEND_STATUS" = "success" ]; then
    echo -e "${YELLOW}Next steps for backend:${NC}"
    echo "  1. Test your backend health endpoint:"
    echo "     curl https://your-railway-url.up.railway.app/health"
    echo ""
fi

if [ "$FRONTEND_STATUS" = "success" ]; then
    echo -e "${YELLOW}Next steps for frontend:${NC}"
    echo "  1. Visit your Netlify URL and verify everything works"
    echo ""
fi

if [ "$BACKEND_STATUS" = "success" ] && [ "$FRONTEND_STATUS" = "success" ]; then
    echo -e "${YELLOW}Important:${NC}"
    echo "  If you see CORS errors, update CORS_ORIGINS in Railway:"
    echo "    - Go to https://railway.app/dashboard"
    echo "    - Add your Netlify URL to CORS_ORIGINS"
    echo ""
fi

echo -e "${BLUE}Dashboards:${NC}"
echo "  Railway: https://railway.app/dashboard"
echo "  Netlify: https://app.netlify.com"
echo ""

# Exit with error if any deployment failed
if [ "$BACKEND_STATUS" = "failed" ] || [ "$FRONTEND_STATUS" = "failed" ]; then
    exit 1
fi
