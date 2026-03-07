# Paystack Security Agent

A specialized sub-agent for comprehensive security audits of Paystack payment integrations. This agent performs automated security analysis and provides auto-fix capabilities for common vulnerabilities.

## Features

### Security Checks
- ✅ **Webhook Signature Validation** (HMAC-SHA512)
- ✅ **API Key Exposure Detection** (sk_live_, sk_test_)
- ✅ **HTTPS Enforcement Checks**
- ✅ **Input Validation for Payment Amounts**
- ✅ **Idempotency Key Implementation**
- ✅ **Callback URL Validation**
- ✅ **Secret Key Storage Security**
- ✅ **PCI-DSS Compliance Checks**
- ✅ **SQL Injection Detection**
- ✅ **Sensitive Data Logging Detection**
- ✅ **Rate Limiting Verification**

### Auto-Fix Capabilities
- 🔧 Add webhook signature validation
- 🔧 Remove hardcoded keys (replace with env vars)
- 🔧 Add HTTPS enforcement
- 🔧 Add input validation
- 🔧 Add idempotency keys
- 🔧 Mask sensitive data in logs

## Installation

```bash
# Copy the agent to your project
cp -r paystack-security-agent /path/to/your/project/

# Or use directly
python paystack_security_agent.py
```

## Quick Start

```python
from paystack_security_agent import PaystackSecurityAgent

# Initialize the agent
agent = PaystackSecurityAgent(enable_auto_fix=True)

# Audit your webhook handler
with open('webhook_handler.py', 'r') as f:
    code = f.read()

report = agent.audit_webhook_handler(code, "webhook_handler.py")

# View results
print(f"Security Score: {report.overall_score}/100")
print(f"Critical Issues: {report.critical_count}")

# Print detailed report
print(report.to_markdown())
```

## Usage Examples

### 1. Webhook Handler Audit

```python
webhook_code = '''
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    # Process webhook...
'''

report = agent.audit_webhook_handler(webhook_code, "webhook.py")
```

### 2. API Integration Audit

```python
api_code = '''
def process_payment(amount, email):
    response = requests.post(
        'https://api.paystack.co/charge',
        headers={'Authorization': 'Bearer sk_live_...'},
        json={'amount': amount, 'email': email}
    )
'''

report = agent.audit_api_integration(api_code, "payment.py")
```

### 3. Validate Webhook Signature

```python
payload = request.get_data()
signature = request.headers.get('x-paystack-signature')
secret = os.getenv('PAYSTACK_SECRET_KEY')

is_valid = agent.validate_webhook_signature(payload, signature, secret)

if not is_valid:
    return "Invalid signature", 401
```

### 4. Full Codebase Audit

```python
# Audit entire codebase
report = agent.full_audit("/path/to/your/project")

# Save report
with open('security_report.md', 'w') as f:
    f.write(report.to_markdown())
```

### 5. Scan for Exposed Keys

```python
files = ['app.py', 'config.py', 'utils.py']
findings = agent.scan_for_exposed_keys(files)

for finding in findings:
    print(f"{finding.severity.value}: {finding.title} at line {finding.line_number}")
```

### 6. Fix Security Issues

```python
# Auto-fix enabled
agent = PaystackSecurityAgent(enable_auto_fix=True)
report = agent.audit_webhook_handler(vulnerable_code, "webhook.py")

# Get fixed code
if report.fixed_code:
    with open('webhook_fixed.py', 'w') as f:
        f.write(report.fixed_code)
```

## Security Report Structure

```python
{
    "overall_score": 75,  # 0-100
    "scan_timestamp": "2024-01-01T12:00:00",
    "files_scanned": 10,
    "summary": {
        "critical": 0,
        "high": 2,
        "medium": 3,
        "low": 5,
        "total": 10
    },
    "pci_compliance_status": "COMPLIANT",
    "findings": [
        {
            "issue_type": "missing_webhook_validation",
            "severity": "CRITICAL",
            "title": "Missing Webhook Signature Validation",
            "description": "...",
            "location": "webhook.py",
            "line_number": 15,
            "auto_fixable": True,
            "fixed_code": "..."
        }
    ],
    "recommendations": [
        "Implement webhook signature validation...",
        "Move API keys to environment variables..."
    ]
}
```

## Severity Levels

| Level | Description | Action Required |
|-------|-------------|-----------------|
| 🔴 CRITICAL | Data breach risk | Immediate action |
| 🟠 HIGH | Significant vulnerability | Fix within 24 hours |
| 🟡 MEDIUM | Moderate risk | Fix within 1 week |
| 🟢 LOW | Minor concern | Fix when convenient |
| ℹ️ INFO | Informational | Review |

## Paystack-Specific Rules

### Webhook Security
- Must verify `x-paystack-signature` header
- Use HMAC-SHA512 for signature validation
- Raw payload must be preserved before JSON parsing

### API Key Security
- Never hardcode secret keys
- Use environment variables: `os.getenv('PAYSTACK_SECRET_KEY')`
- Never log secret keys
- Rotate keys immediately if exposed

### HTTPS Enforcement
- All callback URLs must use HTTPS
- Webhook endpoints must enforce HTTPS in production
- Redirect HTTP to HTTPS

### Payment Validation
- Validate amounts are positive numbers
- Check minimum/maximum limits
- Verify currency codes
- Validate email format

### Idempotency
- Required for transfers and bulk charges
- Generate unique keys per request
- Include in `Idempotency-Key` header

## PCI-DSS Compliance

The agent checks for:
- ✅ No card data storage
- ✅ No CVV logging
- ✅ No PIN logging
- ✅ Encrypted transmission (HTTPS)
- ✅ Secure key management

## Running the Demo

```bash
cd /home/teacherchris37/MasterBuilder7/skills/paystack-security-agent
python paystack_security_agent.py
```

This will run a comprehensive demo showing:
1. Vulnerable webhook detection
2. API key exposure scanning
3. Webhook signature validation
4. Secure code comparison
5. Report generation

## Integration Examples

### Flask Webhook Handler (Secure)

```python
import os
import hmac
import hashlib
from flask import Flask, request, abort
from paystack_security_agent import PaystackSecurityAgent

app = Flask(__name__)
agent = PaystackSecurityAgent()

def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    secret = os.getenv('PAYSTACK_SECRET_KEY')
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route('/webhook/paystack', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('x-paystack-signature')
    payload = request.get_data()
    
    if not verify_paystack_signature(payload, signature):
        abort(401)
    
    data = request.get_json()
    # Process webhook...
    return 'OK', 200

# Audit your code
@app.route('/admin/security-audit', methods=['POST'])
def security_audit():
    with open(__file__, 'r') as f:
        report = agent.audit_webhook_handler(f.read(), __file__)
    return report.to_dict()
```

### FastAPI Integration

```python
from fastapi import FastAPI, Request, HTTPException
from paystack_security_agent import PaystackSecurityAgent

app = FastAPI()
agent = PaystackSecurityAgent()

@app.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    signature = request.headers.get('x-paystack-signature')
    payload = await request.body()
    secret = os.getenv('PAYSTACK_SECRET_KEY')
    
    if not agent.validate_webhook_signature(payload, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = await request.json()
    # Process...
    return {"status": "success"}
```

## CI/CD Integration

```yaml
# .github/workflows/security.yml
name: Paystack Security Audit

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Run Paystack Security Audit
        run: |
          python -c "
          from paystack_security_agent import PaystackSecurityAgent
          agent = PaystackSecurityAgent()
          report = agent.full_audit('.')
          print(report.to_markdown())
          if report.critical_count > 0 or report.high_count > 0:
              exit(1)
          "
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please ensure:
1. Code follows PEP 8
2. Tests pass
3. Documentation is updated
4. Security rules are well-tested

## Support

For issues and feature requests, please open an issue on the repository.
