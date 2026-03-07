#!/bin/bash
# YOLO Multi-AI Mode Launcher
# Runs ChatGPT, Grok, Kimi, Claude + all agents in parallel

set -e

PROJECT_PATH="${1:-.}"
SAFETY_THRESHOLD="${2:-0.6}"

echo "🔥 YOLO MULTI-AI MODE 🔥"
echo "========================"
echo "Project: $PROJECT_PATH"
echo "AIs: Kimi + ChatGPT + Grok + Claude"
echo "Agents: 64 max parallel"
echo "Safety: $SAFETY_THRESHOLD"
echo ""

source .venv/bin/activate

python3 apex/yolo_multi_ai.py "$PROJECT_PATH" --safety "$SAFETY_THRESHOLD"
