# Skill: Paystack Security Agent

## Description

A specialized sub-agent for comprehensive security audits of Paystack payment integrations. Performs automated security analysis with auto-fix capabilities.

## Capabilities

### Security Checks
- Webhook signature validation (HMAC-SHA512)
- API key exposure detection
- HTTPS enforcement verification
- Input validation checks
- Idempotency key implementation
- PCI-DSS compliance checks
- SQL injection detection
- Sensitive data logging detection

### Auto-Fix Capabilities
- Add webhook signature validation
- Replace hardcoded keys with environment variables
- Add HTTPS enforcement
- Add input validation
- Add idempotency keys

## Usage

```python
from paystack_security_agent import PaystackSecurityAgent

# Initialize
agent = PaystackSecurityAgent(enable_auto_fix=True)

# Audit webhook handler
report = agent.audit_webhook_handler(code, "webhook.py")

# Audit API integration  
report = agent.audit_api_integration(code, "payment.py")

# Full codebase audit
report = agent.full_audit("/path/to/codebase")

# Validate webhook signature
is_valid = agent.validate_webhook_signature(payload, signature, secret)

# Generate report
print(report.to_markdown())
```

## API Reference

### Classes

#### PaystackSecurityAgent
- `__init__(enable_auto_fix=False)` - Initialize agent
- `audit_webhook_handler(code, filename)` - Audit webhook code
- `audit_api_integration(code, filename)` - Audit API code
- `audit_transaction_flow(code, filename)` - Audit transaction code
- `validate_webhook_signature(payload, signature, secret)` - Verify HMAC-SHA512
- `scan_for_exposed_keys(files)` - Scan files for API keys
- `check_pci_compliance(codebase_path)` - Check PCI-DSS compliance
- `full_audit(codebase_path)` - Complete codebase audit

#### SecurityReport
- `to_dict()` - Convert to dictionary
- `to_markdown()` - Generate markdown report

### Enums

#### SeverityLevel
- CRITICAL - Data breach risk
- HIGH - Significant vulnerability  
- MEDIUM - Moderate risk
- LOW - Minor concern

#### IssueType
- EXPOSED_API_KEY
- MISSING_WEBHOOK_VALIDATION
- HTTP_CALLBACK
- MISSING_HTTPS
- NO_INPUT_VALIDATION
- MISSING_IDEMPOTENCY
- SENSITIVE_DATA_LOGGING
- SQL_INJECTION_RISK

## Examples

See `example_usage.py` for complete examples.

## Files

- `paystack_security_agent.py` - Main agent implementation
- `test_agent.py` - Unit tests
- `example_usage.py` - Usage examples
- `README.md` - Full documentation

## Dependencies

- Python 3.7+
- Standard library only (no external dependencies)

## Version

1.0.0
