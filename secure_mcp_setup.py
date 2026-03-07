#!/usr/bin/env python3
"""
Secure MCP Server Setup
Options to avoid exposing your real IP address
"""

import subprocess
import os
import sys
from pathlib import Path


def setup_ngrok():
    """
    Option 1: Ngrok (Easiest - gives you a random public URL)
    
    Pros:
    - No IP exposure
    - Automatic HTTPS
    - Random URL changes each restart
    - Free tier available
    
    Cons:
    - URL changes on restart
    - Rate limits on free tier
    """
    print("=" * 70)
    print("🔒 OPTION 1: Ngrok Tunnel (Recommended for testing)")
    print("=" * 70)
    
    guide = """
1. Install ngrok:
   curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \\
     sudo gpg --dearmor -o /etc/apt/keyrings/ngrok.gpg && \\
     echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \\
     sudo tee /etc/apt/sources.list.d/ngrok.list && \\
     sudo apt update && sudo apt install ngrok

2. Sign up at https://ngrok.com (free)

3. Add your auth token:
   ngrok config add-authtoken YOUR_TOKEN

4. Start secure tunnel to MCP server:
   ngrok http 8000

5. You'll get a secure URL like:
   https://abc123.ngrok-free.app

6. Give THIS URL to ChatGPT/Grok:
   https://abc123.ngrok-free.app/mcp/invoke

✅ Your real IP is hidden!
"""
    print(guide)


def setup_cloudflare_tunnel():
    """
    Option 2: Cloudflare Tunnel (Free, persistent URL)
    
    Pros:
    - No IP exposure
    - Custom subdomain (your-name.cloudflare.io)
    - Free forever
    - Built-in DDoS protection
    
    Cons:
    - Requires Cloudflare account
    - Slightly more setup
    """
    print("\n" + "=" * 70)
    print("🔒 OPTION 2: Cloudflare Tunnel (Best for production)")
    print("=" * 70)
    
    guide = """
1. Install cloudflared:
   curl -L --output cloudflared.deb \\
     https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && \\
     sudo dpkg -i cloudflared.deb

2. Login to Cloudflare:
   cloudflared tunnel login
   (This opens browser - select your domain)

3. Create a tunnel:
   cloudflared tunnel create mcp-server

4. Create config file ~/.cloudflared/config.yml:
   tunnel: YOUR_TUNNEL_ID
   credentials-file: /home/YOUR_USERNAME/.cloudflared/YOUR_TUNNEL_ID.json
   
   ingress:
     - hostname: mcp.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404

5. Route DNS:
   cloudflared tunnel route dns mcp-server mcp.yourdomain.com

6. Start tunnel:
   cloudflared tunnel run mcp-server

7. Give this URL to ChatGPT/Grok:
   https://mcp.yourdomain.com/mcp/invoke

✅ Permanent secure URL, no IP exposure, DDoS protected!
"""
    print(guide)


def setup_tailscale():
    """
    Option 3: Tailscale (Private mesh network)
    
    Pros:
    - Zero IP exposure
    - Private network (only authorized devices)
    - Free for personal use
    - No public internet exposure
    
    Cons:
    - Both sides need Tailscale
    - More complex setup
    """
    print("\n" + "=" * 70)
    print("🔒 OPTION 3: Tailscale (Private network)")
    print("=" * 70)
    
    guide = """
1. Install Tailscale:
   curl -fsSL https://tailscale.com/install.sh | sh

2. Start Tailscale:
   sudo tailscale up

3. Get your Tailscale IP:
   tailscale ip -4
   (Returns something like: 100.x.y.z)

4. ChatGPT/Grok would need Tailscale too (hard for web AIs)

⚠️  This is better for AI-to-AI communication, not web-based AIs

For ChatGPT/Grok, use Option 1 or 2 instead.
"""
    print(guide)


def setup_reverse_proxy():
    """
    Option 4: Reverse Proxy with Authentication
    
    If you already have a server/domain, use nginx/Caddy as proxy
    """
    print("\n" + "=" * 70)
    print("🔒 OPTION 4: Nginx Reverse Proxy (If you have a server)")
    print("=" * 70)
    
    config = '''
server {
    listen 443 ssl http2;
    server_name mcp.yourdomain.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # API Key authentication
    location /mcp/ {
        # Check API key
        if ($http_x_api_key != "YOUR_SECRET_API_KEY") {
            return 401;
        }
        
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
'''
    print(config)
    print("\n✅ This hides your real IP behind your domain!")


def setup_api_key_auth():
    """
    Add API key authentication to MCP server
    """
    print("\n" + "=" * 70)
    print("🔐 Add API Key Authentication (Security Layer)")
    print("=" * 70)
    
    code = '''
# Add this to mcp_http_server.py

import os
from fastapi import HTTPException, Header

API_KEY = os.getenv("MCP_API_KEY", "your-secret-key-here")

@app.middleware("http")
async def api_key_auth(request, call_next):
    # Skip auth for docs and health
    if request.url.path in ["/docs", "/openapi.json", "/health", "/"]:
        return await call_next(request)
    
    # Check API key
    api_key = request.headers.get("X-API-Key")
    if api_key != API_KEY:
        return JSONResponse(
            {"error": "Invalid or missing API key"},
            status_code=401
        )
    
    return await call_next(request)
'''
    print(code)
    print("\nThen start server with:")
    print("  MCP_API_KEY=super-secret-key python3 mcp_http_server.py")
    print("\nChatGPT/Grok must include header:")
    print('  X-API-Key: super-secret-key')


def setup_localtunnel():
    """
    Option 5: LocalTunnel (Free, no signup)
    
    Easiest option for quick testing
    """
    print("\n" + "=" * 70)
    print("🔒 OPTION 5: LocalTunnel (Easiest, no signup)")
    print("=" * 70)
    
    guide = """
1. Install LocalTunnel:
   npm install -g localtunnel

2. Start MCP server (in one terminal):
   python3 mcp_http_server.py

3. Start tunnel (in another terminal):
   lt --port 8000

4. You'll get a URL like:
   https://cool-beans-42.loca.lt

5. Give THIS URL to ChatGPT/Grok:
   https://cool-beans-42.loca.lt/mcp/invoke

⚠️  Note: LocalTunnel URLs change on restart
⚠️  Free tier has rate limits

✅ No IP exposure, no signup required!
"""
    print(guide)


def print_summary():
    """Print summary of options"""
    print("\n" + "=" * 70)
    print("📊 COMPARISON OF SECURE OPTIONS")
    print("=" * 70)
    
    comparison = """
┌─────────────────────┬────────────┬───────────┬────────────┬──────────┐
│ Option              │ IP Hidden? │ SSL/HTTPS │ Persistent │ Difficulty│
├─────────────────────┼────────────┼───────────┼────────────┼──────────┤
│ 1. Ngrok            │ ✅ Yes     │ ✅ Yes    │ ❌ No      │ Easy     │
│ 2. Cloudflare       │ ✅ Yes     │ ✅ Yes    │ ✅ Yes     │ Medium   │
│ 3. Tailscale        │ ✅ Yes     │ ✅ Yes    │ ✅ Yes     │ Hard     │
│ 4. Nginx Proxy      │ ✅ Yes     │ ✅ Yes    │ ✅ Yes     │ Hard     │
│ 5. LocalTunnel      │ ✅ Yes     │ ✅ Yes    │ ❌ No      │ Easy     │
└─────────────────────┴────────────┴───────────┴────────────┴──────────┘

RECOMMENDATION:
- Quick test: LocalTunnel (Option 5) - easiest
- Production: Cloudflare Tunnel (Option 2) - best overall
- Maximum security: Cloudflare + API Key auth
"""
    print(comparison)


def main():
    """Main menu"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         SECURE MCP SERVER SETUP - HIDE YOUR REAL IP                  ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    while True:
        print("\nChoose an option:")
        print("  1. Ngrok (Easiest, good for testing)")
        print("  2. Cloudflare Tunnel (Best for production)")
        print("  3. Tailscale (Private network)")
        print("  4. Nginx Reverse Proxy (If you have a server)")
        print("  5. LocalTunnel (No signup required)")
        print("  6. Add API Key Authentication")
        print("  7. Show comparison")
        print("  8. Exit")
        
        choice = input("\nEnter choice (1-8): ").strip()
        
        if choice == "1":
            setup_ngrok()
        elif choice == "2":
            setup_cloudflare_tunnel()
        elif choice == "3":
            setup_tailscale()
        elif choice == "4":
            setup_reverse_proxy()
        elif choice == "5":
            setup_localtunnel()
        elif choice == "6":
            setup_api_key_auth()
        elif choice == "7":
            print_summary()
        elif choice == "8":
            print("\n👋 Goodbye!")
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    # If run with --all, show all options
    if "--all" in sys.argv:
        setup_ngrok()
        setup_cloudflare_tunnel()
        setup_tailscale()
        setup_reverse_proxy()
        setup_localtunnel()
        setup_api_key_auth()
        print_summary()
    else:
        main()
