#!/bin/bash
# YOLO Mode Launcher for MasterBuilder7
# Runs ZO1 and ZO2 computers in full autonomous build mode

set -e

PROJECT_PATH="${1:-.}"
SAFETY_THRESHOLD="${2:-0.6}"
MAX_AGENTS="${3:-64}"

echo "🔥 MASTERBUILDER7 YOLO MODE 🔥"
echo "=============================="
echo "Project: $PROJECT_PATH"
echo "Safety Threshold: $SAFETY_THRESHOLD"
echo "Max Agents: $MAX_AGENTS"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Check if we're in the right directory
if [ ! -f "yolo_orchestrator.py" ]; then
    echo "❌ Error: Not in MasterBuilder7 directory"
    exit 1
fi

echo "🚀 Starting YOLO Build..."
echo "   ZO1: ONLINE"
echo "   ZO2: ONLINE"
echo ""

# Run YOLO orchestrator
python3 yolo_orchestrator.py "$PROJECT_PATH" --safety "$SAFETY_THRESHOLD" --agents "$MAX_AGENTS"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ YOLO Build Complete!"
else
    echo "❌ YOLO Build Failed!"
fi

exit $EXIT_CODE
