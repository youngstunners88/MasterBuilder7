"""
Code Validator: Validates generated code for correctness and style.
"""

import ast
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationIssue:
    """A code validation issue."""
    severity: str  # error, warning, info
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    rule: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_valid: bool
    issues: List[ValidationIssue]
    metrics: Dict[str, Any]


class CodeValidator:
    """
    Validates generated code for correctness, style, and best practices.
    """
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, List[callable]]:
        """Load validation rules."""
        return {
            "python": [
                self._check_syntax,
                self._check_imports,
                self._check_naming_conventions,
                self._check_docstrings,
                self._check_complexity,
            ],
            "javascript": [
                self._check_js_syntax,
            ],
        }
    
    def validate_files(
        self, 
        files: Dict[str, str], 
        language: str
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple files.
        
        Args:
            files: Dictionary of filename -> content
            language: Programming language
            
        Returns:
            Dictionary of filename -> ValidationResult
        """
        results = {}
        for filename, content in files.items():
            results[filename] = self.validate(content, language, filename)
        return results
    
    def validate(
        self, 
        code: str, 
        language: str,
        filename: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate code.
        
        Args:
            code: Source code to validate
            language: Programming language
            filename: Optional filename for context
            
        Returns:
            ValidationResult
        """
        issues = []
        metrics = {}
        
        # Run language-specific validators
        lang_rules = self.rules.get(language, [])
        for rule in lang_rules:
            try:
                rule_issues = rule(code, filename)
                issues.extend(rule_issues)
            except Exception as e:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"Validation rule failed: {e}",
                    rule=rule.__name__
                ))
        
        # Calculate metrics
        metrics = self._calculate_metrics(code, language)
        
        # Determine if valid (no errors)
        is_valid = not any(i.severity == "error" for i in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            metrics=metrics
        )
    
    def _check_syntax(
        self, 
        code: str, 
        filename: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Check Python syntax."""
        issues = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity="error",
                message=f"Syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset,
                rule="syntax"
            ))
        return issues
    
    def _check_imports(
        self, 
        code: str, 
        filename: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Check import statements."""
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ["os", "sys", "subprocess"]:
                            issues.append(ValidationIssue(
                                severity="warning",
                                message=f"Potentially dangerous import: {alias.name}",
                                line=node.lineno,
                                rule="security"
                            ))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "password" in node.module.lower():
                        issues.append(ValidationIssue(
                            severity="warning",
                            message=f"Suspicious import: {node.module}",
                            line=node.lineno,
                            rule="security"
                        ))
        except SyntaxError:
            pass
        return issues
    
    def _check_naming_conventions(
        self, 
        code: str, 
        filename: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Check Python naming conventions."""
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name[0].isupper():
                        issues.append(ValidationIssue(
                            severity="warning",
                            message=f"Function name should be lowercase: {node.name}",
                            line=node.lineno,
                            rule="pep8"
                        ))
                elif isinstance(node, ast.ClassDef):
                    if not node.name[0].isupper():
                        issues.append(ValidationIssue(
                            severity="warning",
                            message=f"Class name should be CamelCase: {node.name}",
                            line=node.lineno,
                            rule="pep8"
                        ))
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    if len(node.id) == 1 and node.id not in ['i', 'j', 'k', 'x', 'y', 'z']:
                        issues.append(ValidationIssue(
                            severity="info",
                            message=f"Consider more descriptive name: {node.id}",
                            line=node.lineno,
                            rule="readability"
                        ))
        except SyntaxError:
            pass
        return issues
    
    def _check_docstrings(
        self, 
        code: str, 
        filename: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Check for missing docstrings."""
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        issues.append(ValidationIssue(
                            severity="info",
                            message=f"Missing docstring for {node.__class__.__name__.lower()}: {node.name}",
                            line=node.lineno,
                            rule="documentation"
                        ))
        except SyntaxError:
            pass
        return issues
    
    def _check_complexity(
        self, 
        code: str, 
        filename: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Check code complexity."""
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Simple complexity check: count branches
                    branches = 0
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.With, 
                                              ast.Try, ast.ExceptHandler)):
                            branches += 1
                    
                    if branches > 10:
                        issues.append(ValidationIssue(
                            severity="warning",
                            message=f"Function {node.name} is complex ({branches} branches). Consider refactoring.",
                            line=node.lineno,
                            rule="complexity"
                        ))
                    
                    # Check function length
                    lines = code.split('\n')
                    func_lines = 0
                    start_line = node.lineno - 1
                    end_line = node.end_lineno or start_line + 1
                    func_lines = end_line - start_line
                    
                    if func_lines > 50:
                        issues.append(ValidationIssue(
                            severity="warning",
                            message=f"Function {node.name} is too long ({func_lines} lines). Consider breaking it up.",
                            line=node.lineno,
                            rule="complexity"
                        ))
        except SyntaxError:
            pass
        return issues
    
    def _check_js_syntax(
        self, 
        code: str, 
        filename: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Basic JavaScript syntax checks."""
        issues = []
        
        # Check for unclosed brackets
        brackets = {"(": ")", "[": "]", "{": "}"}
        stack = []
        for i, char in enumerate(code):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"Unmatched closing bracket: {char}",
                        column=i,
                        rule="syntax"
                    ))
                else:
                    stack.pop()
        
        if stack:
            for char, pos in stack:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"Unclosed bracket: {char}",
                    column=pos,
                    rule="syntax"
                ))
        
        # Check for common JS issues
        if "var " in code:
            issues.append(ValidationIssue(
                severity="warning",
                message="Use 'let' or 'const' instead of 'var'",
                rule="best_practice"
            ))
        
        if "==" in code and "===" not in code:
            issues.append(ValidationIssue(
                severity="warning",
                message="Consider using '===' instead of '=='",
                rule="best_practice"
            ))
        
        return issues
    
    def _calculate_metrics(self, code: str, language: str) -> Dict[str, Any]:
        """Calculate code metrics."""
        lines = code.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        
        metrics = {
            "total_lines": len(lines),
            "code_lines": len(non_empty_lines),
            "blank_lines": len(lines) - len(non_empty_lines),
            "avg_line_length": sum(len(l) for l in non_empty_lines) / max(len(non_empty_lines), 1),
        }
        
        if language == "python":
            try:
                tree = ast.parse(code)
                metrics["functions"] = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
                metrics["classes"] = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
                metrics["imports"] = len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))])
            except SyntaxError:
                pass
        
        return metrics
    
    def format_report(self, result: ValidationResult, filename: str = "code") -> str:
        """Format validation results as a report."""
        lines = [
            f"Validation Report for {filename}",
            "=" * 50,
            f"Valid: {result.is_valid}",
            f"Issues: {len(result.issues)}",
            "",
            "Issues:",
            "-" * 50,
        ]
        
        for issue in result.issues:
            location = ""
            if issue.line:
                location = f" (line {issue.line}"
                if issue.column:
                    location += f", col {issue.column}"
                location += ")"
            
            lines.append(f"[{issue.severity.upper()}] {issue.message}{location}")
        
        lines.extend([
            "",
            "Metrics:",
            "-" * 50,
        ])
        
        for key, value in result.metrics.items():
            lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)


class SecurityValidator(CodeValidator):
    """
    Security-focused code validator.
    """
    
    DANGEROUS_PATTERNS = {
        "python": [
            (r'eval\s*\(', "Dangerous eval() usage"),
            (r'exec\s*\(', "Dangerous exec() usage"),
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell=True is dangerous"),
            (r'os\.system\s*\(', "os.system() is dangerous"),
            (r'input\s*\(', "input() can be unsafe - validate input"),
            (r'\.format\s*\([^)]*%', "Potential format string vulnerability"),
            (r'f["\'].*\{.*\}.*["\'].*\.format', "Format string with f-string mix"),
            (r'sql.*%.*%', "Potential SQL injection"),
            (r'pickle\.(loads|load)', "Pickle can execute arbitrary code"),
            (r'yaml\.load\s*\([^)]*\)(?!.*Loader)', "yaml.load without Loader is unsafe"),
        ],
        "javascript": [
            (r'eval\s*\(', "Dangerous eval() usage"),
            (r'new\s+Function\s*\(', "new Function() is dangerous"),
            (r'document\.write\s*\(', "document.write can be unsafe"),
            (r'innerHTML\s*=', "innerHTML assignment can cause XSS"),
            (r'\.exec\s*\(', "Potential code injection"),
        ],
    }
    
    def validate_security(self, code: str, language: str) -> ValidationResult:
        """Validate code for security issues."""
        issues = []
        
        patterns = self.DANGEROUS_PATTERNS.get(language, [])
        for pattern, message in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                # Find line number
                line_num = code[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    severity="error",
                    message=message,
                    line=line_num,
                    rule="security"
                ))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            metrics={"security_issues": len(issues)}
        )
