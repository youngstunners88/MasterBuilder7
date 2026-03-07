#!/bin/bash
# Setup Zo Computer Bridge for APEX Fleet
# Run this to enable tandem operation

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Setting Up APEX Fleet ↔ Zo Computer Bridge            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create directories
mkdir -p ~/.config/kimi/skills/zo-bridge
mkdir -p /var/log/apex-zo

# Copy skill files
cp -r .config/kimi/skills/zo-bridge/* ~/.config/kimi/skills/zo-bridge/ 2>/dev/null || true

# Copy APEX connector
cp apex/zo-connector.ts ~/MasterBuilder7/apex/ 2>/dev/null || true

# Make scripts executable
chmod +x ~/.config/kimi/skills/zo-bridge/zo.sh
chmod +x ~/MasterBuilder7/apex/zo-connector.ts 2>/dev/null || true

echo "✅ Bridge files installed"

# Test connection
echo ""
echo "Testing connection to Zo Computer..."
~/.config/kimi/skills/zo-bridge/zo.sh test

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Commands:"
echo "  ~/.config/kimi/skills/zo-bridge/zo.sh ask \"Hello Zo\""
echo "  ~/.config/kimi/skills/zo-bridge/zo.sh sync"
echo "  ~/.config/kimi/skills/zo-bridge/zo.sh daemon &"
echo ""
echo "Tandem Mode (from APEX Fleet):"
echo "  cd ~/MasterBuilder7/apex && bun run zo-connector.ts start &"
echo ""
echo "This enables:"
echo "  • Kimi CLI ↔ Zo bidirectional messaging"
echo "  • Task delegation between APEX and Zo"
echo "  • Shared context and state"
echo "  • 24/7 continuous operation"
