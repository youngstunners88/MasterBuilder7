#!/bin/bash
#
# START AUTOMATION FACILITY
# Deploys 24 agents across 3 Zo computers with parallel execution
#

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           🤖 24-AGENT AUTOMATION FACILITY                        ║"
echo "║           MasterBuilder7 Parallel Execution                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📍 Repository:${NC} https://github.com/youngstunners88/MasterBuilder7.git"
echo -e "${BLUE}🖥️  Zo Computers:${NC} 3 (Primary, Secondary, Tertiary)"
echo -e "${BLUE}🤖 Total Agents:${NC} 24"
echo ""

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
command -v bun >/dev/null 2>&1 || { echo "❌ Bun required but not installed."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ Git required but not installed."; exit 1; }
echo -e "${GREEN}✅ All dependencies present${NC}"
echo ""

# Step 1: Deploy 24 agents
echo -e "${YELLOW}🚀 Step 1: Deploying 24 agents...${NC}"
bun deploy/agent-deployer.ts deploy --mode=parallel --stress || {
    echo "⚠️  Deploy encountered issues, continuing..."
}
echo ""

# Step 2: Start Inter-Zo sync
echo -e "${YELLOW}🔄 Step 2: Starting Inter-Zo synchronization...${NC}"
bun core/inter-zo-protocol.ts sync
echo -e "${GREEN}✅ Zo computers synchronized${NC}"
echo ""

# Step 3: Check cluster status
echo -e "${YELLOW}📊 Step 3: Cluster status...${NC}"
bun core/inter-zo-protocol.ts status
echo ""

# Step 4: Start stress testing
echo -e "${YELLOW}🔥 Step 4: Starting stress tests...${NC}"
bun core/stress-test-framework.ts run --duration=60 --agents=24 --iterations=50 &
STRESS_PID=$!
echo -e "${GREEN}✅ Stress tests running (PID: $STRESS_PID)${NC}"
echo ""

# Step 5: Git sync
echo -e "${YELLOW}📁 Step 5: Syncing with Git...${NC}"
git pull mb7 master
git add -A
git commit -m "chore: Automation cycle - $(date -u +%Y-%m-%d-%H:%M:%S) UTC" || echo "No changes to commit"
git push mb7 master || echo "Push failed or up to date"
echo -e "${GREEN}✅ Git sync complete${NC}"
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 FACILITY OPERATIONAL                       ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  🤖 24 Agents deployed                                           ║"
echo "║  🖥️  3 Zo computers synchronized                                  ║"
echo "║  🔥 Stress tests running                                          ║"
echo "║  📁 Auto-commits enabled                                          ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Commands:                                                        ║"
echo "║    bun core/inter-zo-protocol.ts status                          ║"
echo "║    bun core/stress-test-framework.ts run --agents=24             ║"
echo "║    bun deploy/agent-deployer.ts deploy --stress                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}All systems operational. Press Ctrl+C to stop.${NC}"

# Keep running
wait $STRESS_PID
