# Google Play Deployment - Production Hardening Guide

Complete guide for securely deploying the Google Play Store MCP server in production.

---

## Quick Start (Production)

```bash
# 1. Clone and setup
cd /home/teacherchris37/MasterBuilder7
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic slowapi

# 2. Set environment variables
export MCP_API_SECRET="$(openssl rand -hex 32)"
export GOOGLE_PLAY_PACKAGE_NAME="com.yourcompany.app"
export GOOGLE_PLAY_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# 3. Validate environment
python google_play_deployment.py env-check

# 4. Start server
python mcp_http_server_playstore.py
```

---

## Environment Configuration

### Required Variables

```bash
# Core security (MANDATORY)
export MCP_API_SECRET="your-min-32-char-secret-here-random-string"
export GOOGLE_PLAY_SERVICE_ACCOUNT_JSON='{
  "type": "service_account",
  "project_id": "your-project",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----...",
  "client_email": "play-store@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}'
export GOOGLE_PLAY_PACKAGE_NAME="com.yourcompany.app"

# Rate limiting (optional, defaults shown)
export RATE_LIMIT_REQUESTS="100"
export RATE_LIMIT_WINDOW="60"

# Network (optional, defaults shown)
export MCP_HOST="127.0.0.1"
export MCP_PORT="8000"
export ALLOWED_ORIGINS="https://yourdomain.com,https://admin.yourdomain.com"

# Request limits
export MAX_REQUEST_SIZE="1048576"  # 1MB
export REQUEST_TIMEOUT="30"
```

### Generating Secure Secrets

```bash
# API Secret (32+ chars)
openssl rand -hex 32

# Generate nonce for testing
date +%s%N | sha256sum | head -c 32

# Generate request signature
echo -n '{"tool":"validate","params":{}}' | openssl dgst -sha256 -hmac "$MCP_API_SECRET"
```

---

## Google Play Service Account Setup

### 1. Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. IAM & Admin → Service Accounts
4. Create Service Account
   - Name: `play-store-deployer`
   - Role: `Service Account User`

### 2. Grant Play Console Access

1. Go to [Google Play Console](https://play.google.com/console/)
2. Setup → API Access
3. Link your Google Cloud project
4. Invite service account:
   - Email: `play-store@your-project.iam.gserviceaccount.com`
   - Role: `Release Manager` (or Admin)

### 3. Create JSON Key

1. Google Cloud Console → Service Accounts
2. Select your service account
3. Keys → Add Key → Create New Key
4. Select JSON format
5. Download and save securely

### 4. Set Environment Variable

```bash
# Copy JSON content
export GOOGLE_PLAY_SERVICE_ACCOUNT_JSON="$(cat service-account.json)"

# Or directly
cat service-account.json | jq -c | read -r GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
```

---

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/mcp-playstore.service`:

```ini
[Unit]
Description=MCP PlayStore Server
After=network.target

[Service]
Type=simple
User=mcp
Group=mcp
WorkingDirectory=/opt/mcp-playstore
Environment=PYTHONPATH=/opt/mcp-playstore
Environment=MCP_HOST=127.0.0.1
Environment=MCP_PORT=8000
Environment=MCP_API_SECRET=your-secret-here
Environment=GOOGLE_PLAY_PACKAGE_NAME=com.yourcompany.app
# Load other env vars from file
EnvironmentFile=/opt/mcp-playstore/.env

ExecStart=/opt/mcp-playstore/venv/bin/python mcp_http_server_playstore.py
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-playstore
sudo systemctl start mcp-playstore
sudo systemctl status mcp-playstore
```

### Nginx Reverse Proxy (HTTPS)

```nginx
server {
    listen 443 ssl http2;
    server_name mcp.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name mcp.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

# Security: Run as non-root
RUN groupadd -r mcp && useradd -r -g mcp mcp

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY mcp_http_server_playstore.py .
COPY google_play_deployment.py .

# Set ownership
RUN chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "mcp_http_server_playstore.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-playstore:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000
      - MCP_API_SECRET=${MCP_API_SECRET}
      - GOOGLE_PLAY_PACKAGE_NAME=${GOOGLE_PLAY_PACKAGE_NAME}
      - GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=${GOOGLE_PLAY_SERVICE_ACCOUNT_JSON}
    volumes:
      - ./artifacts:/app/artifacts:ro
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

---

## Usage Examples

### 1. Validate AAB File

```bash
python google_play_deployment.py validate artifacts/app.aab
```

### 2. Deploy to Internal Track

```bash
python google_play_deployment.py deploy artifacts/app.aab internal "v1.0.0" "Initial release"
```

### 3. Check Deployment Status

```bash
python google_play_deployment.py status <deployment-id>
```

### 4. Promote to Production

```bash
python google_play_deployment.py promote 12345 beta production
```

### 5. MCP API Call (with authentication)

```bash
#!/bin/bash
# deploy.sh - Example MCP API call

API_URL="https://mcp.yourdomain.com"
API_SECRET="your-secret"
TOOL="google_play_deploy"
AAB_PATH="artifacts/app.aab"
TRACK="internal"

# Generate request components
TIMESTAMP=$(date +%s)
NONCE=$(openssl rand -hex 16)
REQUEST_ID=$(uuidgen)

# Build request body
BODY=$(cat <<EOF
{
  "tool": "$TOOL",
  "params": {
    "aab_path": "$AAB_PATH",
    "track": "$TRACK"
  },
  "request_id": "$REQUEST_ID",
  "timestamp": $TIMESTAMP
}
EOF
)

# Generate signature
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$API_SECRET" | cut -d' ' -f2)

# Make request
curl -X POST "$API_URL/mcp/invoke" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET" \
  -H "X-Timestamp: $TIMESTAMP" \
  -H "X-Nonce: $NONCE" \
  -H "X-Request-Signature: $SIGNATURE" \
  -d "$BODY"
```

---

## Monitoring & Alerting

### Log Monitoring

```bash
# Watch security events
tail -f /tmp/mcp_playstore_security.log | grep "AUTH_FAIL"

# Monitor deployments
tail -f /tmp/google_play_deploy.log

# Failed deployments
journalctl -u mcp-playstore -f | grep ERROR
```

### Prometheus Metrics (Optional)

Add to your monitoring:
```python
# Add to mcp_http_server_playstore.py
from prometheus_client import Counter, Histogram, generate_latest

deployment_counter = Counter('gp_deployments_total', 'Total deployments', ['track', 'status'])
deployment_duration = Histogram('gp_deployment_duration_seconds', 'Deployment duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: mcp-playstore
    rules:
      - alert: HighAuthFailureRate
        expr: rate(auth_failures_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High authentication failure rate"
          
      - alert: DeploymentFailures
        expr: rate(deployments_failed_total[1h]) > 5
        for: 10m
        labels:
          severity: critical
```

---

## Troubleshooting

### Environment Validation Fails

```bash
# Check all required vars
python google_play_deployment.py env-check

# Common issues:
# 1. Missing GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
echo $GOOGLE_PLAY_SERVICE_ACCOUNT_JSON | jq .  # Should output valid JSON

# 2. Invalid MCP_API_SECRET
# Must be at least 32 characters
```

### Authentication Failures

```bash
# Check logs
tail /tmp/mcp_playstore_security.log

# Common causes:
# - Wrong API secret
# - Expired timestamp (clock skew)
# - Reused nonce
# - Missing headers
```

### Google Play API Errors

```bash
# Verify service account permissions
# Check Play Console > Setup > API Access

# Test connectivity
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

creds = service_account.Credentials.from_service_account_info(
    json.loads(os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON')),
    scopes=['https://www.googleapis.com/auth/androidpublisher']
)
service = build('androidpublisher', 'v3', credentials=creds)
print('Connected successfully')
"
```

---

## Security Checklist

### Before Production

- [ ] API secret is 32+ random characters
- [ ] Service account has minimum required permissions
- [ ] HTTPS enabled with valid certificate
- [ ] Rate limiting configured
- [ ] CORS origins restricted
- [ ] Logs stored securely with rotation
- [ ] Health checks configured
- [ ] Rollback procedures tested
- [ ] Backup of signing keys

### Regular Maintenance

- [ ] Rotate API secrets quarterly
- [ ] Review audit logs weekly
- [ ] Update dependencies monthly
- [ ] Test disaster recovery quarterly
- [ ] Review service account permissions annually

---

## API Reference

### MCP Tools Available

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `google_play_deploy` | Deploy AAB to track | Yes |
| `google_play_status` | Check deployment status | Yes |
| `google_play_list_tracks` | List release tracks | Yes |
| `google_play_rollback` | Rollback release | Yes |
| `google_play_validate_aab` | Validate AAB file | Yes |

### HTTP Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/mcp/tools` | GET | No | List tools |
| `/mcp/invoke` | POST | Yes | Invoke tool |
| `/mcp/status` | GET | Yes | Server status |

---

## Support

For issues:
1. Check logs: `/tmp/mcp_playstore_*.log`
2. Validate environment: `python google_play_deployment.py env-check`
3. Review audit logs: `tail /tmp/mcp_playstore_security.log`
4. Open GitHub issue with logs (redact secrets)
