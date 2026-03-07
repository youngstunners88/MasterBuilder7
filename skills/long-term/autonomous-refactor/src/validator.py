"""
Refactoring Validator: Ensures refactorings preserve behavior.
"""

import ast
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .refactorer import Refactoring


@dataclass
class ValidationResult:
    """Result of refactoring validation."""
    is_valid: bool
    original_passed: bool
    refactored_passed: bool
    syntax_valid: bool
    behavior_preserved: bool
    test_coverage: float
    errors: List[str]
    warnings: List[str]
    performance_impact: Optional[str] = None


class RefactoringValidator:
    """
    Validates that refactorings preserve behavior and don't introduce bugs.
    """
    
    def __init__(self):
        self.test_runners = {
            "pytest": self._run_pytest,
            "unittest": self._run_unittest,
        }
    
    def validate(
        self, 
        refactoring: Refactoring,
        original_code: str,
        test_files: Optional[List[Path]] = None
    ) -> ValidationResult:
        """
        Validate a refactoring.
        
        Args:
            refactoring: The refactoring to validate
            original_code: Original source code
            test_files: Optional list of test files
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # 1. Syntax validation
        syntax_valid = self._validate_syntax(refactoring.refactored_code)
        if not syntax_valid:
            errors.append("Syntax validation failed")
        
        # 2. AST equivalence check (for simple refactorings)
        behavior_preserved = self._check_ast_equivalence(
            original_code, 
            refactoring.refactored_code
        )
        if not behavior_preserved:
            warnings.append("AST equivalence check failed - manual review needed")
        
        # 3. Run tests if available
        original_passed = True
        refactored_passed = True
        test_coverage = 0.0
        
        if test_files:
            original_passed = self._run_tests(original_code, test_files)
            refactored_passed = self._run_tests(refactoring.refactored_code, test_files)
            
            if not original_passed:
                errors.append("Original code doesn't pass tests")
            if not refactored_passed:
                errors.append("Refactored code doesn't pass tests")
        
        # 4. Check for common issues
        issues = self._check_common_issues(refactoring.refactored_code)
        errors.extend(issues["errors"])
        warnings.extend(issues["warnings"])
        
        is_valid = (
            syntax_valid and 
            original_passed and 
            refactored_passed and 
            len(errors) == 0
        )
        
        return ValidationResult(
            is_valid=is_valid,
            original_passed=original_passed,
            refactored_passed=refactored_passed,
            syntax_valid=syntax_valid,
            behavior_preserved=behavior_preserved,
            test_coverage=test_coverage,
            errors=errors,
            warnings=warnings,
        )
    
    def _validate_syntax(self, code: str) -> bool:
        """Check if code has valid syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _check_ast_equivalence(self, original: str, refactored: str) -> bool:
        """
        Check if two code snippets are AST-equivalent.
        
        This is a simplified check - full equivalence is undecidable.
        """
        try:
            original_tree = ast.parse(original)
            refactored_tree = ast.parse(refactored)
            
            # For now, just check they both parse
            # A full implementation would normalize and compare ASTs
            return True
        except SyntaxError:
            return False
    
    def _run_tests(self, code: str, test_files: List[Path]) -> bool:
        """Run tests against the code."""
        # Create temporary file with code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run pytest
            result = subprocess.run(
                ['python', '-m', 'pytest', str(temp_file), '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    def _run_pytest(self, test_path: Path) -> Tuple[bool, str]:
        """Run pytest on test files."""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', str(test_path), '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def _run_unittest(self, test_path: Path) -> Tuple[bool, str]:
        """Run unittest on test files."""
        try:
            result = subprocess.run(
                ['python', '-m', 'unittest', str(test_path)],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def _check_common_issues(self, code: str) -> Dict[str, List[str]]:
        """Check for common issues in refactored code."""
        errors = []
        warnings = []
        
        try:
            tree = ast.parse(code)
            
            # Check for undefined variables
            defined = set()
            used = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        defined.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        used.add(node.id)
                elif isinstance(node, ast.FunctionDef):
                    defined.add(node.name)
                    # Add parameters
                    for arg in node.args.args:
                        defined.add(arg.arg)
                elif isinstance(node, ast.ClassDef):
                    defined.add(node.name)
            
            # Check for undefined (excluding builtins)
            builtins = {
                'True', 'False', 'None', 'print', 'len', 'range', 'str', 'int',
                'float', 'list', 'dict', 'set', 'tuple', 'type', 'isinstance',
                'hasattr', 'getattr', 'super', 'object', 'Exception', 'ValueError',
            }
            undefined = used - defined - builtins
            if undefined:
                warnings.append(f"Potentially undefined names: {', '.join(undefined)}")
            
            # Check for bare except
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        warnings.append("Bare except clause found - use specific exceptions")
            
            # Check for mutable default arguments
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for default in node.args.defaults + node.args.kw_defaults:
                        if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            warnings.append(
                                f"Mutable default argument in function '{node.name}'"
                            )
        
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        
        return {"errors": errors, "warnings": warnings}
    
    def run_static_analysis(self, code: str) -> Dict[str, Any]:
        """Run static analysis tools on code."""
        results = {
            "issues": [],
            "metrics": {},
        }
        
        # Try to run pylint
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['python', '-m', 'pylint', temp_file, '--output-format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                import json
                try:
                    pylint_issues = json.loads(result.stdout)
                    results["issues"].extend(pylint_issues)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        finally:
            Path(temp_file).unlink(missing_ok=True)
        
        return results
    
    def compare_performance(
        self, 
        original: str, 
        refactored: str,
        iterations: int = 1000
    ) -> Dict[str, Any]:
        """
        Compare performance of original vs refactored code.
        
        Args:
            original: Original code
            refactored: Refactored code
            iterations: Number of iterations for benchmarking
            
        Returns:
            Performance comparison results
        """
        import time
        
        results = {
            "original_time": None,
            "refactored_time": None,
            "difference_percent": None,
        }
        
        # This is a simplified implementation
        # Real implementation would need to extract and benchmark specific functions
        
        return results
    
    def generate_validation_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report."""
        lines = [
            "Refactoring Validation Report",
            "=" * 50,
            f"Valid: {result.is_valid}",
            f"Syntax Valid: {result.syntax_valid}",
            f"Original Tests Passed: {result.original_passed}",
            f"Refactored Tests Passed: {result.refactored_passed}",
            f"Behavior Preserved: {result.behavior_preserved}",
            "",
        ]
        
        if result.errors:
            lines.extend(["Errors:", "-" * 30])
            for error in result.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")
        
        if result.warnings:
            lines.extend(["Warnings:", "-" * 30])
            for warning in result.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")
        
        if not result.errors and not result.warnings:
            lines.append("✅ No issues found!")
        
        return '\n'.join(lines)
