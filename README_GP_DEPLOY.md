# Google Play Deployment Tool

A secure, easy-to-use tool for deploying Android apps to Google Play Store.

## Quick Start (3 minutes)

### 1. Setup (One-time)

```bash
python gp_wizard.py
```

This interactive wizard will:
- Guide you through Google Play credential setup
- Configure your package name
- Set up notifications (optional)
- Test the connection

### 2. Deploy

```bash
# Auto-detect and deploy
python gp_wizard.py --deploy

# Or specify explicitly
python google_play_deployment.py deploy build/app.aab production
```

### 3. Monitor

```bash
# View dashboard
python gp_dashboard.py

# Watch in real-time
python gp_dashboard.py --watch
```

## Installation

### Requirements

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib pyyaml
```

### Configuration

The tool supports configuration via:

1. **Interactive wizard** (recommended): `python gp_wizard.py`
2. **Config file**: `~/.config/gp-deploy/config.yml`
3. **Environment variables**: For CI/CD

## Usage

### Commands

```bash
# Validate AAB file
python google_play_deployment.py validate build/app.aab

# Deploy to a track
python google_play_deployment.py deploy build/app.aab internal
python google_play_deployment.py deploy build/app.aab alpha "v1.0.0" "Bug fixes"
python google_play_deployment.py deploy build/app.aab production

# Check deployment status
python google_play_deployment.py status <deployment-id>

# List recent deployments
python google_play_deployment.py list

# Promote between tracks
python google_play_deployment.py promote 123 alpha beta

# Rollback
python google_play_deployment.py rollback production 122
```

### Configuration File

Create `gp-deploy.yml` in your project root:

```yaml
google_play:
  credentials_file: ~/.credentials/play-store.json
  package_name: com.example.app

deployment:
  default_track: internal
  auto_promote: true
  promote_from: internal
  promote_to: alpha

notifications:
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/...
  email:
    enabled: true
    address: team@example.com
```

## CI/CD Integration

### GitHub Actions

Add `.github/workflows/google-play-deploy.yml`:

```yaml
name: Deploy to Google Play

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  deploy:
    uses: youngstunners88/MasterBuilder7/.github/workflows/google-play-deploy.yml@main
    secrets:
      GOOGLE_PLAY_SERVICE_ACCOUNT: ${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT }}
    with:
      GOOGLE_PLAY_PACKAGE_NAME: ${{ vars.GOOGLE_PLAY_PACKAGE_NAME }}
```

Required secrets:
- `GOOGLE_PLAY_SERVICE_ACCOUNT`: Your service account JSON
- `GOOGLE_PLAY_PACKAGE_NAME`: Your app's package name

Optional:
- `SLACK_WEBHOOK_URL`: For notifications

### GitLab CI

```yaml
deploy:
  stage: deploy
  image: python:3.11
  script:
    - pip install google-api-python-client pyyaml
    - python google_play_deployment.py deploy build/app.aab internal
  only:
    - main
```

## Security

This tool implements enterprise-grade security:

- ✅ Path traversal protection
- ✅ Command injection prevention
- ✅ Input validation & sanitization
- ✅ Replay attack prevention
- ✅ Audit logging
- ✅ Rate limiting
- ✅ ZIP bomb detection
- ✅ No secrets in code

See [SECURITY_AUDIT_REPORT.md](docs/SECURITY_AUDIT_REPORT.md) for details.

## Features

### Core
- [x] AAB file validation
- [x] Google Play API integration
- [x] Multi-track support (internal/alpha/beta/production)
- [x] Deployment history
- [x] Rollback support

### UX
- [x] Interactive setup wizard
- [x] Auto-detect AAB files
- [x] Progress indicators
- [x] Dashboard
- [x] Configuration file support

### CI/CD
- [x] GitHub Actions workflow
- [x] Environment variable support
- [x] Slack notifications
- [x] Automatic track selection

## Troubleshooting

### "Environment not configured"

Run the setup wizard:
```bash
python gp_wizard.py
```

### "Invalid credentials"

1. Go to [Google Play Console](https://play.google.com/console)
2. Setup → API Access → Create Service Account
3. Download JSON key
4. Run wizard and paste credentials

### "AAB validation failed"

Check:
- File size < 150MB
- Valid ZIP structure
- Compression ratio < 100x

### View logs

```bash
# Application logs
tail -f /tmp/google_play_deploy.log

# Security audit logs
tail -f /tmp/google_play_security.log
```

## Advanced Usage

### Staged Rollouts

Deploy to percentage of users:

```python
# In your script
from google_play_deployment import GooglePlayAPIClient

client = GooglePlayAPIClient()
client.upload_aab(
    aab_path="app.aab",
    track="production",
    user_fraction=0.1  # 10% of users
)
```

### Custom Release Notes

```bash
python google_play_deployment.py deploy app.aab production \
  "v2.0.0" \
  "New features:\n- Feature 1\n- Feature 2\n\nBug fixes:\n- Fixed crash on startup"
```

### Auto-promotion

Configure in `gp-deploy.yml`:

```yaml
deployment:
  auto_promote: true
  promote_from: internal
  promote_to: alpha
```

Then run:

```bash
python google_play_deployment.py deploy app.aab internal --auto-promote
```

## API Usage

Use programmatically in Python:

```python
import asyncio
from google_play_deployment import DeploymentManager, Track

async def deploy():
    manager = DeploymentManager()
    
    result = await manager.deploy(
        aab_path="build/app.aab",
        track=Track.PRODUCTION,
        release_name="v1.0.0",
        release_notes="Initial release"
    )
    
    if result.success:
        print(f"Deployed! ID: {result.deployment_id}")
    else:
        print(f"Failed: {result.error_details}")

asyncio.run(deploy())
```

## Monitoring

### Prometheus Metrics

The tool exports metrics for monitoring:

```
gp_deployments_total{track="production", status="success"}
gp_deployment_duration_seconds
gp_validation_errors_total
```

### Dashboard

```bash
# Start dashboard
python gp_dashboard.py --watch
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python -m pytest tests/`
4. Submit a pull request

## License

MIT License - See LICENSE file

## Support

- Issues: [GitHub Issues](https://github.com/youngstunners88/MasterBuilder7/issues)
- Documentation: [docs/](docs/)
