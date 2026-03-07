# Skill 7: Security Oracle

Proactive vulnerability detection and remediation.

## Overview

The Security Oracle provides comprehensive security scanning capabilities including:
- Static Application Security Testing (SAST)
- Secret detection in code
- Dependency vulnerability scanning
- Automated remediation suggestions
- CI/CD integration with GitHub issues

## Features

- 🔍 **Multi-Scanner Support** - Semgrep, Bandit, custom rules
- 🔐 **Secret Detection** - API keys, passwords, tokens, private keys
- 📦 **Dependency Scanning** - pip-audit, npm audit integration
- 🛠️ **Auto-Remediation** - Suggested fixes for common issues
- 📊 **Multiple Report Formats** - HTML, JSON, SARIF, Markdown
- 🐛 **GitHub Integration** - Auto-create issues for findings

## Installation

```bash
cd skill7-security-oracle
pip install -r requirements.txt

# Optional: Install additional scanners
pip install semgrep bandit pip-audit
npm install -g npm  # For npm audit
```

## Quick Start

```python
from src.scanner import SecurityScanner
from src.reporter import SecurityReporter
from src.remediator import Remediator

# Initialize scanner
scanner = SecurityScanner()

# Run comprehensive scan
result = scanner.scan("./src", scanners=['all'])

# Generate report
reporter = SecurityReporter(result)
reporter.display_console()
reporter.save("report.html", "html")

# Get remediation suggestions
remediator = Remediator()
suggestions = remediator.generate_suggestions(result.vulnerabilities)
remediator.display_suggestions(suggestions)

# Create GitHub issues for critical findings
reporter.create_github_issue(
    "owner/repo",
    github_token="your_token"
)
```

## Core Components

### SecurityScanner

Main scanner orchestrating multiple security scanning methods.

```python
from src.scanner import SecurityScanner, Severity, VulnCategory

scanner = SecurityScanner(rules_dir="./custom_rules")

# Run specific scanners
result = scanner.scan("./src", scanners=['semgrep', 'secrets'])

# Or run all scanners
result = scanner.scan("./src", scanners=['all'])

# Access results
print(f"Found {len(result.vulnerabilities)} issues")
print(f"Critical: {result.critical_count}")
print(f"High: {result.high_count}")

# Filter by severity
critical = result.get_by_severity(Severity.CRITICAL)
sql_injection = result.get_by_category(VulnCategory.SQL_INJECTION)
```

### SecurityReporter

Generates security reports in various formats.

```python
from src.reporter import SecurityReporter

reporter = SecurityReporter(result)

# Console display
reporter.display_console()

# HTML report with interactive filtering
reporter.save("security_report.html", "html")

# JSON for programmatic use
reporter.save("security_report.json", "json")

# SARIF for GitHub/CodeQL integration
reporter.save("security_report.sarif", "sarif")

# Markdown for documentation
reporter.save("security_report.md", "markdown")

# Create GitHub issues
reporter.create_github_issue(
    "owner/repo",
    github_token="ghp_...",
    vuln=None  # Create for all critical/high, or specify one
)
```

### Remediator

Provides automated remediation suggestions.

```python
from src.remediator import Remediator

remediator = Remediator()

# Generate suggestions
suggestions = remediator.generate_suggestions(result.vulnerabilities)

# Display suggestions
remediator.display_suggestions(suggestions)

# Apply automatic fixes (where safe)
for vuln in result.vulnerabilities:
    if vuln.id in remediator.suggestions:
        suggestion = remediator.suggestions[vuln.id][0]
        remediator.apply_fix(vuln.file_path, vuln, suggestion)

# Generate patch file
patch = remediator.generate_patch(suggestions)
with open("security_patch.md", "w") as f:
    f.write(patch)
```

## Supported Vulnerability Types

| Category | Description | Detection Methods |
|----------|-------------|-------------------|
| SQL Injection | Unsafe SQL query construction | Semgrep, custom rules |
| XSS | Cross-site scripting vulnerabilities | Semgrep, custom rules |
| Command Injection | Unsafe shell command execution | Bandit, Semgrep |
| Path Traversal | Directory traversal attacks | Custom rules |
| Hardcoded Secrets | API keys, passwords in code | Regex patterns, detect-secrets |
| Weak Cryptography | MD5, SHA1, weak algorithms | Bandit |
| Insecure Deserialization | Pickle, yaml.load | Bandit |
| Dependency Vulns | Known vulnerable packages | pip-audit, npm audit |
| CSRF | Missing CSRF protection | Custom rules |
| CORS Misconfig | Overly permissive CORS | Custom rules |

## CLI Usage

```bash
# Run full scan
python -m src.scanner --input ./src --output report.html

# Run specific scanner
python -m src.scanner --input ./src --scanner secrets --output report.json

# Generate remediation patch
python -m src.remediator --report report.json --output patch.md

# Watch mode - scan on file changes
python -m src.scanner --input ./src --watch
```

## Custom Rules

Create custom Semgrep-style rules in `src/rules/`:

```yaml
rules:
  - id: my-custom-rule
    languages:
      - python
    message: Description of the issue
    severity: ERROR
    metadata:
      cwe: "CWE-XXX: Description"
    pattern: dangerous_function($X)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r skill7-security-oracle/requirements.txt
          pip install semgrep bandit pip-audit
      
      - name: Run security scan
        run: |
          python -c "
          from src.scanner import SecurityScanner
          from src.reporter import SecurityReporter
          
          scanner = SecurityScanner()
          result = scanner.scan('.', scanners=['all'])
          
          reporter = SecurityReporter(result)
          reporter.save('security-report.html', 'html')
          reporter.save('security-report.sarif', 'sarif')
          
          # Fail if critical vulnerabilities found
          if result.critical_count > 0:
              print(f'::error::{result.critical_count} critical vulnerabilities found')
              exit(1)
          "
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: security-report.sarif
      
      - name: Create GitHub Issues
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -c "
          from src.scanner import SecurityScanner
          from src.reporter import SecurityReporter
          
          scanner = SecurityScanner()
          result = scanner.scan('.')
          reporter = SecurityReporter(result)
          reporter.create_github_issue(
              '${{ github.repository }}',
              '${{ secrets.GITHUB_TOKEN }}'
          )
          "
```

## Report Formats

### HTML Report

Interactive report with:
- Severity filtering
- Search functionality
- Code highlighting
- Remediation guidance
- References and CWE links

### SARIF Report

Standard format for:
- GitHub Advanced Security
- Azure DevOps
- VS Code integration
- CodeQL compatibility

### Markdown Report

Perfect for:
- Pull request comments
- Documentation
- Issue descriptions
- Email reports

## Severity Levels

| Level | CVSS Range | Action |
|-------|------------|--------|
| Critical | 9.0-10.0 | Fix immediately |
| High | 7.0-8.9 | Fix before release |
| Medium | 4.0-6.9 | Fix in next sprint |
| Low | 0.1-3.9 | Fix when convenient |
| Info | 0.0 | Informational |

## Secret Detection Patterns

The scanner detects:
- AWS Access Keys & Secret Keys
- GitHub Personal Access Tokens
- Slack Tokens
- Private Keys (RSA, EC, DSA)
- Generic API Keys
- Database URLs
- JWT Tokens
- Passwords in code

## Remediation Examples

### SQL Injection
```python
# BAD
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### Hardcoded Secrets
```python
# BAD
API_KEY = "sk-1234567890abcdef"

# GOOD
import os
API_KEY = os.getenv("API_KEY")
```

### XSS Prevention
```javascript
// BAD
element.innerHTML = userInput;

// GOOD
element.textContent = userInput;
```

## Configuration

### Environment Variables

```bash
SECURITY_RULES_DIR=./custom_rules
SECURITY_FAIL_ON=high  # critical, high, medium, low
SECURITY_GITHUB_TOKEN=ghp_...
```

### Scanner Options

```python
scanner = SecurityScanner(
    rules_dir="./my_rules",  # Custom rules
)

# Available scanners:
# - 'semgrep': Pattern-based analysis
# - 'bandit': Python-specific issues
# - 'secrets': Hardcoded credentials
# - 'custom': Custom rule files
# - 'dependencies': Vulnerable packages
# - 'all': Run everything
```

## Testing

```bash
# Run tests
pytest tests/

# Run with sample vulnerable code
python examples/scan_vulnerable_app.py
```

## Examples

See the `examples/` directory:

- `basic_scan.py` - Simple security scan
- `ci_integration.py` - CI/CD pipeline setup
- `custom_rules.py` - Adding custom detection rules
- `auto_remediation.py` - Automated fix application

## License

MIT - RobeetsDay Project