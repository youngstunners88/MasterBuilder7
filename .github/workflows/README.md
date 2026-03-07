# GitHub Actions CI/CD Workflows

This directory contains comprehensive CI/CD workflows for the MasterBuilder7 project.

## Workflows Overview

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI** | `ci.yml` | Push/PR to main/develop | Run tests, linting, type checking |
| **Build** | `build.yml` | Post-CI success, tags | Build Docker images and packages |
| **Deploy Staging** | `deploy-staging.yml` | Post-build on develop | Deploy to staging environment |
| **Deploy Production** | `deploy-production.yml` | Manual, tags | Deploy to production with approval |
| **Agent Orchestration** | `agent-orchestration.yml` | Agent changes, schedule | Manage AI agent fleet |
| **Security Scan** | `security-scan.yml` | Daily, PRs | Security audits and vulnerability scans |
| **Release** | `release.yml` | Tags, manual | Create releases with changelogs |

## Workflow Details

### 🔍 CI (ci.yml)

**Triggers:**
- Push to `main`, `develop`, `feature/**`, `bugfix/**`
- Pull requests to `main`, `develop`

**Jobs:**
1. **Lint & Format** - Black, isort, flake8
2. **Type Check** - mypy
3. **Security Check** - Bandit, TruffleHog
4. **Test** - pytest with coverage (Python 3.10, 3.11, 3.12)
5. **Build Check** - Package and Docker build verification

**Features:**
- Parallel test matrix across Python versions
- Caching for pip dependencies
- Codecov integration
- Slack notifications on failure

### 🏗️ Build (build.yml)

**Triggers:**
- Successful CI on main/develop
- Tags (`v*`, `release-*`)
- Manual dispatch

**Jobs:**
1. **Version Management** - Determine version from tags/inputs
2. **Build Python Package** - Create wheel distribution
3. **Build Docker Images** - Multi-arch images for main app
4. **Build Agent Images** - Individual agent containers
5. **Scan Images** - Trivy vulnerability scanning
6. **Build Docs** - Documentation generation

**Features:**
- Multi-platform builds (linux/amd64, linux/arm64)
- Container registry push (ghcr.io)
- SBOM generation
- Image signing ready

### 🚀 Deploy Staging (deploy-staging.yml)

**Triggers:**
- Successful build on `develop`
- Manual dispatch

**Jobs:**
1. **Pre-deploy Checks** - Validate secrets, image exists
2. **Database Migration** - Alembic migrations
3. **Deploy to Kubernetes** - Rolling update deployment
4. **Smoke Tests** - Health checks and API validation

**Features:**
- Automatic rollback on failure
- Database backups before migration
- Kubernetes rolling updates
- Slack notifications

### 🚀 Deploy Production (deploy-production.yml)

**Triggers:**
- Successful staging deployment
- Manual dispatch with approval

**Jobs:**
1. **Approval Gate** - Require manual approval
2. **Pre-deployment Validation** - Checklist verification
3. **Backup Database** - Pre-deploy backup
4. **Database Migration** - Production migrations
5. **Deploy** - Blue-green deployment
6. **Smoke Tests** - Production health checks
7. **Rollback** - Automatic rollback on failure

**Features:**
- Required manual approval (GitHub Environments)
- Database backup before deployment
- Blue-green deployment strategy
- Automatic rollback on smoke test failure
- PagerDuty integration for failures

### 🤖 Agent Orchestration (agent-orchestration.yml)

**Triggers:**
- Changes to agent code
- Hourly health checks
- Daily orchestration (2 AM UTC)
- Manual dispatch

**Operations:**
- `health-check` - Verify all agents are healthy
- `build-all` - Build all agent images
- `test-all` - Run agent tests
- `orchestrate` - Fleet orchestration
- `deploy-agents` - Deploy to environment
- `update-knowledge-base` - Update agent knowledge

**Features:**
- Agent change detection
- Individual agent building/testing
- Knowledge base updates
- Fleet health monitoring

### 🔒 Security Scan (security-scan.yml)

**Triggers:**
- Daily at 3 AM UTC
- PRs to main
- Manual dispatch

**Scan Types:**
1. **Secret Detection** - TruffleHog, GitLeaks
2. **Dependency Scan** - Safety, pip-audit, OWASP Dependency-Check
3. **SAST** - Bandit, Semgrep, CodeQL
4. **Container Scan** - Trivy, Snyk
5. **IaC Scan** - Checkov, KICS
6. **License Check** - pip-licenses

**Features:**
- Configurable severity thresholds
- SARIF report upload to GitHub Security
- Artifact retention (90 days)
- Slack alerts for critical findings

### 🏷️ Release (release.yml)

**Triggers:**
- Tags (`v*.*.*`)
- Manual dispatch

**Jobs:**
1. **Validation** - Verify version format, CHANGELOG
2. **Build Artifacts** - Cross-platform binaries
3. **Build Images** - Tagged container images
4. **Generate Changelog** - Categorized commit history
5. **Create Release** - GitHub release with assets
6. **Update Docs** - Deploy to GitHub Pages
7. **Deploy PyPI** - Upload to Python Package Index

**Features:**
- Automatic changelog generation
- Multi-platform artifacts
- Semver tagging for Docker
- GitHub Pages documentation
- PyPI publishing

## Required Secrets

### Required for All Workflows
- `GITHUB_TOKEN` - Automatically provided

### CI/CD Secrets
- `CODECOV_TOKEN` - Codecov coverage upload
- `SLACK_WEBHOOK_URL` - Slack notifications

### Deployment Secrets
- `KUBE_CONFIG_STAGING` - Base64-encoded kubeconfig for staging
- `KUBE_CONFIG_PRODUCTION` - Base64-encoded kubeconfig for production
- `DATABASE_URL_STAGING` - Staging database connection
- `DATABASE_URL_PRODUCTION` - Production database connection
- `STAGING_URL` - Staging environment URL
- `PRODUCTION_URL` - Production environment URL
- `PROD_SMOKE_TEST_API_KEY` - API key for production smoke tests

### Agent Secrets
- `AGENT_API_URL_STAGING` - Staging agent API endpoint
- `AGENT_API_KEY` - Agent API authentication
- `OPENAI_API_KEY` - For knowledge base updates
- `CHROMA_PERSIST_DIR` - Vector database persistence

### Security Secrets
- `SLACK_SECURITY_WEBHOOK_URL` - Security alerts
- `SNYK_TOKEN` - Snyk container scanning
- `GITLEAKS_LICENSE` - GitLeaks license

### Release Secrets
- `PYPI_API_TOKEN` - PyPI publishing
- `PAGERDUTY_KEY` - PagerDuty integration

## Environment Configuration

### GitHub Environments

#### staging
- Required: No approval required
- URL: https://staging.masterbuilder7.io

#### production
- Required: Manual approval required
- URL: https://api.masterbuilder7.io
- Protection rules: Required reviewers

## Usage Examples

### Manual CI Trigger
```bash
# Go to Actions > CI > Run workflow
# Select Python version
```

### Deploy Specific Version to Staging
```bash
# Actions > Deploy to Staging > Run workflow
# Input version: v1.2.3
```

### Run Security Scan
```bash
# Actions > Security Scan > Run workflow
# Select scan type: full
# Set severity threshold: HIGH
```

### Create Release
```bash
# Tag and push
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3

# Or manually via Actions > Create Release
```

## Best Practices

1. **Always create PRs** - Direct pushes to main are discouraged
2. **Tag releases** - Use semantic versioning (v1.2.3)
3. **Update CHANGELOG** - Document changes before releasing
4. **Monitor deployments** - Watch Slack notifications
5. **Review security scans** - Address findings promptly

## Troubleshooting

### Workflow Failures

Check the job logs in GitHub Actions UI for specific error details.

### Deployment Rollbacks

Production deployments automatically rollback on smoke test failure. Manual rollback:
```bash
kubectl rollout undo deployment/masterbuilder7 -n masterbuilder7-prod
```

### Agent Health Issues

Run manual health check:
```bash
# Actions > Agent Orchestration > Run workflow
# Operation: health-check
```

## Maintenance

### Updating Python Versions

Edit `PYTHON_VERSION` environment variable in workflows.

### Adding New Agents

Update the agent matrix in `agent-orchestration.yml`:
```yaml
matrix:
  agent:
    - meta-router
    - planning-agent
    - your-new-agent
```

### Modifying Deployment Strategy

Edit the Kubernetes deployment steps in `deploy-staging.yml` and `deploy-production.yml`.

## License

See [LICENSE](../../LICENSE) for details.
