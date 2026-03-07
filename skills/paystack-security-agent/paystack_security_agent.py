#!/usr/bin/env python3
"""
Paystack Security Agent
A specialized sub-agent for comprehensive security audits of Paystack payment integrations.

This agent performs security checks for:
- Webhook signature validation (HMAC-SHA512)
- API key security and exposure detection
- Transaction flow verification
- PCI-DSS compliance checks
- Vulnerability scanning and auto-fix capabilities

Author: MasterBuilder7
Version: 1.0.0
"""

import ast
import hashlib
import hmac
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable


class SeverityLevel(Enum):
    """Security issue severity levels."""
    CRITICAL = "CRITICAL"  # Immediate action required - data breach risk
    HIGH = "HIGH"          # Significant security vulnerability
    MEDIUM = "MEDIUM"      # Moderate risk, should be fixed
    LOW = "LOW"            # Minor security concern, good practice
    INFO = "INFO"          # Informational finding


class IssueType(Enum):
    """Types of security issues."""
    EXPOSED_API_KEY = "exposed_api_key"
    MISSING_WEBHOOK_VALIDATION = "missing_webhook_validation"
    HTTP_CALLBACK = "http_callback"
    MISSING_HTTPS = "missing_https"
    NO_INPUT_VALIDATION = "no_input_validation"
    MISSING_IDEMPOTENCY = "missing_idempotency"
    SENSITIVE_DATA_LOGGING = "sensitive_data_logging"
    INSECURE_KEY_STORAGE = "insecure_key_storage"
    MISSING_AMOUNT_VALIDATION = "missing_amount_validation"
    WEAK_SIGNATURE_ALGORITHM = "weak_signature_algorithm"
    HARDCODED_SECRET = "hardcoded_secret"
    NO_RATE_LIMITING = "no_rate_limiting"
    SQL_INJECTION_RISK = "sql_injection_risk"
    XSS_VULNERABILITY = "xss_vulnerability"
    INSECURE_RANDOM = "insecure_random"


@dataclass
class SecurityFinding:
    """Individual security finding."""
    issue_type: IssueType
    severity: SeverityLevel
    title: str
    description: str
    location: str
    line_number: Optional[int] = None
    snippet: Optional[str] = None
    recommendation: str = ""
    auto_fixable: bool = False
    fixed_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "line_number": self.line_number,
            "snippet": self.snippet,
            "recommendation": self.recommendation,
            "auto_fixable": self.auto_fixable,
            "fixed_code": self.fixed_code
        }


@dataclass
class SecurityReport:
    """Comprehensive security audit report."""
    overall_score: int  # 0-100
    findings: List[SecurityFinding] = field(default_factory=list)
    pci_compliance_status: str = "UNKNOWN"
    pci_compliance_details: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    fixed_code: Optional[str] = None
    scan_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    files_scanned: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    def __post_init__(self):
        self.critical_count = sum(1 for f in self.findings if f.severity == SeverityLevel.CRITICAL)
        self.high_count = sum(1 for f in self.findings if f.severity == SeverityLevel.HIGH)
        self.medium_count = sum(1 for f in self.findings if f.severity == SeverityLevel.MEDIUM)
        self.low_count = sum(1 for f in self.findings if f.severity == SeverityLevel.LOW)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "scan_timestamp": self.scan_timestamp,
            "files_scanned": self.files_scanned,
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "total": len(self.findings)
            },
            "pci_compliance_status": self.pci_compliance_status,
            "pci_compliance_details": self.pci_compliance_details,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations,
            "fixed_code": self.fixed_code
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        md = f"""# Paystack Security Audit Report

**Generated:** {self.scan_timestamp}
**Overall Security Score:** {self.overall_score}/100

## Summary
| Severity | Count |
|----------|-------|
| 🔴 Critical | {self.critical_count} |
| 🟠 High | {self.high_count} |
| 🟡 Medium | {self.medium_count} |
| 🟢 Low | {self.low_count} |

## PCI-DSS Compliance Status: {self.pci_compliance_status}

"""
        if self.pci_compliance_details:
            md += "### Details:\n"
            for detail in self.pci_compliance_details:
                md += f"- {detail}\n"
            md += "\n"

        if self.findings:
            md += "## Findings\n\n"
            for i, finding in enumerate(self.findings, 1):
                emoji = {
                    SeverityLevel.CRITICAL: "🔴",
                    SeverityLevel.HIGH: "🟠",
                    SeverityLevel.MEDIUM: "🟡",
                    SeverityLevel.LOW: "🟢",
                    SeverityLevel.INFO: "ℹ️"
                }.get(finding.severity, "⚪")
                
                md += f"### {i}. {emoji} {finding.title}\n"
                md += f"**Severity:** {finding.severity.value}\n\n"
                md += f"**Location:** `{finding.location}`"
                if finding.line_number:
                    md += f":{finding.line_number}"
                md += "\n\n"
                md += f"**Description:** {finding.description}\n\n"
                
                if finding.snippet:
                    md += f"**Code:**\n```python\n{finding.snippet}\n```\n\n"
                
                md += f"**Recommendation:** {finding.recommendation}\n\n"
                
                if finding.auto_fixable:
                    md += f"✅ **Auto-fix available**\n\n"
                    if finding.fixed_code:
                        md += f"**Fixed Code:**\n```python\n{finding.fixed_code}\n```\n\n"
                
                md += "---\n\n"

        if self.recommendations:
            md += "## General Recommendations\n\n"
            for i, rec in enumerate(self.recommendations, 1):
                md += f"{i}. {rec}\n"

        return md


class PaystackSecurityAgent:
    """
    Comprehensive security agent for Paystack payment integrations.
    
    Performs security audits including:
    - Webhook signature validation (HMAC-SHA512)
    - API key exposure detection
    - Transaction flow verification
    - PCI-DSS compliance checks
    - Auto-fix capabilities for common issues
    """

    # Paystack API key patterns
    SECRET_KEY_PATTERNS = [
        r'sk_live_xxxxx[a-zA-Z0-9]{48}',
        r'sk_test_[a-zA-Z0-9]{48}',
        r'pk_live_[a-zA-Z0-9]{48}',
        r'pk_test_[a-zA-Z0-9]{48}',
    ]

    # Environment variable patterns for secure key storage
    ENV_VAR_PATTERNS = [
        r'os\.getenv\([\'"]PAYSTACK_SECRET_KEY[\'"]\)',
        r'os\.environ\.get\([\'"]PAYSTACK_SECRET_KEY[\'"]\)',
        r'os\.environ\[[\'"]PAYSTACK_SECRET_KEY[\'"]\]',
        r'process\.env\.PAYSTACK_SECRET_KEY',
        r'\.env\.PAYSTACK_SECRET_KEY',
    ]

    def __init__(self, enable_auto_fix: bool = False):
        """
        Initialize the Paystack Security Agent.
        
        Args:
            enable_auto_fix: Whether to automatically generate fixed code
        """
        self.enable_auto_fix = enable_auto_fix
        self.findings: List[SecurityFinding] = []
        self._security_rules: List[Callable[[str, str], List[SecurityFinding]]] = [
            self._check_exposed_api_keys,
            self._check_webhook_validation,
            self._check_https_enforcement,
            self._check_input_validation,
            self._check_idempotency,
            self._check_sensitive_logging,
            self._check_key_storage,
            self._check_amount_validation,
            self._check_rate_limiting,
            self._check_sql_injection,
        ]

    def audit_webhook_handler(self, code: str, filename: str = "webhook.py") -> SecurityReport:
        """
        Audit webhook handler code for security issues.
        
        Args:
            code: Python code string to audit
            filename: Name of the file being audited
            
        Returns:
            SecurityReport with findings and recommendations
        """
        self.findings = []
        
        # Run all security checks
        for rule in self._security_rules:
            findings = rule(code, filename)
            self.findings.extend(findings)
        
        # Specific webhook checks
        self._check_webhook_specific_issues(code, filename)
        
        return self._generate_report(code, filename)

    def audit_api_integration(self, code: str, filename: str = "api_integration.py") -> SecurityReport:
        """
        Audit API integration code for security issues.
        
        Args:
            code: Python code string to audit
            filename: Name of the file being audited
            
        Returns:
            SecurityReport with findings and recommendations
        """
        self.findings = []
        
        # Run all security checks
        for rule in self._security_rules:
            findings = rule(code, filename)
            self.findings.extend(findings)
        
        # Specific API integration checks
        self._check_api_specific_issues(code, filename)
        
        return self._generate_report(code, filename)

    def audit_transaction_flow(self, code: str, filename: str = "transaction.py") -> SecurityReport:
        """
        Audit transaction flow code for security issues.
        
        Args:
            code: Python code string to audit
            filename: Name of the file being audited
            
        Returns:
            SecurityReport with findings and recommendations
        """
        self.findings = []
        
        # Run all security checks
        for rule in self._security_rules:
            findings = rule(code, filename)
            self.findings.extend(findings)
        
        # Specific transaction checks
        self._check_transaction_specific_issues(code, filename)
        
        return self._generate_report(code, filename)

    def validate_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        secret: str
    ) -> bool:
        """
        Validate Paystack webhook signature using HMAC-SHA512.
        
        Paystack signs webhook events with your secret key using HMAC-SHA512.
        The signature is sent in the x-paystack-signature header.
        
        Args:
            payload: Raw request body (JSON string)
            signature: Signature from x-paystack-signature header
            secret: Your Paystack secret key
            
        Returns:
            True if signature is valid, False otherwise
            
        Example:
            >>> agent = PaystackSecurityAgent()
            >>> is_valid = agent.validate_webhook_signature(
            ...     payload='{"event": "charge.success"}',
            ...     signature='abc123...',
            ...     secret='sk_test_...'
            ... )
        """
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False

    def scan_for_exposed_keys(self, files: List[str]) -> List[SecurityFinding]:
        """
        Scan files for exposed Paystack API keys.
        
        Args:
            files: List of file paths to scan
            
        Returns:
            List of findings for exposed keys
        """
        findings = []
        
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern in self.SECRET_KEY_PATTERNS:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            key_type = "test" if "test" in match.group() else "live"
                            findings.append(SecurityFinding(
                                issue_type=IssueType.EXPOSED_API_KEY,
                                severity=SeverityLevel.CRITICAL if key_type == "live" else SeverityLevel.HIGH,
                                title=f"Exposed Paystack {key_type.upper()} Secret Key",
                                description=f"A Paystack {key_type} secret key was found hardcoded in the source code. "
                                          f"This is a critical security risk as anyone with access to the code "
                                          f"can perform operations on your Paystack account.",
                                location=filepath,
                                line_number=line_num,
                                snippet=line.strip(),
                                recommendation="Move the API key to environment variables and use os.getenv() to retrieve it. "
                                             "If this is a live key, immediately revoke it from your Paystack dashboard "
                                             "and generate a new one.",
                                auto_fixable=True,
                                fixed_code=self._generate_key_fix(line, match.group())
                            ))
            except Exception as e:
                findings.append(SecurityFinding(
                    issue_type=IssueType.EXPOSED_API_KEY,
                    severity=SeverityLevel.INFO,
                    title="File Scan Error",
                    description=f"Could not scan file {filepath}: {str(e)}",
                    location=filepath,
                    recommendation="Check file permissions and encoding."
                ))
        
        return findings

    def check_pci_compliance(self, codebase_path: str) -> Tuple[str, List[str]]:
        """
        Check PCI-DSS compliance for the codebase.
        
        Args:
            codebase_path: Path to the codebase directory
            
        Returns:
            Tuple of (compliance_status, compliance_details)
        """
        compliance_details = []
        issues = []
        
        # Check for card data handling
        files = self._get_python_files(codebase_path)
        
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for card number patterns
                if re.search(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b', content):
                    issues.append(f"Potential card data found in {filepath}")
                
                # Check for CVV patterns
                if re.search(r'cvv|cvv2|security.?code', content, re.IGNORECASE):
                    if re.search(r'\b\d{3,4}\b', content):
                        issues.append(f"Potential CVV data found in {filepath}")
                
                # Check for logging of sensitive data
                if re.search(r'(log|print|debug).*(card|cvv|pin|password)', content, re.IGNORECASE):
                    issues.append(f"Potential logging of sensitive data in {filepath}")
                    
            except Exception:
                pass
        
        # Evaluate compliance
        if not issues:
            status = "COMPLIANT"
            compliance_details.append("No card data storage detected")
            compliance_details.append("Using Paystack for payment processing (SAQ A eligible)")
        elif len(issues) <= 2:
            status = "MINOR_ISSUES"
            compliance_details.extend(issues)
            compliance_details.append("Review findings and address before audit")
        else:
            status = "NON_COMPLIANT"
            compliance_details.extend(issues)
            compliance_details.append("Multiple compliance issues found - immediate action required")
        
        return status, compliance_details

    def generate_security_report(self, findings: List[SecurityFinding]) -> SecurityReport:
        """
        Generate a comprehensive security report from findings.
        
        Args:
            findings: List of security findings
            
        Returns:
            SecurityReport with overall score and recommendations
        """
        # Calculate score based on findings
        score = 100
        for finding in findings:
            if finding.severity == SeverityLevel.CRITICAL:
                score -= 25
            elif finding.severity == SeverityLevel.HIGH:
                score -= 15
            elif finding.severity == SeverityLevel.MEDIUM:
                score -= 5
            elif finding.severity == SeverityLevel.LOW:
                score -= 1
        
        score = max(0, score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings)
        
        return SecurityReport(
            overall_score=score,
            findings=findings,
            recommendations=recommendations
        )

    def fix_security_issue(self, issue_type: IssueType, code: str) -> str:
        """
        Auto-fix a security issue in the code.
        
        Args:
            issue_type: Type of security issue to fix
            code: Code containing the issue
            
        Returns:
            Fixed code string
        """
        fixers = {
            IssueType.EXPOSED_API_KEY: self._fix_exposed_key,
            IssueType.MISSING_WEBHOOK_VALIDATION: self._fix_webhook_validation,
            IssueType.HTTP_CALLBACK: self._fix_http_callback,
            IssueType.MISSING_HTTPS: self._fix_https,
            IssueType.NO_INPUT_VALIDATION: self._fix_input_validation,
            IssueType.MISSING_IDEMPOTENCY: self._fix_idempotency,
            IssueType.SENSITIVE_DATA_LOGGING: self._fix_sensitive_logging,
            IssueType.MISSING_AMOUNT_VALIDATION: self._fix_amount_validation,
        }
        
        fixer = fixers.get(issue_type)
        if fixer:
            return fixer(code)
        return code

    # ==================== Internal Security Check Methods ====================

    def _check_exposed_api_keys(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for hardcoded API keys in code."""
        findings = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern in self.SECRET_KEY_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    key_type = "test" if "test" in match.group() else "live"
                    findings.append(SecurityFinding(
                        issue_type=IssueType.EXPOSED_API_KEY,
                        severity=SeverityLevel.CRITICAL if key_type == "live" else SeverityLevel.HIGH,
                        title=f"Exposed Paystack {key_type.upper()} Secret Key",
                        description=f"A Paystack {key_type} secret key is hardcoded in the source code. "
                                  f"This poses a critical security risk.",
                        location=filename,
                        line_number=line_num,
                        snippet=line.strip(),
                        recommendation="Move the API key to environment variables. Use os.getenv('PAYSTACK_SECRET_KEY'). "
                                     "If this is a live key, revoke it immediately in your Paystack dashboard.",
                        auto_fixable=True,
                        fixed_code=self._generate_key_fix(line, match.group())
                    ))
        
        return findings

    def _check_webhook_validation(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for webhook signature validation."""
        findings = []
        
        # Check if webhook handler exists
        if 'webhook' in code.lower() or 'paystack' in code.lower():
            # Check for signature validation
            has_signature_check = any(pattern in code for pattern in [
                'x-paystack-signature',
                'paystack-signature',
                'signature',
                'hmac',
                'validate_webhook'
            ])
            
            if not has_signature_check:
                findings.append(SecurityFinding(
                    issue_type=IssueType.MISSING_WEBHOOK_VALIDATION,
                    severity=SeverityLevel.CRITICAL,
                    title="Missing Webhook Signature Validation",
                    description="The webhook handler does not validate the Paystack webhook signature. "
                              "This allows attackers to send fake webhook events to your application.",
                    location=filename,
                    recommendation="Implement HMAC-SHA512 signature validation using the secret key. "
                                 "Verify the x-paystack-signature header against the computed signature.",
                    auto_fixable=True,
                    fixed_code=self._generate_webhook_fix()
                ))
            
            # Check for weak signature validation
            if 'sha1' in code.lower() or 'sha256' in code.lower():
                if 'sha512' not in code.lower():
                    findings.append(SecurityFinding(
                        issue_type=IssueType.WEAK_SIGNATURE_ALGORITHM,
                        severity=SeverityLevel.HIGH,
                        title="Weak Signature Algorithm",
                        description="The webhook validation uses a weak hashing algorithm. "
                                  "Paystack requires HMAC-SHA512.",
                        location=filename,
                        recommendation="Use hashlib.sha512 for webhook signature validation."
                    ))
        
        return findings

    def _check_https_enforcement(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for HTTPS enforcement in callbacks."""
        findings = []
        
        # Look for callback URLs
        callback_patterns = [
            r'callback_url["\']?\s*[:=]\s*["\']([^"\']+)',
            r'callback["\']?\s*[:=]\s*["\']([^"\']+)',
            r'webhook_url["\']?\s*[:=]\s*["\']([^"\']+)',
        ]
        
        for pattern in callback_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                url = match.group(1)
                if url.startswith('http://') and not url.startswith('http://localhost'):
                    findings.append(SecurityFinding(
                        issue_type=IssueType.HTTP_CALLBACK,
                        severity=SeverityLevel.HIGH,
                        title="Insecure HTTP Callback URL",
                        description=f"The callback URL uses HTTP instead of HTTPS: {url}",
                        location=filename,
                        snippet=f'callback_url = "{url}"',
                        recommendation="Always use HTTPS for callback URLs to prevent man-in-the-middle attacks.",
                        auto_fixable=True,
                        fixed_code=f'callback_url = "{url.replace("http://", "https://")}"'
                    ))
        
        # Check for HTTPS redirects/enforcement
        if 'https' not in code.lower() and ('callback' in code.lower() or 'webhook' in code.lower()):
            findings.append(SecurityFinding(
                issue_type=IssueType.MISSING_HTTPS,
                severity=SeverityLevel.MEDIUM,
                title="HTTPS Not Enforced",
                description="No HTTPS enforcement found for webhook/callback handlers.",
                location=filename,
                recommendation="Enforce HTTPS in production environments for all webhook endpoints."
            ))
        
        return findings

    def _check_input_validation(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for input validation in payment processing."""
        findings = []
        
        # Check for amount validation
        if 'amount' in code.lower():
            has_validation = any(pattern in code for pattern in [
                'try:',
                'except',
                'ValueError',
                'TypeError',
                'validate',
                'isinstance(amount',
                'float(amount)',
                'int(amount)'
            ])
            
            if not has_validation:
                findings.append(SecurityFinding(
                    issue_type=IssueType.NO_INPUT_VALIDATION,
                    severity=SeverityLevel.HIGH,
                    title="Missing Input Validation",
                    description="Payment amounts are processed without proper input validation. "
                              "This could lead to type errors or injection attacks.",
                    location=filename,
                    recommendation="Validate and sanitize all payment inputs. Use try-except blocks "
                                 "and validate amount is a positive number.",
                    auto_fixable=True
                ))
        
        return findings

    def _check_idempotency(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for idempotency key implementation."""
        findings = []
        
        # Check for transfer or charge operations
        if any(op in code for op in ['transfer', 'charge', 'refund', 'initiate']):
            has_idempotency = any(pattern in code for pattern in [
                'idempotency',
                'Idempotency-Key',
                'X-Idempotency-Key',
                'unique_key',
                'request_id'
            ])
            
            if not has_idempotency:
                findings.append(SecurityFinding(
                    issue_type=IssueType.MISSING_IDEMPOTENCY,
                    severity=SeverityLevel.MEDIUM,
                    title="Missing Idempotency Key",
                    description="Critical operations (transfers, charges) do not implement idempotency keys. "
                              "This can lead to duplicate transactions on network retries.",
                    location=filename,
                    recommendation="Generate unique idempotency keys for each transaction request "
                                 "and include them in the request headers.",
                    auto_fixable=True,
                    fixed_code=self._generate_idempotency_fix()
                ))
        
        return findings

    def _check_sensitive_logging(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for sensitive data in logs."""
        findings = []
        
        sensitive_patterns = [
            (r'(print|log|logger|debug)\(.*secret', "secret key logging"),
            (r'(print|log|logger|debug)\(.*password', "password logging"),
            (r'(print|log|logger|debug)\(.*cvv', "CVV logging"),
            (r'(print|log|logger|debug)\(.*card.*number', "card number logging"),
            (r'(print|log|logger|debug)\(.*pin', "PIN logging"),
        ]
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, description in sensitive_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        issue_type=IssueType.SENSITIVE_DATA_LOGGING,
                        severity=SeverityLevel.CRITICAL,
                        title="Sensitive Data in Logs",
                        description=f"Code appears to log {description}. This violates PCI-DSS compliance "
                                  "and exposes sensitive customer information.",
                        location=filename,
                        line_number=line_num,
                        snippet=line.strip(),
                        recommendation="Never log secret keys, passwords, CVV, PINs, or full card numbers. "
                                     "If needed for debugging, mask sensitive data.",
                        auto_fixable=True
                    ))
        
        return findings

    def _check_key_storage(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for secure API key storage."""
        findings = []
        
        # Check for environment variable usage
        has_env_var = any(pattern in code for pattern in self.ENV_VAR_PATTERNS)
        has_hardcoded = any(re.search(pattern, code) for pattern in self.SECRET_KEY_PATTERNS)
        
        if not has_env_var and not has_hardcoded:
            # Check if there are any API calls
            if 'paystack' in code.lower() or 'authorization' in code.lower():
                findings.append(SecurityFinding(
                    issue_type=IssueType.INSECURE_KEY_STORAGE,
                    severity=SeverityLevel.MEDIUM,
                    title="API Key Storage Not Verified",
                    description="Could not verify that API keys are stored securely in environment variables.",
                    location=filename,
                    recommendation="Store API keys in environment variables and access via os.getenv('PAYSTACK_SECRET_KEY')."
                ))
        
        return findings

    def _check_amount_validation(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for payment amount validation."""
        findings = []
        
        # Look for amount processing
        amount_patterns = [
            r'amount\s*=\s*',
            r'["\']amount["\']\s*:',
            r'\.amount',
        ]
        
        has_amount = any(re.search(pattern, code) for pattern in amount_patterns)
        
        if has_amount:
            has_validation = any(pattern in code for pattern in [
                'amount > 0',
                'amount <= 0',
                'amount >=',
                'amount_min',
                'amount_max',
                'validate_amount',
                'if amount',
            ])
            
            if not has_validation:
                findings.append(SecurityFinding(
                    issue_type=IssueType.MISSING_AMOUNT_VALIDATION,
                    severity=SeverityLevel.HIGH,
                    title="Missing Amount Validation",
                    description="Payment amounts are not validated before processing. "
                              "This could allow negative amounts, zero amounts, or extremely large values.",
                    location=filename,
                    recommendation="Validate amount is positive, within acceptable range, and is a valid number.",
                    auto_fixable=True,
                    fixed_code=self._generate_amount_validation_fix()
                ))
        
        return findings

    def _check_rate_limiting(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for rate limiting on payment endpoints."""
        findings = []
        
        if 'webhook' in code.lower() or 'callback' in code.lower() or 'charge' in code.lower():
            has_rate_limit = any(pattern in code for pattern in [
                'rate_limit',
                'RateLimit',
                'throttle',
                'Throttle',
                '@limit',
                'slowapi',
                'redis',
            ])
            
            if not has_rate_limit:
                findings.append(SecurityFinding(
                    issue_type=IssueType.NO_RATE_LIMITING,
                    severity=SeverityLevel.MEDIUM,
                    title="No Rate Limiting",
                    description="Payment endpoints lack rate limiting protection. "
                              "This makes them vulnerable to brute force and DDoS attacks.",
                    location=filename,
                    recommendation="Implement rate limiting on all payment-related endpoints. "
                                 "Use tools like slowapi, flask-limiter, or nginx rate limiting."
                ))
        
        return findings

    def _check_sql_injection(self, code: str, filename: str) -> List[SecurityFinding]:
        """Check for SQL injection vulnerabilities."""
        findings = []
        
        # Look for unsafe SQL patterns
        sql_patterns = [
            (r'execute\s*\(\s*["\'].*%s', "string formatting in SQL"),
            (r'execute\s*\(\s*f["\']', "f-string in SQL"),
            (r'execute\s*\(\s*["\'].*\+', "string concatenation in SQL"),
            (r'\.format\(.*\).*SELECT|INSERT|UPDATE|DELETE', "format() in SQL"),
        ]
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, description in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        issue_type=IssueType.SQL_INJECTION_RISK,
                        severity=SeverityLevel.CRITICAL,
                        title="SQL Injection Risk",
                        description=f"Potential SQL injection via {description}. "
                                  "User input may be directly included in SQL queries.",
                        location=filename,
                        line_number=line_num,
                        snippet=line.strip(),
                        recommendation="Use parameterized queries with placeholders (%s, ?) "
                                     "instead of string formatting."
                    ))
        
        return findings

    def _check_webhook_specific_issues(self, code: str, filename: str) -> None:
        """Additional checks specific to webhook handlers."""
        # Check for request body parsing
        if 'request' in code.lower() and ('body' in code.lower() or 'json' in code.lower()):
            # Check if raw body is preserved for signature validation
            if 'get_json()' in code and 'data' not in code.lower():
                self.findings.append(SecurityFinding(
                    issue_type=IssueType.MISSING_WEBHOOK_VALIDATION,
                    severity=SeverityLevel.HIGH,
                    title="Webhook Body Not Preserved",
                    description="The request body must be preserved as raw bytes for signature validation. "
                              "Using get_json() before signature check breaks validation.",
                    location=filename,
                    recommendation="Access request.data or request.get_data() before parsing JSON "
                                 "for signature validation."
                ))

    def _check_api_specific_issues(self, code: str, filename: str) -> None:
        """Additional checks specific to API integrations."""
        # Check for timeout settings
        if 'requests' in code or 'httpx' in code or 'urllib' in code:
            if 'timeout' not in code:
                self.findings.append(SecurityFinding(
                    issue_type=IssueType.NO_RATE_LIMITING,
                    severity=SeverityLevel.LOW,
                    title="No Request Timeout",
                    description="HTTP requests to Paystack API do not have timeout settings.",
                    location=filename,
                    recommendation="Always set timeouts on API requests to prevent hanging connections. "
                                 "Example: requests.post(url, json=data, timeout=30)"
                ))

    def _check_transaction_specific_issues(self, code: str, filename: str) -> None:
        """Additional checks specific to transaction flows."""
        # Check for transaction status verification
        if 'charge' in code.lower() or 'transaction' in code.lower():
            has_status_check = any(pattern in code for pattern in [
                'status',
                'success',
                'failed',
                'verify',
            ])
            
            if not has_status_check:
                self.findings.append(SecurityFinding(
                    issue_type=IssueType.NO_INPUT_VALIDATION,
                    severity=SeverityLevel.HIGH,
                    title="Transaction Status Not Verified",
                    description="Transaction status is not verified before processing. "
                              "Failed or pending transactions may be processed as successful.",
                    location=filename,
                    recommendation="Always verify transaction status from Paystack API before fulfilling orders."
                ))

    # ==================== Auto-Fix Methods ====================

    def _fix_exposed_key(self, code: str) -> str:
        """Replace hardcoded key with environment variable."""
        for pattern in self.SECRET_KEY_PATTERNS:
            code = re.sub(
                rf'["\']{pattern}["\']',
                "os.getenv('PAYSTACK_SECRET_KEY')",
                code
            )
        return f"import os\n{code}"

    def _fix_webhook_validation(self, code: str) -> str:
        """Add webhook signature validation."""
        validation_code = '''
def verify_paystack_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Paystack webhook signature."""
    import hmac
    import hashlib
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

# In your webhook handler:
@app.route('/webhook/paystack', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('x-paystack-signature')
    payload = request.get_data()
    
    if not signature:
        return 'Missing signature', 400
    
    if not verify_paystack_signature(payload, signature, os.getenv('PAYSTACK_SECRET_KEY')):
        return 'Invalid signature', 401
    
    # Process the webhook
    data = request.get_json()
    # ... handle event
'''
        return validation_code + '\n' + code

    def _fix_http_callback(self, code: str) -> str:
        """Replace HTTP with HTTPS in callbacks."""
        return code.replace('http://', 'https://')

    def _fix_https(self, code: str) -> str:
        """Add HTTPS enforcement."""
        https_code = '''
# HTTPS Enforcement
if not request.is_secure and os.getenv('ENVIRONMENT') == 'production':
    return redirect(request.url.replace('http://', 'https://'), code=301)

'''
        return https_code + code

    def _fix_input_validation(self, code: str) -> str:
        """Add input validation."""
        validation_code = '''
def validate_payment_input(amount, email):
    """Validate payment input data."""
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > 1000000:  # Maximum limit
            raise ValueError("Amount exceeds maximum limit")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid amount: {e}")
    
    if not email or '@' not in email:
        raise ValueError("Valid email is required")
    
    return amount, email

'''
        return validation_code + code

    def _fix_idempotency(self, code: str) -> str:
        """Add idempotency key."""
        return self._generate_idempotency_fix() + '\n' + code

    def _fix_sensitive_logging(self, code: str) -> str:
        """Remove sensitive data from logs."""
        # Mask sensitive fields in log statements
        code = re.sub(
            r'(log|print|debug)\((.*secret.*)\)',
            r'\1("[REDACTED]")',
            code,
            flags=re.IGNORECASE
        )
        code = re.sub(
            r'(log|print|debug)\((.*password.*)\)',
            r'\1("[REDACTED]")',
            code,
            flags=re.IGNORECASE
        )
        return code

    def _fix_amount_validation(self, code: str) -> str:
        """Add amount validation."""
        return self._generate_amount_validation_fix() + '\n' + code

    # ==================== Helper Methods ====================

    def _generate_report(self, code: str, filename: str) -> SecurityReport:
        """Generate the final security report."""
        score = self._calculate_score(self.findings)
        recommendations = self._generate_recommendations(self.findings)
        
        fixed_code = None
        if self.enable_auto_fix and self.findings:
            fixed_code = self._apply_all_fixes(code, self.findings)
        
        return SecurityReport(
            overall_score=score,
            findings=self.findings,
            recommendations=recommendations,
            fixed_code=fixed_code
        )

    def _calculate_score(self, findings: List[SecurityFinding]) -> int:
        """Calculate overall security score."""
        score = 100
        for finding in findings:
            if finding.severity == SeverityLevel.CRITICAL:
                score -= 25
            elif finding.severity == SeverityLevel.HIGH:
                score -= 15
            elif finding.severity == SeverityLevel.MEDIUM:
                score -= 5
            elif finding.severity == SeverityLevel.LOW:
                score -= 1
        return max(0, score)

    def _generate_recommendations(self, findings: List[SecurityFinding]) -> List[str]:
        """Generate general recommendations based on findings."""
        recommendations = []
        issue_types = {f.issue_type for f in findings}
        
        if IssueType.EXPOSED_API_KEY in issue_types:
            recommendations.append(
                "Immediately revoke any exposed API keys in your Paystack dashboard "
                "and rotate to new keys stored in environment variables."
            )
        
        if IssueType.MISSING_WEBHOOK_VALIDATION in issue_types:
            recommendations.append(
                "Implement webhook signature validation using HMAC-SHA512 to prevent "
                "fake webhook events from being processed."
            )
        
        if IssueType.SENSITIVE_DATA_LOGGING in issue_types:
            recommendations.append(
                "Review all logging statements and ensure no sensitive data "
                "(keys, passwords, card data) is being logged."
            )
        
        if IssueType.HTTP_CALLBACK in issue_types:
            recommendations.append(
                "Update all callback URLs to use HTTPS. Configure your web server "
                "to redirect HTTP traffic to HTTPS."
            )
        
        if IssueType.MISSING_IDEMPOTENCY in issue_types:
            recommendations.append(
                "Implement idempotency keys for all transfer and refund operations "
                "to prevent duplicate transactions."
            )
        
        if IssueType.NO_RATE_LIMITING in issue_types:
            recommendations.append(
                "Implement rate limiting on all payment-related endpoints to "
                "protect against brute force and DDoS attacks."
            )
        
        if not any('https' in r.lower() for r in recommendations):
            recommendations.append(
                "Ensure all communication with Paystack APIs uses HTTPS."
            )
        
        recommendations.append(
            "Regularly audit your code for security vulnerabilities and "
            "keep dependencies up to date."
        )
        
        return recommendations

    def _generate_key_fix(self, line: str, key: str) -> str:
        """Generate fixed code for exposed key."""
        return line.replace(f'"{key}"', "os.getenv('PAYSTACK_SECRET_KEY')").replace(f"'{key}'", "os.getenv('PAYSTACK_SECRET_KEY')")

    def _generate_webhook_fix(self) -> str:
        """Generate webhook validation code."""
        return '''
import hmac
import hashlib
import os
from flask import request, abort

def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    """Verify Paystack webhook signature using HMAC-SHA512."""
    secret = os.getenv('PAYSTACK_SECRET_KEY')
    if not secret:
        return False
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

@app.route('/webhook/paystack', methods=['POST'])
def handle_paystack_webhook():
    # Get the signature from headers
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        abort(400, 'Missing signature')
    
    # Get raw payload for signature verification
    payload = request.get_data()
    
    # Verify signature
    if not verify_paystack_signature(payload, signature):
        abort(401, 'Invalid signature')
    
    # Now safe to parse JSON
    data = request.get_json()
    
    # Process the event
    event = data.get('event')
    # ... handle different event types
    
    return 'OK', 200
'''

    def _generate_idempotency_fix(self) -> str:
        """Generate idempotency key implementation."""
        return '''
import uuid

def generate_idempotency_key() -> str:
    """Generate unique idempotency key for transactions."""
    return f"ihhashi-{uuid.uuid4().hex}"

# When making a transfer:
headers = {
    'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}',
    'Content-Type': 'application/json',
    'Idempotency-Key': generate_idempotency_key()
}

response = requests.post(
    'https://api.paystack.co/transfer',
    headers=headers,
    json={
        'source': 'balance',
        'reason': 'Delivery Payment',
        'amount': amount,
        'recipient': recipient_code
    },
    timeout=30
)
'''

    def _generate_amount_validation_fix(self) -> str:
        """Generate amount validation code."""
        return '''
def validate_amount(amount) -> int:
    """
    Validate payment amount.
    
    Args:
        amount: Amount to validate (in kobo/cents)
        
    Returns:
        Validated amount as integer
        
    Raises:
        ValueError: If amount is invalid
    """
    try:
        amount = int(float(amount))
    except (TypeError, ValueError):
        raise ValueError("Amount must be a valid number")
    
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    
    if amount < 100:  # Minimum 1 unit
        raise ValueError("Amount below minimum")
    
    if amount > 100000000:  # Maximum limit
        raise ValueError("Amount exceeds maximum allowed")
    
    return amount
'''

    def _apply_all_fixes(self, code: str, findings: List[SecurityFinding]) -> str:
        """Apply all auto-fixable fixes to the code."""
        fixed_code = code
        
        for finding in findings:
            if finding.auto_fixable and finding.fixed_code:
                # Simple replacement (in production, use AST-based replacement)
                if finding.snippet and finding.snippet in fixed_code:
                    fixed_code = fixed_code.replace(finding.snippet, finding.fixed_code, 1)
        
        return fixed_code

    def _get_python_files(self, path: str) -> List[str]:
        """Get all Python files in a directory."""
        files = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith('.py'):
                    files.append(os.path.join(root, filename))
        return files

    # ==================== Public Utility Methods ====================

    def full_audit(self, codebase_path: str) -> SecurityReport:
        """
        Perform a full security audit of the codebase.
        
        Args:
            codebase_path: Path to the codebase directory
            
        Returns:
            Comprehensive SecurityReport
        """
        self.findings = []
        files = self._get_python_files(codebase_path)
        
        # Scan for exposed keys
        key_findings = self.scan_for_exposed_keys(files)
        self.findings.extend(key_findings)
        
        # Audit each file
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                # Determine audit type based on filename/content
                filename = os.path.basename(filepath)
                if 'webhook' in filename.lower():
                    self.audit_webhook_handler(code, filename)
                elif 'transaction' in filename.lower() or 'payment' in filename.lower():
                    self.audit_transaction_flow(code, filename)
                else:
                    self.audit_api_integration(code, filename)
            except Exception:
                pass
        
        # Check PCI compliance
        pci_status, pci_details = self.check_pci_compliance(codebase_path)
        
        # Generate final report
        report = self._generate_report("", "")
        report.files_scanned = len(files)
        report.pci_compliance_status = pci_status
        report.pci_compliance_details = pci_details
        
        return report


# ==================== Demo / Test Code ====================

VULNERABLE_WEBHOOK_CODE = '''
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# CRITICAL: Exposed API key
PAYSTACK_SECRET_KEY = "sk_live_xxxxx"

@app.route('/webhook/paystack', methods=['POST'])
def handle_webhook():
    # HIGH: No signature validation - accepts any request
    data = request.get_json()
    
    # CRITICAL: Logging sensitive data
    print(f"Processing payment with key: {PAYSTACK_SECRET_KEY}")
    
    # HIGH: No input validation
    amount = data['amount']
    email = data['customer']['email']
    
    # Process the payment
    if data['event'] == 'charge.success':
        # Update order status
        update_order(data['data']['reference'], 'paid')
    
    return jsonify({'status': 'success'})

def update_order(reference, status):
    # MEDIUM: SQL injection risk
    query = f"UPDATE orders SET status = '{status}' WHERE reference = '{reference}'"
    db.execute(query)

def process_refund(amount, recipient):
    # HIGH: No idempotency key
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    response = requests.post('https://api.paystack.co/transfer', 
                           headers=headers,
                           json={'amount': amount, 'recipient': recipient})
    return response.json()

if __name__ == '__main__':
    app.run(debug=True)
'''

VULNERABLE_API_CODE = '''
import requests

# CRITICAL: Exposed test key (still a risk)
SECRET_KEY = "sk_test_1234567890abcdef1234567890abcdef12345678"

class PaystackAPI:
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.base_url = "http://api.paystack.co"  # HIGH: HTTP instead of HTTPS
    
    def charge_card(self, email, amount, card_number):
        # HIGH: No input validation
        headers = {'Authorization': f'Bearer {self.secret_key}'}
        data = {
            'email': email,
            'amount': amount * 100,  # No validation on amount
            'card': {
                'number': card_number,  # CRITICAL: Logging card data
            }
        }
        
        print(f"Charging card: {card_number}")  # CRITICAL: Logging sensitive data
        
        response = requests.post(  # MEDIUM: No timeout
            f'{self.base_url}/charge',
            headers=headers,
            json=data
        )
        
        return response.json()
    
    def create_transfer(self, amount, recipient, reason):
        # HIGH: No idempotency key - duplicate risk
        headers = {'Authorization': f'Bearer {self.secret_key}'}
        response = requests.post(
            f'{self.base_url}/transfer',
            headers=headers,
            json={
                'source': 'balance',
                'amount': amount,
                'recipient': recipient,
                'reason': reason
            }
        )
        return response.json()
'''

SECURE_WEBHOOK_EXAMPLE = '''
import os
import hmac
import hashlib
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    """Verify Paystack webhook signature using HMAC-SHA512."""
    secret = os.getenv('PAYSTACK_SECRET_KEY')
    if not secret:
        return False
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

def validate_payment_data(data: dict) -> tuple:
    """Validate payment data."""
    try:
        amount = int(data.get('amount', 0))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        email = data.get('customer', {}).get('email', '')
        if not email or '@' not in email:
            raise ValueError("Valid email required")
        
        return amount, email
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid data: {e}")

@app.route('/webhook/paystack', methods=['POST'])
def handle_webhook():
    # Verify signature first
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        abort(400, 'Missing signature')
    
    payload = request.get_data()
    if not verify_paystack_signature(payload, signature):
        abort(401, 'Invalid signature')
    
    # Safe to parse JSON
    data = request.get_json()
    
    try:
        amount, email = validate_payment_data(data)
    except ValueError as e:
        abort(400, str(e))
    
    # Log safely (no sensitive data)
    app.logger.info(f"Processing payment event: {data.get('event')}")
    
    if data.get('event') == 'charge.success':
        reference = data['data']['reference']
        # Use parameterized query
        update_order_status(reference, 'paid')
    
    return jsonify({'status': 'success'}), 200

def update_order_status(reference: str, status: str):
    """Update order status using parameterized query."""
    query = "UPDATE orders SET status = %s WHERE reference = %s"
    db.execute(query, (status, reference))
'''


def demo():
    """Run demonstration of the Paystack Security Agent."""
    print("=" * 80)
    print("PAYSTACK SECURITY AGENT - DEMO")
    print("=" * 80)
    
    # Initialize agent with auto-fix enabled
    agent = PaystackSecurityAgent(enable_auto_fix=True)
    
    # Demo 1: Webhook audit
    print("\n" + "=" * 80)
    print("DEMO 1: Webhook Handler Security Audit")
    print("=" * 80)
    print("\nVulnerable Code:")
    print("-" * 40)
    print(VULNERABLE_WEBHOOK_CODE[:500] + "...")
    
    report = agent.audit_webhook_handler(VULNERABLE_WEBHOOK_CODE, "webhook_handler.py")
    print(f"\nSecurity Score: {report.overall_score}/100")
    print(f"Critical: {report.critical_count}, High: {report.high_count}, Medium: {report.medium_count}")
    
    print("\nFindings:")
    for i, finding in enumerate(report.findings[:5], 1):
        emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
            finding.severity.value, "⚪"
        )
        print(f"{i}. {emoji} [{finding.severity.value}] {finding.title}")
        print(f"   Line {finding.line_number}: {finding.description[:80]}...")
        if finding.auto_fixable:
            print(f"   ✅ Auto-fix available")
    
    # Demo 2: API integration audit
    print("\n" + "=" * 80)
    print("DEMO 2: API Integration Security Audit")
    print("=" * 80)
    
    report2 = agent.audit_api_integration(VULNERABLE_API_CODE, "paystack_api.py")
    print(f"\nSecurity Score: {report2.overall_score}/100")
    print(f"Critical: {report2.critical_count}, High: {report2.high_count}")
    
    # Demo 3: Webhook signature validation
    print("\n" + "=" * 80)
    print("DEMO 3: Webhook Signature Validation")
    print("=" * 80)
    
    payload = '{"event": "charge.success", "data": {"reference": "123"}}'
    secret = "sk_test_1234567890abcdef1234567890abcdef12345678"
    
    # Generate valid signature
    valid_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    is_valid = agent.validate_webhook_signature(payload, valid_signature, secret)
    print(f"\nValid signature test: {'✅ PASS' if is_valid else '❌ FAIL'}")
    
    is_invalid = agent.validate_webhook_signature(payload, "invalid_signature", secret)
    print(f"Invalid signature test: {'❌ FAIL (correctly rejected)' if not is_invalid else '✅ PASS'}")
    
    # Demo 4: Secure code example
    print("\n" + "=" * 80)
    print("DEMO 4: Secure Webhook Example")
    print("=" * 80)
    
    report_secure = agent.audit_webhook_handler(SECURE_WEBHOOK_EXAMPLE, "secure_webhook.py")
    print(f"\nSecurity Score: {report_secure.overall_score}/100")
    print(f"Findings: {len(report_secure.findings)}")
    if report_secure.findings:
        for finding in report_secure.findings:
            print(f"  - [{finding.severity.value}] {finding.title}")
    else:
        print("  ✅ No security issues found!")
    
    # Demo 5: Generate report
    print("\n" + "=" * 80)
    print("DEMO 5: Markdown Report Generation")
    print("=" * 80)
    
    print("\n" + report.to_markdown()[:2000] + "\n... [truncated]")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    
    return agent, report


if __name__ == "__main__":
    agent, report = demo()
