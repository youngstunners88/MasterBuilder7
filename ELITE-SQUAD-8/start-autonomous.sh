#!/bin/bash
# Start 8-Agent Elite Squad Autonomous Operation

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        🚀 STARTING ELITE SQUAD AUTONOMOUS OPERATION            ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo ""

# Start n8n if available
if command -v n8n &> /dev/null; then
    echo "📊 Starting n8n dashboard..."
    n8n start &
    echo "   Dashboard: http://localhost:5678"
else
    echo "⚠️  n8n not installed. Install with: npm install -g n8n"
fi

echo ""
echo "🦀 Starting 8 Elite Agents..."
echo ""

# Start the orchestrator
python3 /home/teacherchris37/MasterBuilder7/ELITE-SQUAD-8/orchestrator.py &
ORCH_PID=$!
echo "   Orchestrator PID: $ORCH_PID"

echo ""
echo "✅ Elite Squad Autonomous Operation Active!"
echo ""
echo "Commands:"
echo "  tail -f /tmp/elite-squad.log     # View logs"
echo "  kill $ORCH_PID                   # Stop orchestrator"
echo "  pkill -f n8n                     # Stop n8n"
echo ""
echo "Press Ctrl+C to stop all"
echo ""

# Wait
wait $ORCH_PID
