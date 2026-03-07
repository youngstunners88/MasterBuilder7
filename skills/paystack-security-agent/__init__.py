"""
Paystack Security Agent
A specialized sub-agent for comprehensive security audits of Paystack payment integrations.

Usage:
    from paystack_security_agent import PaystackSecurityAgent, SecurityReport, SeverityLevel
    
    # Initialize agent
    agent = PaystackSecurityAgent(enable_auto_fix=True)
    
    # Audit webhook handler
    report = agent.audit_webhook_handler(webhook_code, "webhook.py")
    
    # Audit API integration
    report = agent.audit_api_integration(api_code, "api.py")
    
    # Full codebase audit
    report = agent.full_audit("/path/to/codebase")
    
    # Validate webhook signature
    is_valid = agent.validate_webstack_signature(payload, signature, secret)
    
    # Generate markdown report
    print(report.to_markdown())
"""

from .paystack_security_agent import (
    PaystackSecurityAgent,
    SecurityFinding,
    SecurityReport,
    SeverityLevel,
    IssueType,
    VULNERABLE_WEBHOOK_CODE,
    VULNERABLE_API_CODE,
    SECURE_WEBHOOK_EXAMPLE,
    demo,
)

__version__ = "1.0.0"
__author__ = "MasterBuilder7"

__all__ = [
    "PaystackSecurityAgent",
    "SecurityFinding",
    "SecurityReport",
    "SeverityLevel",
    "IssueType",
    "VULNERABLE_WEBHOOK_CODE",
    "VULNERABLE_API_CODE",
    "SECURE_WEBHOOK_EXAMPLE",
    "demo",
]
