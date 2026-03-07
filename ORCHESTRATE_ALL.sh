#!/bin/bash
# MASTER ORCHESTRATOR
# Runs ALL agents in tandem to acquire resources

echo "🔥 MASTER ORCHESTRATOR: Activating all agents"
echo "================================================"

# Function to run agent with logging
run_agent() {
  local name=$1
  local path=$2
  local log_file="/tmp/agent-${name}.log"
  
  echo "▶️  Starting ${name}..."
  bun run "${path}" > "${log_file}" 2>&1 &
  echo "   PID: $! | Log: ${log_file}"
}

# 1. Deploy 8 Elite Squad agents
echo -e "\n📦 ELITE SQUAD (8 agents)"
run_agent "captain" "./captain/index.ts"
run_agent "meta-router" "./meta-router/index.ts"
run_agent "architect" "./architect/index.ts"
run_agent "frontend" "./frontend/index.ts"
run_agent "backend" "./backend/index.ts"
run_agent "guardian" "./guardian/index.ts"
run_agent "devops" "./devops/index.ts"
run_agent "evolution" "./evolution/index.ts"

# 2. Deploy 5 Resource Acquisition sub-agents
echo -e "\n🎯 RESOURCE ACQUISITION (5 agents)"
run_agent "keystore-manager" "./sub-agents/keystore-manager/agent.ts"
run_agent "play-store-api" "./sub-agents/play-store-api/agent.ts"
run_agent "render-deploy" "./sub-agents/render-deploy/agent.ts"
run_agent "ios-certificate" "./sub-agents/ios-certificate/agent.ts"
run_agent "health-check" "./sub-agents/health-check/agent.ts"

# 3. Deploy infrastructure
echo -e "\n🏗️  INFRASTRUCTURE"
run_agent "cost-guardian" "./cost-tracking/guardian.ts"
run_agent "auto-scaler" "./infrastructure/monitoring/auto-scaler.ts"
run_agent "dashboard" "./dashboard/server.ts"

# 4. Bridge connector
echo -e "\n🔗 BRIDGE CONNECTOR"
run_agent "bridge" "./bridge-connector.ts"

echo -e "\n✅ ALL AGENTS DEPLOYED"
echo "📊 Total: 17 agents running in tandem"
echo "🎯 Mission: Acquire all missing resources"
echo ""
echo "📋 Monitor logs:"
echo "   tail -f /tmp/agent-*.log"
echo ""
echo "🌐 Dashboard:"
echo "   http://localhost:3000"
echo ""
echo "💰 Cost Status:"
echo "   http://localhost:7777/status"
echo ""
echo "🏥 Health Check:"
echo "   http://localhost:9999/healthz"
