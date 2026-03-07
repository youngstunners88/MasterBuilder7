# DevOps Engineer AGENTS.md
## Deployment & Infrastructure Protocol

### MANDATORY: Pre-Deployment Search

**Before ANY deployment:**

1. **Check `../shared/memory/deployment-history.md`**
   - Last deployment status
   - Known issues with this environment
   - Recent infrastructure changes

2. **Read `../shared/memory/infrastructure-state.md`**
   - Current environment versions
   - Resource utilization
   - Pending maintenance windows

3. **Verify `../shared/memory/budget-tracker.md`**
   - Deployment cost estimate
   - Remaining budget
   - If <20% budget → Flag for approval

### CI/CD Pipeline Protocol

**Pipeline Stages:**
```yaml
1. BUILD:
   - Checkout code
   - Install dependencies
   - Run unit tests
   - Build artifacts
   
2. TEST:
   - Run integration tests
   - Security scans
   - Performance benchmarks
   - Guardian verification
   
3. STAGE:
   - Deploy to staging
   - Run smoke tests
   - Manual QA (if required)
   
4. PROD:
   - Deploy to production (blue-green)
   - Automated smoke tests
   - Monitor for 30 minutes
   - Mark complete or rollback
```

**GitHub Actions Integration:**
```yaml
name: APEX Deploy
on:
  workflow_dispatch:
    inputs:
      repo_url: { required: true }
      track: { required: true }
      budget_limit: { required: true }

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: APEX Deploy
        run: |
          bun run captain deploy \
            --repo ${{ inputs.repo_url }} \
            --track ${{ inputs.track }} \
            --budget ${{ inputs.budget_limit }}
```

### Deployment Strategies

**Blue-Green (Preferred):**
- Deploy new version to "green" environment
- Run smoke tests
- Switch traffic (blue → green)
- Keep blue for 1 hour (instant rollback)
- Destroy blue after confirmation

**Canary (For high-risk):**
- Deploy to 5% of traffic
- Monitor for 1 hour
- Gradually increase: 25% → 50% → 100%
- Automatic rollback if error rate > threshold

**Rolling (For stateless):**
- Replace instances one by one
- Max unavailable: 1
- Health check before next instance

### Health Monitoring

**Post-Deployment Checks (First 30 min):**
- Error rate < 0.1%
- P95 latency < 500ms
- 5xx rate = 0
- CPU/memory stable

**If ANY check fails:**
1. Trigger automatic rollback
2. Notify Captain
3. Preserve failed deployment logs
4. Require Guardian re-verification

**Record in `memory/deployment-health.md`:**
```yaml
deployment_id: uuid
timestamp: ISO8601
metrics:
  error_rate: 0.02%
  latency_p95: 120ms
  cpu_avg: 45%
status: HEALTHY
incidents: []
```

### Rollback Protocol

**Automatic Triggers:**
- Error rate > 1% for 5 minutes
- 5xx rate > 0.5%
- P95 latency > 2x baseline
- Guardian NO-GO after deployment

**Manual Rollback:**
```bash
# Via Captain
captain rollback --workflow [id] --to-last-green

# Or GitHub Actions
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/.../actions/workflows/rollback.yml/dispatches \
  -d '{"ref":"main","inputs":{"workflow_id":"..."}}'
```

**Rollback Steps:**
1. Stop traffic to new version
2. Switch to last known good
3. Verify health checks pass
4. Notify all agents
5. Log incident to `memory/rollback-incidents.md`

### Infrastructure as Code

**Terraform/CloudFormation:**
- All resources defined in code
- State stored remotely (S3 + DynamoDB)
- Changes via PR, not console
- Drift detection daily

**Environment Parity:**
- Staging = Production (smaller scale)
- Same versions, same configs
- Same monitoring, same alerts
- Test disaster recovery in staging

### Cost Optimization

**Track in `memory/cost-optimization.md`:**
- Resource right-sizing (don't over-provision)
- Spot instances for batch jobs
- Reserved instances for steady-state
- Storage lifecycle policies

**Monthly Review:**
- Top 5 costs by service
- Unused resources (orphaned disks, etc.)
- Reserved instance coverage
- Budget vs actual

---
*"Production is not a place. It's a state of mind."*
