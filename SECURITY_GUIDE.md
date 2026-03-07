# Security Guide: Protect Your IP Address

## ⚠️ Why You Should NOT Give Out Your Real IP

**Risks of exposing your real IP:**
- DDoS attacks
- Port scanning
- Direct server attacks
- Privacy concerns
- Location exposure

**Solution:** Use a **secure tunnel** that hides your IP!

---

## 🔒 Recommended: Secure Tunnel Options

### Option 1: LocalTunnel (Easiest - 2 minutes setup)

**Best for:** Quick testing, no signup required

```bash
# 1. Install (if you have Node.js)
npm install -g localtunnel

# 2. Start MCP server (Terminal 1)
cd /home/teacherchris37/MasterBuilder7
source .venv/bin/activate
python3 mcp_http_server.py

# 3. Start tunnel (Terminal 2)
lt --port 8000

# 4. You'll get a secure URL:
# https://cool-beans-42.loca.lt

# 5. Give THIS to ChatGPT/Grok:
# https://cool-beans-42.loca.lt/mcp/invoke
```

**Pros:**
- ✅ Free, no signup
- ✅ Hides your real IP
- ✅ HTTPS enabled
- ✅ Instant setup

**Cons:**
- ❌ URL changes on restart
- ❌ Rate limits

---

### Option 2: Ngrok (Most Popular)

**Best for:** Regular use, stable connections

```bash
# 1. Install
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# 2. Sign up at https://ngrok.com (free)
# Get your authtoken from dashboard

# 3. Configure
ngrok config add-authtoken YOUR_TOKEN_HERE

# 4. Start MCP server (Terminal 1)
python3 mcp_http_server.py

# 5. Start tunnel (Terminal 2)
ngrok http 8000

# 6. You'll get a URL:
# https://abc123-def.ngrok-free.app

# 7. Give THIS to ChatGPT/Grok
```

**Pros:**
- ✅ Most popular, well-documented
- ✅ HTTPS included
- ✅ Web dashboard
- ✅ Stable URLs (with paid plan)

**Cons:**
- ❌ Free URLs change on restart
- ❌ Requires signup

---

### Option 3: Cloudflare Tunnel (Best for Production)

**Best for:** Permanent setup, professional use

```bash
# 1. Install
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 2. Login (opens browser)
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create mcp-server

# 4. Create config file
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/YOUR_USERNAME/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: mcp.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# 5. Add DNS record
cloudflared tunnel route dns mcp-server mcp.yourdomain.com

# 6. Start tunnel
cloudflared tunnel run mcp-server

# 7. Permanent URL: https://mcp.yourdomain.com
```

**Pros:**
- ✅ **Permanent URL** (never changes!)
- ✅ Free forever
- ✅ DDoS protection
- ✅ Your own subdomain
- ✅ Most secure option

**Cons:**
- ❌ Requires domain (can use free subdomain)
- ❌ More setup steps

---

## 🔐 Add API Key Authentication (Extra Security)

Even with a tunnel, add API key authentication:

### 1. Set API Key
```bash
export MCP_API_KEY="super-secret-key-$(date +%s)"
echo $MCP_API_KEY
```

### 2. Start Secure Server
```bash
python3 mcp_http_server_secure.py
```

### 3. ChatGPT/Grok Must Include Header:
```bash
curl -X POST https://your-tunnel-url/mcp/invoke \
  -H "Authorization: Bearer super-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "yolo_mode_enable",
    "params": {"project_path": "/path/to/project"}
  }'
```

---

## 📋 Quick Setup Summary

### For Testing (5 minutes):
```bash
# Terminal 1: Start MCP
python3 mcp_http_server.py

# Terminal 2: Start tunnel
npx localtunnel --port 8000

# Give tunnel URL to ChatGPT/Grok
```

### For Regular Use:
```bash
# 1. Install ngrok
# 2. Sign up at ngrok.com
# 3. Add authtoken
# 4. ngrok http 8000
```

### For Production:
```bash
# 1. Set up Cloudflare Tunnel
# 2. Get your own domain
# 3. Permanent URL forever
# 4. Most secure option
```

---

## 🔍 Verify Your Real IP is Hidden

After setting up tunnel, verify:

```bash
# 1. Check what IP tunnel shows
curl https://your-tunnel-url/health

# 2. It should NOT show your real IP
# 3. Only the tunnel's IP is exposed
```

---

## ⚡ One-Command Setup Script

```bash
# Save as setup_secure_mcp.sh
cat > setup_secure_mcp.sh << 'EOF'
#!/bin/bash

echo "🔒 Setting up Secure MCP Server..."

# Check if localtunnel is available
if command -v lt &> /dev/null; then
    echo "✅ LocalTunnel found"
    TUNNEL_CMD="lt --port 8000"
elif command -v npx &> /dev/null; then
    echo "✅ Using npx localtunnel"
    TUNNEL_CMD="npx localtunnel --port 8000"
else
    echo "❌ Please install Node.js or localtunnel"
    exit 1
fi

# Start MCP server in background
echo "🚀 Starting MCP server..."
cd /home/teacherchris37/MasterBuilder7
source .venv/bin/activate
python3 mcp_http_server.py &
MCP_PID=$!

sleep 2

# Start tunnel
echo "🌐 Starting secure tunnel..."
echo "📡 Your secure URL will appear below:"
echo "========================================"
$TUNNEL_CMD

# Cleanup on exit
trap "kill $MCP_PID 2>/dev/null; exit" INT TERM
wait
EOF

chmod +x setup_secure_mcp.sh
./setup_secure_mcp.sh
```

---

## 🎯 What to Give ChatGPT/Grok

### ❌ NEVER Give:
- Your real IP: `http://192.168.1.100:8000`
- Your home IP: `http://203.0.113.45:8000`
- Direct server access

### ✅ ALWAYS Give:
- LocalTunnel: `https://cool-beans-42.loca.lt`
- Ngrok: `https://abc123.ngrok-free.app`
- Cloudflare: `https://mcp.yourdomain.com`

---

## 🔒 Security Checklist

- [ ] Using tunnel (not real IP)
- [ ] HTTPS enabled
- [ ] API key authentication set
- [ ] Rate limiting enabled
- [ ] Request logging active
- [ ] Tunnel URL changes regularly (or use static with Cloudflare)

---

## 🚨 Emergency: If You Accidentally Exposed Your IP

```bash
# 1. Stop MCP server immediately
pkill -f mcp_http_server

# 2. Change firewall rules
sudo ufw deny 8000

# 3. Restart with tunnel ONLY
./setup_secure_mcp.sh

# 4. Monitor for suspicious activity
sudo tail -f /var/log/auth.log
```

---

## 📞 Summary

**Question:** How do I safely connect ChatGPT/Grok without exposing my IP?

**Answer:** Use a **tunnel**!

```
Your Server (localhost:8000)
    ↓
Tunnel (ngrok, localtunnel, cloudflare)
    ↓
Secure HTTPS URL (no IP exposed!)
    ↓
ChatGPT/Grok connect here
```

**Easiest:** `npx localtunnel --port 8000`  
**Best:** Cloudflare Tunnel with your own domain

**Your real IP stays private!** 🔒
