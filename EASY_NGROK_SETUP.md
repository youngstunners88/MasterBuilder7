# Easy Ngrok Setup (No Passwords!)

## Why Switch from LocalTunnel?

LocalTunnel requires a password every time someone accesses from a different IP. This is annoying for ChatGPT/Grok.

**Ngrok = No passwords needed!**

## Quick Setup (3 minutes)

### Step 1: Sign Up (30 seconds)
1. Go to https://ngrok.com
2. Click "Sign Up" (free)
3. Verify email

### Step 2: Get Your Token (30 seconds)
1. Go to https://dashboard.ngrok.com/get-started/your-authtoken
2. Copy the token (starts with `ngrok_...`)

### Step 3: Install & Configure (2 minutes)

Run these commands on your Google VM:

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo gpg --dearmor -o /etc/apt/keyrings/ngrok.gpg && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok

# Add your token (replace with your actual token)
ngrok config add-authtoken YOUR_TOKEN_HERE
```

### Step 4: Run Everything

```bash
cd /home/teacherchris37/MasterBuilder7
./setup_ngrok_quick.sh
```

Or manually:

```bash
# Terminal 1: Start MCP
source .venv/bin/activate
python3 mcp_http_server.py

# Terminal 2: Start Ngrok tunnel
ngrok http 8000
```

### Step 5: Get Your URL

Ngrok will show:
```
Forwarding  https://abc123-def.ngrok-free.app -> http://localhost:8000
```

**Give this to ChatGPT:**
```
https://abc123-def.ngrok-free.app/mcp/invoke
```

✅ **No password required!**

---

## Even Easier: Use the Script

```bash
# One command does everything
cd /home/teacherchris37/MasterBuilder7
./setup_ngrok_quick.sh
```

---

## Summary

| Feature | LocalTunnel | Ngrok |
|---------|-------------|-------|
| Password required | ❌ Yes | ✅ No |
| URL changes | ❌ Yes | ❌ Yes (free) |
| Setup time | 1 min | 3 min |
| Stability | Good | Better |
| HTTPS | ✅ Yes | ✅ Yes |

**Recommendation:** Use Ngrok - no password hassles!
