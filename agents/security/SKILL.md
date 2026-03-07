# Security Agent

Automated security auditing and vulnerability detection.

## Overview

**Platform**: CI/CD Pipeline
**Status**: Production Ready
**Tools**: Snyk, Bandit, Trivy, CodeQL

## Scans

| Type | Tool | Schedule |
|------|------|----------|
| Dependencies | Snyk | On push |
| Code Analysis | Bandit | On PR |
| Secrets | GitLeaks | On push |
| Containers | Trivy | On build |
| DAST | OWASP ZAP | Weekly |
| SAST | CodeQL | On push |

## Configuration

```yaml
security:
  snyk_token: ${SNYK_TOKEN}
  threshold: high
  fail_on_critical: true
  
notifications:
  slack: ${SLACK_WEBHOOK}
  email: security@ihhashi.co.za
```

## Blocking Rules

- Critical vulnerabilities
- Secrets in code
- Compliance violations
