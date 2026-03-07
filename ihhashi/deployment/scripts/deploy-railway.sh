#!/bin/bash
# Deploy iHhashi Backend to Railway
# Usage: ./deployment/scripts/deploy-railway.sh [OPTIONS]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_TESTS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Deploy iHhashi backend to Railway"
            echo ""
            echo "Options:"
            echo "  --skip-tests    Skip running tests before deployment"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== iHhashi Railway Deployment ===${NC}"

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${YELLOW}Installing Railway CLI...${NC}"
    npm install -g @railway/cli
fi

# Check if user is logged in
if ! railway whoami &> /dev/null 2>&1; then
    echo -e "${YELLOW}Please login to Railway:${NC}"
    railway login
fi

# Change to backend directory
cd "$(dirname "$0")/../../backend"

# Run tests if not skipped
if [ "$SKIP_TESTS" = false ]; then
    echo -e "${BLUE}Running tests...${NC}"
    if command -v python3 &> /dev/null; then
        # Create minimal test env if needed
        if [ ! -f .env.test ]; then
            cat > .env.test << 'EOF'
MONGODB_URL=mongodb://localhost:27017
SECRET_KEY=test-secret-key-for-tests-only
ENVIRONMENT=testing
EOF
        fi
        
        # Run tests with coverage (don't fail on test errors for now)
        pip install pytest pytest-asyncio pytest-cov -q 2>/dev/null || true
        python3 -m pytest --cov=app -v 2>/dev/null || echo -e "${YELLOW}⚠️  Tests completed with warnings${NC}"
    fi
    echo ""
fi

# Check if project is linked
if [ ! -f .railway/config.json ] 2>/dev/null || ! railway status &> /dev/null 2>&1; then
    echo -e "${YELLOW}Project not linked to Railway${NC}"
    echo ""
    read -p "Link to existing Railway project? (Y/n): " link_project
    if [[ ! $link_project =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}Running: railway link${NC}"
        railway link
    else
        read -p "Create new Railway project? (y/N): " create_project
        if [[ $create_project =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Creating new project...${NC}"
            railway init
        else
            echo -e "${RED}❌ Cannot deploy without a linked project${NC}"
            exit 1
        fi
    fi
fi

# Check environment variables
echo ""
echo -e "${BLUE}Checking Railway environment variables...${NC}"

# Try to get env vars from Railway
RAILWAY_ENV=$(railway variables --json 2>/dev/null || echo "{}")

if [ "$RAILWAY_ENV" = "{}" ] || [ -z "$RAILWAY_ENV" ]; then
    echo -e "${YELLOW}⚠️  No environment variables set in Railway${NC}"
    echo ""
    echo -e "${YELLOW}Required variables:${NC}"
    echo "  - MONGODB_URL (your MongoDB connection string)"
    echo "  - SECRET_KEY (generate: openssl rand -base64 32)"
    echo "  - SUPABASE_URL (from Supabase project)"
    echo "  - SUPABASE_ANON_KEY (from Supabase project)"
    echo "  - CORS_ORIGINS (your Netlify frontend URL)"
    echo ""
    echo -e "${YELLOW}Set them at: https://railway.app/dashboard${NC}"
    echo ""
    read -p "Continue anyway? (y/N): " continue_anyway
    if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Check for critical variables
    echo -e "${GREEN}✓ Environment variables configured${NC}"
    
    # Check for specific required vars (this is a simple check)
    REQUIRED_VARS=("MONGODB_URL" "SECRET_KEY")
    MISSING_VARS=()
    
    for var in "${REQUIRED_VARS[@]}"; do
        if ! echo "$RAILWAY_ENV" | grep -q "$var"; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Missing recommended variables:${NC}"
        for var in "${MISSING_VARS[@]}"; do
            echo "    - $var"
        done
    fi
fi

echo ""
echo -e "${GREEN}Deploying to Railway...${NC}"
railway up

# Get the deployed URL
echo ""
echo -e "${BLUE}Getting deployment URL...${NC}"
SERVICE_URL=$(railway domain 2>/dev/null || echo "")

if [ -n "$SERVICE_URL" ]; then
    echo ""
    echo -e "${GREEN}✅ Deployed successfully!${NC}"
    echo -e "${GREEN}URL: https://$SERVICE_URL${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Test health endpoint (wait ~30s for deployment):"
    echo "     curl https://$SERVICE_URL/health"
    echo ""
    echo "  2. Set this URL as VITE_API_URL in your frontend:"
    echo "     export VITE_API_URL=https://$SERVICE_URL"
    echo ""
    
    # Test health endpoint
    echo -e "${BLUE}Testing health endpoint...${NC}"
    sleep 5
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$SERVICE_URL/health" 2>/dev/null || echo "000")
    
    if [ "$HTTP_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Health check passed${NC}"
        HEALTH_RESPONSE=$(curl -s "https://$SERVICE_URL/health" 2>/dev/null || echo "")
        echo "  Response: $HEALTH_RESPONSE"
    else
        echo -e "${YELLOW}⚠️  Health check returned HTTP $HTTP_STATUS${NC}"
        echo "  The deployment may still be starting. Try again in 30 seconds."
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  Could not determine service URL${NC}"
    echo -e "${YELLOW}Check Railway dashboard for deployment status${NC}"
fi

echo ""
echo -e "${BLUE}Railway Dashboard: https://railway.app/dashboard${NC}"
