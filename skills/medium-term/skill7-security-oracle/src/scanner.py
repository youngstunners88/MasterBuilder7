"""Security scanner for proactive vulnerability detection."""

import os
import re
import json
import subprocess
import hashlib
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from datetime import datetime

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnCategory(Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    AUTH_BYPASS = "auth_bypass"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"
    INSECURE_CONFIG = "insecure_config"
    DEPENDENCY_VULN = "dependency_vuln"
    SECRET_LEAK = "secret_leak"
    RACE_CONDITION = "race_condition"
    SSRF = "ssrf"
    XXE = "xxe"
    LDAP_INJECTION = "ldap_injection"
    XML_INJECTION = "xml_injection"
    LOG_INJECTION = "log_injection"
    TEMPLATE_INJECTION = "template_injection"
    CSRF = "csrf"
    CORS_MISCONFIG = "cors_misconfig"


@dataclass
class Vulnerability:
    """Represents a security vulnerability."""
    id: str
    title: str
    description: str
    severity: Severity
    category: VulnCategory
    file_path: str
    line_number: int
    column: int
    code_snippet: str
    remediation: str
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    references: List[str] = field(default_factory=list)
    scanner: str = ""
    confidence: str = "medium"  # low, medium, high
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'category': self.category.value,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'column': self.column,
            'code_snippet': self.code_snippet,
            'remediation': self.remediation,
            'cwe_id': self.cwe_id,
            'cvss_score': self.cvss_score,
            'references': self.references,
            'scanner': self.scanner,
            'confidence': self.confidence,
            'discovered_at': self.discovered_at
        }


@dataclass
class ScanResult:
    """Result of a security scan."""
    vulnerabilities: List[Vulnerability]
    scan_time: datetime
    target_path: str
    scanners_used: List[str]
    files_scanned: int
    duration_seconds: float
    
    def get_by_severity(self, severity: Severity) -> List[Vulnerability]:
        return [v for v in self.vulnerabilities if v.severity == severity]
    
    def get_by_category(self, category: VulnCategory) -> List[Vulnerability]:
        return [v for v in self.vulnerabilities if v.category == category]
    
    @property
    def critical_count(self) -> int:
        return len(self.get_by_severity(Severity.CRITICAL))
    
    @property
    def high_count(self) -> int:
        return len(self.get_by_severity(Severity.HIGH))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vulnerabilities': [v.to_dict() for v in self.vulnerabilities],
            'scan_time': self.scan_time.isoformat(),
            'target_path': self.target_path,
            'scanners_used': self.scanners_used,
            'files_scanned': self.files_scanned,
            'duration_seconds': self.duration_seconds,
            'summary': {
                'total': len(self.vulnerabilities),
                'critical': self.critical_count,
                'high': self.high_count,
                'medium': len(self.get_by_severity(Severity.MEDIUM)),
                'low': len(self.get_by_severity(Severity.LOW)),
                'info': len(self.get_by_severity(Severity.INFO))
            }
        }


class SecurityScanner:
    """Main security scanner orchestrating multiple scanning methods."""
    
    SECRET_PATTERNS = {
        'aws_access_key': r'AKIA[0-9A-Z]{16}',
        'aws_secret_key': r'[0-9a-zA-Z/+]{40}',
        'github_token': r'gh[pousr]_[A-Za-z0-9_]{36,}',
        'slack_token': r'xox[baprs]-[0-9a-zA-Z]{10,48}',
        'private_key': r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
        'api_key': r'[aA][pP][iI][_-]?[kK][eE][yY][\s]*[=:]+[\s]*["\']?[a-zA-Z0-9]{16,}["\']?',
        'password': r'[pP][aA][sS][sS][wW][oO][rR][dD][\s]*[=:]+[\s]*["\'][^"\']+["\']',
        'secret': r'[sS][eE][cC][rR][eE][tT][\s]*[=:]+[\s]*["\'][^"\']+["\']',
        'jwt_token': r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
        'database_url': r'(postgres|mysql|mongodb|redis)://[^\s"\']+',
    }
    
    SQL_INJECTION_PATTERNS = [
        r'execute\s*\(\s*["\'].*%s',
        r'cursor\.execute\s*\(\s*["\'].*\+',
        r'\.format\s*\(\s*.*\)',
        r'f["\'].*\{.*\}.*["\']',
        r'\.query\s*\(\s*["\'].*\$',
    ]
    
    XSS_PATTERNS = [
        r'innerHTML\s*=',
        r'document\.write\s*\(',
        r'eval\s*\(',
        r'\.html\s*\(',
    ]
    
    def __init__(self, rules_dir: Optional[str] = None):
        self.rules_dir = Path(rules_dir) if rules_dir else Path(__file__).parent / 'rules'
        self.vulnerabilities: List[Vulnerability] = []
        self.custom_rules: List[Dict] = []
        self.load_custom_rules()
    
    def load_custom_rules(self):
        """Load custom Semgrep-style rules."""
        if not self.rules_dir.exists():
            return
        
        for rule_file in self.rules_dir.glob('*.yaml'):
            try:
                with open(rule_file) as f:
                    self.custom_rules.append(yaml.safe_load(f))
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not load rule {rule_file}: {e}")
    
    def scan(self, target_path: str, 
             scanners: Optional[List[str]] = None) -> ScanResult:
        """Run comprehensive security scan."""
        import time
        start_time = time.time()
        
        target_path = Path(target_path)
        scanners = scanners or ['all']
        
        self.vulnerabilities = []
        files_scanned = 0
        scanners_used = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Run Semgrep if available
            if 'all' in scanners or 'semgrep' in scanners:
                task = progress.add_task("[cyan]Running Semgrep...", total=None)
                try:
                    self._run_semgrep(target_path)
                    scanners_used.append('semgrep')
                except Exception as e:
                    console.print(f"[yellow]Semgrep scan failed:[/yellow] {e}")
                progress.remove_task(task)
            
            # Run Bandit for Python
            if 'all' in scanners or 'bandit' in scanners:
                task = progress.add_task("[cyan]Running Bandit...", total=None)
                try:
                    self._run_bandit(target_path)
                    scanners_used.append('bandit')
                except Exception as e:
                    console.print(f"[yellow]Bandit scan failed:[/yellow] {e}")
                progress.remove_task(task)
            
            # Run secret detection
            if 'all' in scanners or 'secrets' in scanners:
                task = progress.add_task("[cyan]Scanning for secrets...", total=None)
                files_scanned += self._scan_for_secrets(target_path)
                scanners_used.append('secrets')
                progress.remove_task(task)
            
            # Run custom rules
            if 'all' in scanners or 'custom' in scanners:
                task = progress.add_task("[cyan]Running custom rules...", total=None)
                files_scanned += self._run_custom_rules(target_path)
                scanners_used.append('custom')
                progress.remove_task(task)
            
            # Run dependency scan
            if 'all' in scanners or 'dependencies' in scanners:
                task = progress.add_task("[cyan]Scanning dependencies...", total=None)
                self._scan_dependencies(target_path)
                scanners_used.append('dependencies')
                progress.remove_task(task)
        
        duration = time.time() - start_time
        
        return ScanResult(
            vulnerabilities=self.vulnerabilities,
            scan_time=datetime.now(),
            target_path=str(target_path),
            scanners_used=scanners_used,
            files_scanned=files_scanned,
            duration_seconds=duration
        )
    
    def _run_semgrep(self, target_path: Path):
        """Run Semgrep security scanner."""
        try:
            cmd = [
                'semgrep',
                '--config=auto',
                '--json',
                '--quiet',
                str(target_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode in (0, 1):  # 1 means findings found
                data = json.loads(result.stdout)
                
                for finding in data.get('results', []):
                    vuln = Vulnerability(
                        id=finding.get('check_id', 'unknown'),
                        title=finding.get('extra', {}).get('message', 'Unknown issue'),
                        description=finding.get('extra', {}).get('message', ''),
                        severity=self._map_semgrep_severity(
                            finding.get('extra', {}).get('metadata', {}).get('severity', 'WARNING')
                        ),
                        category=self._map_semgrep_category(finding.get('check_id', '')),
                        file_path=finding.get('path', ''),
                        line_number=finding.get('start', {}).get('line', 0),
                        column=finding.get('start', {}).get('col', 0),
                        code_snippet=finding.get('extra', {}).get('lines', ''),
                        remediation="Review and fix the identified issue",
                        cwe_id=self._extract_cwe(finding.get('extra', {}).get('metadata', {}).get('cwe', [])),
                        scanner='semgrep',
                        confidence=finding.get('extra', {}).get('metadata', {}).get('confidence', 'medium')
                    )
                    self.vulnerabilities.append(vuln)
                    
        except FileNotFoundError:
            console.print("[yellow]Warning:[/yellow] Semgrep not found. Install with: pip install semgrep")
        except subprocess.TimeoutExpired:
            console.print("[yellow]Warning:[/yellow] Semgrep scan timed out")
    
    def _run_bandit(self, target_path: Path):
        """Run Bandit Python security scanner."""
        try:
            cmd = [
                'bandit',
                '-r',
                '-f', 'json',
                str(target_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.stdout:
                data = json.loads(result.stdout)
                
                for result_item in data.get('results', []):
                    vuln = Vulnerability(
                        id=f"bandit-{result_item.get('test_id', 'B000')}",
                        title=result_item.get('issue_text', 'Unknown issue'),
                        description=result_item.get('issue_text', ''),
                        severity=self._map_bandit_severity(result_item.get('issue_severity', 'MEDIUM')),
                        category=self._map_bandit_category(result_item.get('test_name', '')),
                        file_path=result_item.get('filename', ''),
                        line_number=result_item.get('line_number', 0),
                        column=result_item.get('col_offset', 0),
                        code_snippet=result_item.get('code', ''),
                        remediation=result_item.get('more_info', ''),
                        cwe_id=result_item.get('cwe', {}).get('id'),
                        scanner='bandit',
                        confidence=result_item.get('issue_confidence', 'medium').lower()
                    )
                    self.vulnerabilities.append(vuln)
                    
        except FileNotFoundError:
            console.print("[yellow]Warning:[/yellow] Bandit not found. Install with: pip install bandit")
    
    def _scan_for_secrets(self, target_path: Path) -> int:
        """Scan for hardcoded secrets and credentials."""
        files_scanned = 0
        
        for file_path in target_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Skip binary files and common non-code files
            if self._is_binary(file_path):
                continue
            
            # Skip common directories
            if any(part in str(file_path) for part in ['.git', 'node_modules', '__pycache__', '.venv']):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                files_scanned += 1
            except Exception:
                continue
            
            # Check each secret pattern
            for secret_type, pattern in self.SECRET_PATTERNS.items():
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    col = match.start() - content.rfind('\n', 0, match.start())
                    
                    # Calculate context
                    lines = content.split('\n')
                    context_start = max(0, line_num - 2)
                    context_end = min(len(lines), line_num + 1)
                    code_snippet = '\n'.join(lines[context_start:context_end])
                    
                    vuln = Vulnerability(
                        id=f"secret-{secret_type}",
                        title=f"Hardcoded {secret_type.replace('_', ' ').title()}",
                        description=f"Potential hardcoded {secret_type} detected in code",
                        severity=Severity.CRITICAL if secret_type in ['private_key', 'aws_secret_key'] else Severity.HIGH,
                        category=VulnCategory.HARDCODED_SECRET,
                        file_path=str(file_path),
                        line_number=line_num,
                        column=col,
                        code_snippet=code_snippet,
                        remediation=f"Move {secret_type} to environment variables or secure vault",
                        cwe_id="CWE-798",
                        cvss_score=7.5,
                        references=[
                            "https://cwe.mitre.org/data/definitions/798.html",
                            "https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication"
                        ],
                        scanner='secrets',
                        confidence='high'
                    )
                    self.vulnerabilities.append(vuln)
        
        return files_scanned
    
    def _run_custom_rules(self, target_path: Path) -> int:
        """Run custom security rules."""
        files_scanned = 0
        
        for file_path in target_path.rglob('*.py'):
            if not file_path.is_file():
                continue
            
            if any(part in str(file_path) for part in ['.git', 'node_modules', '__pycache__']):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                files_scanned += 1
            except Exception:
                continue
            
            # Check SQL injection patterns
            for i, line in enumerate(content.split('\n'), 1):
                for pattern in self.SQL_INJECTION_PATTERNS:
                    if re.search(pattern, line):
                        vuln = Vulnerability(
                            id="sql-injection",
                            title="Potential SQL Injection",
                            description="User input may be directly concatenated into SQL queries",
                            severity=Severity.CRITICAL,
                            category=VulnCategory.SQL_INJECTION,
                            file_path=str(file_path),
                            line_number=i,
                            column=line.find('execute') if 'execute' in line else 0,
                            code_snippet=line.strip(),
                            remediation="Use parameterized queries or an ORM",
                            cwe_id="CWE-89",
                            cvss_score=9.1,
                            references=[
                                "https://owasp.org/www-community/attacks/SQL_Injection",
                                "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
                            ],
                            scanner='custom',
                            confidence='medium'
                        )
                        self.vulnerabilities.append(vuln)
                        break
        
        return files_scanned
    
    def _scan_dependencies(self, target_path: Path):
        """Scan dependencies for known vulnerabilities."""
        # Check for requirements.txt
        req_file = target_path / 'requirements.txt'
        if req_file.exists():
            try:
                self._scan_requirements(req_file)
            except Exception as e:
                console.print(f"[yellow]Dependency scan warning:[/yellow] {e}")
        
        # Check for package.json
        package_file = target_path / 'package.json'
        if package_file.exists():
            try:
                self._scan_npm_package(package_file)
            except Exception as e:
                console.print(f"[yellow]NPM scan warning:[/yellow] {e}")
    
    def _scan_requirements(self, req_file: Path):
        """Scan Python requirements for vulnerabilities."""
        try:
            cmd = ['pip-audit', '-r', str(req_file), '--format=json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                data = json.loads(result.stdout)
                for vuln in data.get('vulnerabilities', []):
                    for spec in vuln.get('specs', []):
                        v = Vulnerability(
                            id=f"pip-audit-{vuln.get('id', 'unknown')}",
                            title=f"Vulnerable dependency: {vuln.get('name', 'unknown')}",
                            description=vuln.get('description', ''),
                            severity=self._cvss_to_severity(vuln.get('fix_versions', [])),
                            category=VulnCategory.DEPENDENCY_VULN,
                            file_path=str(req_file),
                            line_number=0,
                            column=0,
                            code_snippet=f"{vuln.get('name')} {spec}",
                            remediation=f"Update to: {', '.join(vuln.get('fix_versions', []))}",
                            cwe_id=None,
                            scanner='pip-audit',
                            confidence='high'
                        )
                        self.vulnerabilities.append(v)
                        
        except FileNotFoundError:
            console.print("[yellow]Warning:[/yellow] pip-audit not found. Install with: pip install pip-audit")
    
    def _scan_npm_package(self, package_file: Path):
        """Scan NPM package.json for vulnerabilities."""
        try:
            cmd = ['npm', 'audit', '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=package_file.parent, timeout=120)
            
            if result.stdout:
                data = json.loads(result.stdout)
                for vuln_id, vuln_data in data.get('advisories', {}).items():
                    v = Vulnerability(
                        id=f"npm-{vuln_id}",
                        title=vuln_data.get('title', 'NPM vulnerability'),
                        description=vuln_data.get('overview', ''),
                        severity=self._map_npm_severity(vuln_data.get('severity', 'moderate')),
                        category=VulnCategory.DEPENDENCY_VULN,
                        file_path=str(package_file),
                        line_number=0,
                        column=0,
                        code_snippet=vuln_data.get('module_name', ''),
                        remediation=vuln_data.get('recommendation', 'Update dependency'),
                        cwe_id=None,
                        scanner='npm-audit',
                        confidence='high'
                    )
                    self.vulnerabilities.append(v)
                    
        except Exception as e:
            console.print(f"[yellow]NPM audit warning:[/yellow] {e}")
    
    def _is_binary(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except Exception:
            return True
    
    def _map_semgrep_severity(self, severity: str) -> Severity:
        """Map Semgrep severity to internal severity."""
        mapping = {
            'ERROR': Severity.HIGH,
            'WARNING': Severity.MEDIUM,
            'INFO': Severity.LOW
        }
        return mapping.get(severity.upper(), Severity.MEDIUM)
    
    def _map_bandit_severity(self, severity: str) -> Severity:
        """Map Bandit severity to internal severity."""
        mapping = {
            'CRITICAL': Severity.CRITICAL,
            'HIGH': Severity.HIGH,
            'MEDIUM': Severity.MEDIUM,
            'LOW': Severity.LOW
        }
        return mapping.get(severity.upper(), Severity.MEDIUM)
    
    def _map_bandit_category(self, test_name: str) -> VulnCategory:
        """Map Bandit test name to category."""
        mapping = {
            'B301': VulnCategory.COMMAND_INJECTION,
            'B608': VulnCategory.SQL_INJECTION,
            'B102': VulnCategory.COMMAND_INJECTION,
            'B105': VulnCategory.HARDCODED_SECRET,
            'B601': VulnCategory.COMMAND_INJECTION,
            'B609': VulnCategory.WEAK_CRYPTO,
        }
        # Extract test ID if present
        match = re.match(r'B\d+', test_name)
        if match:
            return mapping.get(match.group(), VulnCategory.INSECURE_CONFIG)
        return VulnCategory.INSECURE_CONFIG
    
    def _map_semgrep_category(self, check_id: str) -> VulnCategory:
        """Map Semgrep check ID to category."""
        check_lower = check_id.lower()
        if 'sql' in check_lower:
            return VulnCategory.SQL_INJECTION
        elif 'xss' in check_lower:
            return VulnCategory.XSS
        elif 'command' in check_lower or 'exec' in check_lower:
            return VulnCategory.COMMAND_INJECTION
        elif 'secret' in check_lower or 'password' in check_lower:
            return VulnCategory.HARDCODED_SECRET
        elif 'path' in check_lower:
            return VulnCategory.PATH_TRAVERSAL
        elif 'auth' in check_lower:
            return VulnCategory.AUTH_BYPASS
        elif 'crypto' in check_lower:
            return VulnCategory.WEAK_CRYPTO
        return VulnCategory.INSECURE_CONFIG
    
    def _extract_cwe(self, cwe_list: List[str]) -> Optional[str]:
        """Extract CWE ID from list."""
        if not cwe_list:
            return None
        # Take first CWE
        cwe = cwe_list[0]
        match = re.search(r'CWE-(\d+)', str(cwe))
        if match:
            return f"CWE-{match.group(1)}"
        return None
    
    def _cvss_to_severity(self, fix_versions: List[str]) -> Severity:
        """Estimate severity from fix versions."""
        # This is a simplified heuristic
        if not fix_versions:
            return Severity.MEDIUM
        return Severity.HIGH
    
    def _map_npm_severity(self, severity: str) -> Severity:
        """Map NPM severity to internal severity."""
        mapping = {
            'critical': Severity.CRITICAL,
            'high': Severity.HIGH,
            'moderate': Severity.MEDIUM,
            'low': Severity.LOW
        }
        return mapping.get(severity.lower(), Severity.MEDIUM)