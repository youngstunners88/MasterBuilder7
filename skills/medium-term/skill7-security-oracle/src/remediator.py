"""Security remediation assistant."""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from rich.console import Console

from .scanner import Vulnerability, VulnCategory, Severity

console = Console()


@dataclass
class RemediationSuggestion:
    """A suggestion for fixing a vulnerability."""
    vuln_id: str
    title: str
    description: str
    original_code: str
    fixed_code: str
    explanation: str
    confidence: str  # low, medium, high
    requires_review: bool


class Remediator:
    """Provides automated remediation suggestions for vulnerabilities."""
    
    # Remediation templates for common issues
    SQL_INJECTION_FIX = """# BAD (Vulnerable)
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD (Secure)
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
# OR with SQLAlchemy:
User.query.filter_by(id=user_id).first()
"""
    
    HARDCODED_SECRET_FIX = """# BAD (Vulnerable)
API_KEY = "sk-1234567890abcdef"

# GOOD (Secure)
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
# Add to .env file (and .gitignore!)
# API_KEY=sk-1234567890abcdef
"""
    
    COMMAND_INJECTION_FIX = """# BAD (Vulnerable)
os.system(f"ls {user_input}")
subprocess.call(f"echo {user_input}", shell=True)

# GOOD (Secure)
import shlex
import subprocess

# Use list instead of string, avoid shell=True
subprocess.run(["ls", user_input])
# Or validate input
safe_input = shlex.quote(user_input)
subprocess.run(f"echo {safe_input}", shell=True)
"""
    
    WEAK_CRYPTO_FIX = """# BAD (Vulnerable)
import hashlib
hash = hashlib.md5(password.encode()).hexdigest()

# GOOD (Secure)
import hashlib
import secrets

# Use strong hashing with salt
salt = secrets.token_hex(16)
hash = hashlib.sha256((password + salt).encode()).hexdigest()

# Even better: Use bcrypt
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
"""
    
    XSS_FIX = """# BAD (Vulnerable - JavaScript)
element.innerHTML = userInput;

# GOOD (Secure)
// Use textContent instead
element.textContent = userInput;

// Or sanitize HTML
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
"""
    
    PATH_TRAVERSAL_FIX = """# BAD (Vulnerable)
with open(f"/uploads/{filename}", "r") as f:
    content = f.read()

# GOOD (Secure)
import os
from pathlib import Path

uploads_dir = Path("/uploads").resolve()
file_path = (uploads_dir / filename).resolve()

# Ensure file is within uploads directory
if not str(file_path).startswith(str(uploads_dir)):
    raise ValueError("Invalid filename")

with open(file_path, "r") as f:
    content = f.read()
"""
    
    def __init__(self):
        self.suggestions: Dict[str, List[RemediationSuggestion]] = {}
    
    def generate_suggestions(self, vulnerabilities: List[Vulnerability]) -> List[RemediationSuggestion]:
        """Generate remediation suggestions for vulnerabilities."""
        suggestions = []
        
        for vuln in vulnerabilities:
            suggestion = self._generate_for_vulnerability(vuln)
            if suggestion:
                suggestions.append(suggestion)
        
        self.suggestions = {s.vuln_id: [s] for s in suggestions}
        return suggestions
    
    def _generate_for_vulnerability(self, vuln: Vulnerability) -> Optional[RemediationSuggestion]:
        """Generate a suggestion for a specific vulnerability."""
        generators = {
            VulnCategory.SQL_INJECTION: self._fix_sql_injection,
            VulnCategory.XSS: self._fix_xss,
            VulnCategory.COMMAND_INJECTION: self._fix_command_injection,
            VulnCategory.PATH_TRAVERSAL: self._fix_path_traversal,
            VulnCategory.HARDCODED_SECRET: self._fix_hardcoded_secret,
            VulnCategory.WEAK_CRYPTO: self._fix_weak_crypto,
            VulnCategory.INSECURE_DESERIALIZATION: self._fix_insecure_deserialization,
            VulnCategory.AUTH_BYPASS: self._fix_auth_bypass,
            VulnCategory.CSRF: self._fix_csrf,
            VulnCategory.CORS_MISCONFIG: self._fix_cors,
        }
        
        generator = generators.get(vuln.category)
        if generator:
            return generator(vuln)
        
        return self._generic_fix(vuln)
    
    def _fix_sql_injection(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate SQL injection fix."""
        code = vuln.code_snippet
        
        # Try to detect the pattern and generate fix
        if 'f"' in code or '.format(' in code or '%' in code:
            # Extract the query parts
            fixed = self._transform_sql_query(code)
        else:
            fixed = "# Use parameterized queries\ncursor.execute(\"SELECT * FROM table WHERE id = %s\", (user_id,))"
        
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix SQL Injection with Parameterized Queries",
            description="Replace string concatenation/formatting with parameterized queries",
            original_code=code,
            fixed_code=fixed,
            explanation="""
SQL injection occurs when user input is directly concatenated into SQL queries.
Parameterized queries ensure user input is treated as data, not executable code.

Benefits:
- Prevents SQL injection attacks
- Often improves query performance
- Makes code cleaner and easier to read
""",
            confidence="high",
            requires_review=True
        )
    
    def _transform_sql_query(self, code: str) -> str:
        """Transform a SQL query to use parameters."""
        # Simple transformation for common patterns
        # This is a basic implementation - real world would need AST parsing
        
        # Pattern: f"SELECT ... {var}"
        if 'f"' in code or "f'" in code:
            # Extract variables
            import re
            vars_found = re.findall(r'\{([^}]+)\}', code)
            
            if vars_found:
                # Replace with placeholders
                fixed_query = re.sub(r'\{[^}]+\}', '%s', code)
                fixed_query = fixed_query.replace('f"', '"').replace("f'", "'")
                
                params = ', '.join(vars_found)
                return f"# Secure version\ncursor.execute({fixed_query}, ({params},))"
        
        return self.SQL_INJECTION_FIX
    
    def _fix_xss(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate XSS fix."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix XSS with Output Encoding",
            description="Sanitize or encode user input before rendering in HTML",
            original_code=vuln.code_snippet,
            fixed_code=self.XSS_FIX,
            explanation="""
XSS attacks occur when user input is rendered in HTML without proper escaping.
Always encode output or use safe APIs like textContent instead of innerHTML.
""",
            confidence="high",
            requires_review=True
        )
    
    def _fix_command_injection(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate command injection fix."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix Command Injection",
            description="Avoid shell=True and properly validate/escape user input",
            original_code=vuln.code_snippet,
            fixed_code=self.COMMAND_INJECTION_FIX,
            explanation="""
Command injection allows attackers to execute arbitrary system commands.
Use lists instead of strings for subprocess calls and avoid shell=True when possible.
""",
            confidence="high",
            requires_review=True
        )
    
    def _fix_path_traversal(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate path traversal fix."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix Path Traversal",
            description="Validate that file paths stay within intended directories",
            original_code=vuln.code_snippet,
            fixed_code=self.PATH_TRAVERSAL_FIX,
            explanation="""
Path traversal allows attackers to access files outside intended directories.
Always resolve paths and verify they're within the allowed directory.
""",
            confidence="high",
            requires_review=False
        )
    
    def _fix_hardcoded_secret(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate hardcoded secret fix."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Move Secret to Environment Variable",
            description="Replace hardcoded secrets with environment variables",
            original_code=vuln.code_snippet,
            fixed_code=self.HARDCODED_SECRET_FIX,
            explanation="""
Hardcoded secrets can be exposed through version control or decompilation.
Always store secrets in environment variables or secure vaults like AWS Secrets Manager.

Steps:
1. Move secret to .env file
2. Add .env to .gitignore
3. Load secret using python-dotenv or os.getenv()
4. Rotate the exposed secret immediately
""",
            confidence="high",
            requires_review=False
        )
    
    def _fix_weak_crypto(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate weak cryptography fix."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Use Strong Cryptography",
            description="Replace weak hashing algorithms with strong alternatives",
            original_code=vuln.code_snippet,
            fixed_code=self.WEAK_CRYPTO_FIX,
            explanation="""
Weak cryptographic algorithms can be easily broken by attackers.
Use bcrypt, Argon2, or PBKDF2 for password hashing.
Never use MD5 or SHA1 for password storage.
""",
            confidence="high",
            requires_review=True
        )
    
    def _fix_insecure_deserialization(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate insecure deserialization fix."""
        fix_code = """# BAD (Vulnerable)
import pickle
data = pickle.loads(user_input)

# GOOD (Secure)
import json
data = json.loads(user_input)

# If you must use pickle, sign the data:
import pickle
import hmac
import hashlib

def safe_loads(data, secret):
    sig, payload = data[:32], data[32:]
    expected = hmac.new(secret, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid signature")
    return pickle.loads(payload)
"""
        
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix Insecure Deserialization",
            description="Use safe serialization formats or implement integrity checks",
            original_code=vuln.code_snippet,
            fixed_code=fix_code,
            explanation="""
Insecure deserialization can lead to remote code execution.
Avoid pickle, yaml.load(), and eval() on untrusted data.
Use JSON or implement cryptographic signatures for integrity.
""",
            confidence="medium",
            requires_review=True
        )
    
    def _fix_auth_bypass(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate authentication bypass fix."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix Authentication Issue",
            description="Implement proper authentication and authorization checks",
            original_code=vuln.code_snippet,
            fixed_code="# Review authentication logic\n# Ensure all protected routes check authentication\n# Use established libraries like Flask-Login, Django Auth, etc.",
            explanation="""
Authentication bypass vulnerabilities allow unauthorized access.
Always use established authentication libraries and follow security best practices.
Ensure all protected endpoints verify authentication before processing.
""",
            confidence="low",
            requires_review=True
        )
    
    def _fix_csrf(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate CSRF fix."""
        fix_code = """# Flask-WTF Example
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# In templates:
# <form method="post">
#     {{ form.hidden_tag() }}
#     ...
# </form>

# Django (enabled by default)
# Ensure MIDDLEWARE includes:
# 'django.middleware.csrf.CsrfViewMiddleware'
"""
        
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Add CSRF Protection",
            description="Implement CSRF tokens for state-changing operations",
            original_code=vuln.code_snippet,
            fixed_code=fix_code,
            explanation="""
CSRF attacks force users to perform unintended actions.
Always use CSRF tokens for POST, PUT, DELETE requests.
Most web frameworks provide built-in CSRF protection.
""",
            confidence="high",
            requires_review=True
        )
    
    def _fix_cors(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate CORS misconfiguration fix."""
        fix_code = """# Flask-CORS Example
from flask_cors import CORS

# Restrict to specific origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://trusted-domain.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# NEVER use:
# CORS(app, origins="*")  # Too permissive
"""
        
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title="Fix CORS Configuration",
            description="Restrict CORS to specific trusted origins",
            original_code=vuln.code_snippet,
            fixed_code=fix_code,
            explanation="""
Overly permissive CORS allows malicious websites to access your API.
Always whitelist specific origins rather than using *.
""",
            confidence="high",
            requires_review=True
        )
    
    def _generic_fix(self, vuln: Vulnerability) -> RemediationSuggestion:
        """Generate generic fix for unknown vulnerability types."""
        return RemediationSuggestion(
            vuln_id=vuln.id,
            title=f"Fix {vuln.category.value.replace('_', ' ').title()}",
            description=vuln.description,
            original_code=vuln.code_snippet,
            fixed_code="# TODO: Review and fix this vulnerability\n# See OWASP guidelines for remediation",
            explanation=f"""
This is a {vuln.severity.value} severity {vuln.category.value.replace('_', ' ')} issue.
Review the code carefully and apply appropriate fixes based on OWASP guidelines.

References:
{chr(10).join(f"- {ref}" for ref in vuln.references) if vuln.references else "- https://owasp.org/www-project-top-ten/"}
""",
            confidence="low",
            requires_review=True
        )
    
    def apply_fix(self, file_path: str, vuln: Vulnerability, 
                  suggestion: RemediationSuggestion) -> bool:
        """Attempt to automatically apply a fix."""
        if suggestion.requires_review:
            console.print(f"[yellow]Fix for {vuln.id} requires manual review[/yellow]")
            return False
        
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            content = path.read_text()
            lines = content.split('\n')
            
            # Find the vulnerable line
            vuln_line_idx = vuln.line_number - 1
            if vuln_line_idx >= len(lines):
                return False
            
            # For high confidence fixes, attempt replacement
            if suggestion.confidence == "high" and vuln.category in (
                VulnCategory.HARDCODED_SECRET,
                VulnCategory.PATH_TRAVERSAL
            ):
                # Add fix as comment before the line
                indent = len(lines[vuln_line_idx]) - len(lines[vuln_line_idx].lstrip())
                fix_lines = suggestion.fixed_code.split('\n')
                commented_fix = [" " * indent + "# SECURITY FIX APPLIED:"]
                for line in fix_lines:
                    commented_fix.append(" " * indent + "# " + line)
                
                lines[vuln_line_idx] = '\n'.join(commented_fix) + '\n' + lines[vuln_line_idx]
                
                path.write_text('\n'.join(lines))
                console.print(f"[green]✓[/green] Applied fix comment to {file_path}:{vuln.line_number}")
                return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]Failed to apply fix:[/red] {e}")
            return False
    
    def display_suggestions(self, suggestions: List[RemediationSuggestion]):
        """Display remediation suggestions in console."""
        if not suggestions:
            console.print("[green]No remediation suggestions available[/green]")
            return
        
        console.print(f"\n[bold]Remediation Suggestions:[/bold] ({len(suggestions)} total)")
        
        for suggestion in suggestions:
            color = "green" if suggestion.confidence == "high" else "yellow" if suggestion.confidence == "medium" else "red"
            
            console.print(f"\n[{color}]●[/[{color}] {suggestion.title}")
            console.print(f"   Confidence: {suggestion.confidence}")
            if suggestion.requires_review:
                console.print("   [yellow]⚠ Requires manual review[/yellow]")
            
            console.print(f"\n   [dim]Original:[/dim]")
            for line in suggestion.original_code.split('\n')[:3]:
                console.print(f"   [red]- {line}[/red]")
            
            console.print(f"\n   [dim]Suggested Fix:[/dim]")
            for line in suggestion.fixed_code.split('\n')[:5]:
                console.print(f"   [green]+ {line}[/green]")
    
    def generate_patch(self, suggestions: List[RemediationSuggestion]) -> str:
        """Generate a unified diff-style patch file."""
        lines = ["# Security Remediation Patch", "# Generated by Security Oracle", ""]
        
        for suggestion in suggestions:
            lines.extend([
                f"## {suggestion.vuln_id}: {suggestion.title}",
                "",
                f"### Description",
                suggestion.description,
                "",
                f"### Original Code",
                "```python",
                suggestion.original_code,
                "```",
                "",
                f"### Fixed Code",
                "```python",
                suggestion.fixed_code,
                "```",
                "",
                f"### Explanation",
                suggestion.explanation,
                "",
                "---",
                ""
            ])
        
        return '\n'.join(lines)