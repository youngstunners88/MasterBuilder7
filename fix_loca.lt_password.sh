#!/bin/bash
# Fix LocalTunnel Password Issue

echo "🔑 Getting LocalTunnel Password..."
echo ""

# Method 1: Get password via curl (run this on your Google VM)
echo "Method 1: Run this command on your Google VM:"
echo "  curl https://loca.lt/mytunnelpassword"
echo ""

# Actually get it
PASSWORD=$(curl -s https://loca.lt/mytunnelpassword)
echo "Your current IP: $PASSWORD"
echo ""

echo "Give this password to ChatGPT: $PASSWORD"
echo ""

echo "⚠️  NOTE: LocalTunnel passwords change frequently!"
echo "   Better alternatives that don't need passwords:"
echo ""
echo "1. Ngrok (recommended):"
echo "   ngrok http 8000"
echo "   # No password required!"
echo ""
echo "2. Cloudflare Tunnel:"
echo "   cloudflared tunnel run mcp-server"
echo "   # No password required!"
echo ""
