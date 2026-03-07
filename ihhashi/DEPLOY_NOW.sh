#!/bin/bash
# Complete iHhashi Deployment Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   iHhashi Auto-Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check Railway login
echo -e "${BLUE}Checking Railway authentication...${NC}"
if ! railway whoami &>/dev/null; then
    echo -e "${RED}❌ Not logged into Railway${NC}"
    echo "   Run: railway login"
    exit 1
fi
echo -e "${GREEN}✓ Railway authenticated${NC}"

echo ""

# ===============================
# BACKEND DEPLOYMENT
# ===============================
echo -e "${BLUE}>>> Deploying Backend to Railway...${NC}"
cd /home/teacherchris37/backend

# Check if linked to project
if [ ! -f .railway/config.json ] 2>/dev/null; then
    echo -e "${YELLOW}Linking to Railway project...${NC}"
    railway link
fi

# Deploy
echo -e "${YELLOW}Deploying backend...${NC}"
railway up

# Get domain
RAILWAY_URL=$(railway domain 2>/dev/null || echo "")
if [ -z "$RAILWAY_URL" ]; then
    echo -e "${RED}❌ Could not get Railway domain${NC}"
    echo "   Check dashboard: https://railway.app/dashboard"
    exit 1
fi

echo -e "${GREEN}✓ Backend deployed: https://$RAILWAY_URL${NC}"
echo ""
read -p "Press Enter to continue to frontend deployment..."
echo ""

# ===============================
# FRONTEND DEPLOYMENT  
# ===============================
echo -e "${BLUE}>>> Deploying Frontend to Netlify...${NC}"
cd /home/teacherchris37/frontend

# Temporarily rename netlify.toml to avoid parsing issues
if [ -f netlify.toml ]; then
    mv netlify.toml netlify.toml.bak
    echo -e "${YELLOW}Temporarily moved netlify.toml${NC}"
fi

# Create env file with Railway URL
echo -e "${YELLOW}Setting up frontend environment...${NC}"
cat > .env.local << EOF
VITE_API_URL=https://$RAILWAY_URL
VITE_APP_ENV=production
EOF

echo -e "${GREEN}✓ Created .env.local with API URL${NC}"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
if [ ! -d node_modules ]; then
    npm ci --legacy-peer-deps 2>&1 | tail -5
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
fi

# Build
echo -e "${YELLOW}Building frontend...${NC}"
rm -rf dist
npm run build 2>&1 | tail -10

if [ ! -d dist ]; then
    echo -e "${RED}❌ Build failed - dist folder not found${NC}"
    # Restore netlify.toml
    mv netlify.toml.bak netlify.toml 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Build successful${NC}"

# Check if linked to site
NETLIFY_SITE=$(netlify status 2>&1 || echo "")
if echo "$NETLIFY_SITE" | grep -q "Not linked"; then
    echo -e "${YELLOW}Linking to Netlify site...${NC}"
    netlify link
fi

# Deploy
echo -e "${YELLOW}Deploying to Netlify...${NC}"
netlify deploy --prod --dir=dist

# Restore netlify.toml
mv netlify.toml.bak netlify.toml 2>/dev/null || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Your URLs:${NC}"
echo -e "  🚀 Backend:  https://$RAILWAY_URL"
echo ""

# Try to get Netlify URL
NETLIFY_URL=$(netlify status --json 2>/dev/null | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
if [ -n "$NETLIFY_URL" ]; then
    echo -e "  🌐 Frontend: $NETLIFY_URL"
else
    echo -e "  🌐 Frontend: [Check Netlify dashboard]"
fi

echo ""
echo -e "${YELLOW}⚠️  IMPORTANT NEXT STEP:${NC}"
echo "   Update CORS_ORIGINS in Railway with your Netlify URL!"
echo ""
echo "   1. Go to: https://railway.app/dashboard"
echo "   2. Select your project → Variables tab"
echo "   3. Add: CORS_ORIGINS=$NETLIFY_URL"
echo "   4. Redeploy: cd backend && railway up"
echo ""
echo -e "${BLUE}Test your deployment:${NC}"
echo "   curl https://$RAILWAY_URL/health"
echo ""
