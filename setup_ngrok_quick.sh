#!/bin/bash
# Quick Ngrok Setup (No password required!)

echo "🚀 Setting up Ngrok (No password hassles!)"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "📦 Installing ngrok..."
    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
    tar xzf ngrok-v3-stable-linux-amd64.tgz 2>/dev/null
    chmod +x ngrok
    sudo mv ngrok /usr/local/bin/ 2>/dev/null || mv ngrok ~/.local/bin/ 2>/dev/null || echo "ngrok" > /dev/null
    rm -f ngrok-v3-stable-linux-amd64.tgz
    echo "✅ Ngrok installed"
else
    echo "✅ Ngrok already installed"
fi

echo ""
echo "🔑 Next steps:"
echo "1. Sign up at https://ngrok.com (free, takes 30 seconds)"
echo "2. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
echo "3. Run: ngrok config add-authtoken YOUR_TOKEN"
echo "4. Then run this script again"
echo ""

# Check if authtoken is configured
if ngrok config check &> /dev/null; then
    echo "✅ Authtoken configured!"
    echo ""
    echo "🎯 Starting MCP server + Ngrok tunnel..."
    echo ""
    
    # Start MCP server in background
    cd /home/teacherchris37/MasterBuilder7
    source .venv/bin/activate
    
    echo "🚀 Starting MCP server on port 8000..."
    python3 mcp_http_server.py &
    MCP_PID=$!
    
    sleep 3
    
    echo "🌐 Starting Ngrok tunnel..."
    echo "📡 Your secure URL (give this to ChatGPT):"
    echo "=========================================="
    
    # Start ngrok and capture URL
    ngrok http 8000 --log=stdout &
    NGROK_PID=$!
    
    sleep 5
    
    # Display the URL
    echo ""
    echo "🔗 Ngrok URLs (check above for https://xxx.ngrok-free.app)"
    echo ""
    echo "📋 To see the URL, run in another terminal:"
    echo "  curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^\"]*'"
    echo ""
    
    # Cleanup on exit
    trap "kill $MCP_PID $NGROK_PID 2>/dev/null; exit" INT TERM
    wait
else
    echo "❌ No authtoken found"
    echo "   Please run: ngrok config add-authtoken YOUR_TOKEN"
fi
