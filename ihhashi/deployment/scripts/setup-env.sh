#!/bin/bash
# Setup environment variables for iHhashi deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== iHhashi Environment Setup ===${NC}"
echo ""

# Function to ask for input
ask_var() {
    local var_name=$1
    local var_desc=$2
    local default_val=$3
    
    echo -e "${BLUE}$var_name${NC}: $var_desc"
    if [ -n "$default_val" ]; then
        read -p "Enter value (default: $default_val): " value
        value=${value:-$default_val}
    else
        read -p "Enter value: " value
    fi
    echo "$var_name=$value"
    echo ""
}

echo -e "${YELLOW}=== Backend Environment Variables ===${NC}"
echo "These will be set in Railway Dashboard"
echo ""

# MongoDB URL
ask_var "MONGODB_URL" "Your MongoDB connection string" ""

# Secret key
SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
echo -e "${BLUE}SECRET_KEY${NC}: Auto-generated (copy this)"
echo "SECRET_KEY=$SECRET_KEY"
echo ""

# Supabase settings
ask_var "SUPABASE_URL" "Your Supabase project URL" ""
ask_var "SUPABASE_ANON_KEY" "Your Supabase anon/public key" ""
ask_var "SUPABASE_SERVICE_ROLE_KEY" "Your Supabase service role key" ""

# CORS Origins
echo -e "${BLUE}CORS_ORIGINS${NC}: Frontend URLs allowed to access the API"
echo "Example: https://ihhashi.netlify.app,https://app.ihhashi.com"
ask_var "CORS_ORIGINS" "Comma-separated list of frontend URLs" ""

echo ""
echo -e "${YELLOW}=== Frontend Environment Variables ===${NC}"
echo "These will be set in Netlify Dashboard or .env.local"
echo ""

# Get Railway URL for API
ask_var "VITE_API_URL" "Your Railway backend URL" "https://your-app.up.railway.app"

echo ""
echo -e "${GREEN}=== Summary ===${NC}"
echo ""
echo -e "${YELLOW}Backend (Railway):${NC}"
echo "  1. Go to: https://railway.app/dashboard"
echo "  2. Select your project"
echo "  3. Go to Variables tab"
echo "  4. Add the environment variables above"
echo ""
echo -e "${YELLOW}Frontend (Netlify):${NC}"
echo "  1. Go to: https://app.netlify.com"
echo "  2. Select your site"
echo "  3. Go to Site Settings > Environment Variables"
echo "  4. Add VITE_API_URL and Supabase variables"
echo ""
echo -e "${GREEN}Or create frontend/.env.local with:${NC}"
cat << EOF
VITE_API_URL=https://your-railway-url.up.railway.app
VITE_SUPABASE_URL=$SUPABASE_URL
VITE_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
EOF
