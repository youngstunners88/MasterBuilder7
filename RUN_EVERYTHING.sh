#!/bin/bash
# MasterBuilder7 - RUN EVERYTHING
# Continuous autonomous operation

echo "🔥 MasterBuilder7 Autonomous Mode"
echo "================================"

# Start n8n
export PATH="/root/.npm-global/bin:$PATH"
nohup n8n start > /tmp/n8n.log 2>&1 &
echo "✅ n8n started on :5678"

# Start 8 Elite Agents
cd /home/workspace/MasterBuilder7/agents
nohup bun run-8-agents-continuous.ts > /tmp/agents.log 2>&1 &
echo "✅ 8 Elite Agents running"

# Start bridge to Kimi CLI and other Zo
cd /home/workspace/MasterBuilder7/agents
nohup bun bridge-connector.ts > /tmp/bridge.log 2>&1 &
echo "✅ Tri-Zo bridge active"

# Start autonomous deployer
cd /home/workspace/MasterBuilder7
nohup bun AUTONOMOUS_DEPLOYER.ts > /tmp/deployer.log 2>&1 &
echo "✅ Autonomous deployer running"

echo ""
echo "🤖 All systems autonomous!"
echo "Logs: /tmp/n8n.log | /tmp/agents.log | /tmp/bridge.log | /tmp/deployer.log"
echo ""
echo "PIDs:"
ps aux | grep -E "n8n|bun.*agents|bun.*bridge|bun.*deployer" | grep -v grep | awk '{print $2, $11}'
