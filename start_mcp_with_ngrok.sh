#!/bin/bash
# Start MCP Server with Ngrok Tunnel
# No password required!

cd /home/teacherchris37/MasterBuilder7

echo "🚀 Starting MasterBuilder7 MCP Server with Ngrok"
echo "================================================"
echo ""

# Check ngrok
if ! command -v ngrok &> /dev/null; then
    echo "❌ Ngrok not found. Installing..."
    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz -O /tmp/ngrok.tgz
    tar xzf /tmp/ngrok.tgz -C /tmp
    sudo mv /tmp/ngrok /usr/local/bin/
    echo "✅ Ngrok installed"
fi

# Check if token is configured
if ! grep -q "authtoken" ~/.config/ngrok/ngrok.yml 2>/dev/null; then
    echo "⚠️  Please run: ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

echo "✅ Ngrok configured"
echo ""

# Start MCP server in background
echo "🟢 Starting MCP server on port 8000..."
source .venv/bin/activate
python3 mcp_http_server.py &
MCP_PID=$!

# Wait for MCP to start
sleep 3

# Check if MCP started
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "❌ MCP server failed to start"
    exit 1
fi

echo "✅ MCP server running (PID: $MCP_PID)"
echo ""

# Start ngrok in background and capture output
echo "🌐 Starting Ngrok tunnel..."
echo "📡 Waiting for tunnel URL..."
echo ""

# Create temp file for ngrok output
NGROK_LOG=$(mktemp)
ngrok http 8000 --log=stdout > "$NGROK_LOG" 2>&1 &
NGROK_PID=$!

# Wait for URL to appear (up to 30 seconds)
for i in {1..30}; do
    URL=$(grep -o 'https://[a-z0-9-]*\.ngrok-free\.app' "$NGROK_LOG" | head -1)
    if [ ! -z "$URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$URL" ]; then
    echo "⚠️  Couldn't get URL automatically. Check manually:"
    echo "   http://localhost:4040"
    URL="$(grep -o 'https://[^[:space:]]*' "$NGROK_LOG" | head -1)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🎉 MCP SERVER READY!                                        ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo "║  📡 GIVE THIS URL TO CHATGPT/GROK:                           ║"
echo "║                                                              ║"
echo "║     $URL/mcp/invoke                                          ║"
echo "║                                                              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Example usage:                                              ║"
echo "║  curl -X POST $URL/mcp/invoke \\                              ║"
echo "║    -H 'Content-Type: application/json' \\                    ║"
echo "║    -d '{\"tool\":\"yolo_mode_enable\",\"params\":{...}}'         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Ngrok Web Interface: http://localhost:4040                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $MCP_PID $NGROK_PID 2>/dev/null
    rm -f "$NGROK_LOG"
    echo "✅ Stopped"
    exit 0
}

trap cleanup INT TERM

# Keep script running
wait
