"""Tests for the security scanner."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, '../src')

from scanner import SecurityScanner, VulnCategory, Severity


class TestSecurityScanner:
    """Test cases for SecurityScanner."""
    
    def test_initialization(self):
        """Test scanner initialization."""
        scanner = SecurityScanner()
        assert scanner.vulnerabilities == []
    
    def test_secret_detection(self):
        """Test detection of hardcoded secrets."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# This file has secrets for testing
API_KEY = "sk-1234567890abcdef1234567890"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
PASSWORD = "super_secret_password_123"
""")
            tmpfile = f.name
        
        try:
            scanner = SecurityScanner()
            scanner._scan_for_secrets(Path(tmpfile))
            
            # Should find at least one secret
            assert len(scanner.vulnerabilities) > 0
            
            # Check categories
            categories = [v.category for v in scanner.vulnerabilities]
            assert VulnCategory.HARDCODED_SECRET in categories
            
        finally:
            Path(tmpfile).unlink()
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def get_user(user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    
def get_data(value):
    query = "SELECT * FROM data WHERE val = " + value
    cursor.execute(query)
""")
            tmpfile = f.name
        
        try:
            scanner = SecurityScanner()
            scanner._run_custom_rules(Path(tmpfile))
            
            # Check for SQL injection issues
            sql_issues = [v for v in scanner.vulnerabilities 
                         if v.category == VulnCategory.SQL_INJECTION]
            assert len(sql_issues) > 0
            
        finally:
            Path(tmpfile).unlink()
    
    def test_vulnerability_severity(self):
        """Test vulnerability severity levels."""
        vuln = scanner.vulnerabilities[0] if scanner.vulnerabilities else None
        if vuln:
            assert vuln.severity in [
                Severity.CRITICAL, Severity.HIGH, 
                Severity.MEDIUM, Severity.LOW, Severity.INFO
            ]
    
    def test_scan_result_structure(self):
        """Test scan result data structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("API_KEY = 'test123'")
            
            scanner = SecurityScanner()
            result = scanner.scan(tmpdir, scanners=['secrets'])
            
            assert result.target_path == tmpdir
            assert isinstance(result.vulnerabilities, list)
            assert isinstance(result.scanners_used, list)
            assert result.files_scanned >= 0
            assert result.duration_seconds >= 0
    
    def test_get_by_severity(self):
        """Test filtering vulnerabilities by severity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("""
API_KEY = "sk-1234567890abcdef"
""")
            
            scanner = SecurityScanner()
            result = scanner.scan(tmpdir, scanners=['secrets'])
            
            critical = result.get_by_severity(Severity.CRITICAL)
            high = result.get_by_severity(Severity.HIGH)
            
            assert isinstance(critical, list)
            assert isinstance(high, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])