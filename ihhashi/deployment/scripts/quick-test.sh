#!/bin/bash
# Quick test deployment with minimal requirements
# This creates a test build to verify everything works

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== iHhashi Quick Test Deployment ===${NC}"
echo ""

# Backend test
echo -e "${BLUE}Testing Backend Build...${NC}"
cd /home/teacherchris37/backend

# Create a minimal .env for testing if not exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating minimal .env for testing...${NC}"
    cat > .env << 'EOF'
MONGODB_URL=mongodb://localhost:27017/ihhashi
SECRET_KEY=test-secret-key-not-for-production
ENVIRONMENT=development
DEBUG=true
EOF
fi

# Test Python imports
echo -e "${BLUE}Testing Python imports...${NC}"
python3 -c "from app.main import app; print('✓ Backend imports work')" 2>/dev/null || {
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt -q
    python3 -c "from app.main import app; print('✓ Backend imports work')"
}

echo ""

# Frontend test  
echo -e "${BLUE}Testing Frontend Build...${NC}"
cd /home/teacherchris37/frontend

# Check for node_modules
if [ ! -d node_modules ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps
fi

# Create minimal env for testing
if [ ! -f .env.local ] && [ ! -f .env.production ]; then
    echo -e "${YELLOW}Creating test environment file...${NC}"
    cat > .env.local << 'EOF'
VITE_API_URL=http://localhost:8000
EOF
fi

# Try to build
echo -e "${BLUE}Building frontend...${NC}"
rm -rf dist
if npm run build; then
    echo -e "${GREEN}✓ Frontend build successful${NC}"
    echo "  dist/ directory created"
else
    echo -e "${RED}✗ Frontend build failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== All Tests Passed ===${NC}"
echo ""
echo -e "${YELLOW}To deploy to production:${NC}"
echo "  1. Backend: ./deployment/scripts/deploy-railway.sh"
echo "  2. Frontend: ./deployment/scripts/deploy-netlify.sh"
echo ""
echo -e "${YELLOW}Or run full deployment:${NC}"
echo "  ./deployment/scripts/deploy-all.sh"
