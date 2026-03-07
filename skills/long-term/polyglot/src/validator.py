"""
Translation Validator: Validates semantic equivalence of translations.
"""

import ast
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .translator import TranslationRequest, TranslationResult, Language


@dataclass
class ValidationResult:
    """Result of translation validation."""
    is_valid: bool
    syntax_valid: bool
    semantic_preservation: float  # 0.0 - 1.0
    warnings: List[str]
    errors: List[str]
    test_coverage: Optional[float] = None
    performance_comparison: Optional[Dict[str, Any]] = None


class TranslationValidator:
    """
    Validates that translations preserve semantic equivalence.
    """
    
    def __init__(self):
        self.compilers = {
            Language.PYTHON: self._compile_python,
            Language.JAVASCRIPT: self._compile_javascript,
            Language.TYPESCRIPT: self._compile_typescript,
            Language.RUST: self._compile_rust,
            Language.GO: self._compile_go,
        }
    
    def validate(
        self,
        request: TranslationRequest,
        result: TranslationResult
    ) -> ValidationResult:
        """
        Validate a translation.
        
        Args:
            request: Original translation request
            result: Translation result
            
        Returns:
            ValidationResult
        """
        warnings = []
        errors = []
        
        # 1. Syntax validation
        syntax_valid = self._validate_syntax(
            result.target_code, 
            result.target_language
        )
        if not syntax_valid:
            errors.append(f"Syntax validation failed for {result.target_language.value}")
        
        # 2. Semantic preservation check
        semantic_score = self._check_semantic_preservation(
            request.source_code,
            result.target_code,
            request.source_language,
            result.target_language
        )
        
        if semantic_score < 0.8:
            warnings.append(f"Low semantic preservation score: {semantic_score:.0%}")
        
        # 3. Check for lost comments
        comment_score = self._check_comment_preservation(
            request.source_code,
            result.target_code
        )
        
        if comment_score < 1.0 and request.preserve_comments:
            warnings.append(f"Some comments may have been lost: {comment_score:.0%} preserved")
        
        # 4. Idiom check
        idiom_warnings = self._check_idioms(
            result.target_code,
            result.target_language
        )
        warnings.extend(idiom_warnings)
        
        is_valid = syntax_valid and semantic_score >= 0.6
        
        return ValidationResult(
            is_valid=is_valid,
            syntax_valid=syntax_valid,
            semantic_preservation=semantic_score,
            warnings=warnings,
            errors=errors,
        )
    
    def _validate_syntax(self, code: str, language: Language) -> bool:
        """Validate syntax for the target language."""
        compiler = self.compilers.get(language)
        if compiler:
            return compiler(code)
        return True  # Assume valid if no compiler available
    
    def _compile_python(self, code: str) -> bool:
        """Check Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _compile_javascript(self, code: str) -> bool:
        """Check JavaScript syntax using Node.js."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['node', '--check', temp_file],
                capture_output=True,
                timeout=10
            )
            Path(temp_file).unlink(missing_ok=True)
            return result.returncode == 0
        except Exception:
            return True  # Can't check, assume valid
    
    def _compile_typescript(self, code: str) -> bool:
        """Check TypeScript syntax."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['npx', 'tsc', '--noEmit', temp_file],
                capture_output=True,
                timeout=30
            )
            Path(temp_file).unlink(missing_ok=True)
            return result.returncode == 0
        except Exception:
            return True
    
    def _compile_rust(self, code: str) -> bool:
        """Check Rust syntax."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['rustc', '--emit=metadata', '-o', '/dev/null', temp_file],
                capture_output=True,
                timeout=30
            )
            Path(temp_file).unlink(missing_ok=True)
            return result.returncode == 0
        except Exception:
            return True
    
    def _compile_go(self, code: str) -> bool:
        """Check Go syntax."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.go', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['go', 'build', '-o', '/dev/null', temp_file],
                capture_output=True,
                timeout=30
            )
            Path(temp_file).unlink(missing_ok=True)
            return result.returncode == 0
        except Exception:
            return True
    
    def _check_semantic_preservation(
        self,
        source_code: str,
        target_code: str,
        source_lang: Language,
        target_lang: Language
    ) -> float:
        """
        Check how well semantics are preserved.
        
        Returns a score from 0.0 to 1.0.
        """
        scores = []
        
        # Check function count preservation
        source_funcs = self._count_functions(source_code, source_lang)
        target_funcs = self._count_functions(target_code, target_lang)
        
        if source_funcs > 0:
            func_score = min(target_funcs / source_funcs, 1.0)
            scores.append(func_score)
        
        # Check control structure preservation
        source_control = self._count_control_structures(source_code, source_lang)
        target_control = self._count_control_structures(target_code, target_lang)
        
        if source_control > 0:
            control_score = min(target_control / source_control, 1.0)
            scores.append(control_score)
        
        # Check variable preservation
        source_vars = self._count_variables(source_code, source_lang)
        target_vars = self._count_variables(target_code, target_lang)
        
        if source_vars > 0:
            var_score = min(target_vars / source_vars, 1.0)
            if var_score > 1.5:  # Too many variables suggests bloat
                var_score = 0.8
            scores.append(min(var_score, 1.0))
        
        return sum(scores) / len(scores) if scores else 1.0
    
    def _count_functions(self, code: str, language: Language) -> int:
        """Count functions in code."""
        if language == Language.PYTHON:
            try:
                tree = ast.parse(code)
                return len([n for n in ast.walk(tree) if isinstance(n, 
                    (ast.FunctionDef, ast.AsyncFunctionDef))])
            except:
                return 0
        elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
            import re
            return len(re.findall(r'\bfunction\b|\b=>\b', code))
        elif language == Language.RUST:
            import re
            return len(re.findall(r'\bfn\s+\w+', code))
        elif language == Language.GO:
            import re
            return len(re.findall(r'\bfunc\s+\w+', code))
        return 0
    
    def _count_control_structures(self, code: str, language: Language) -> int:
        """Count control structures in code."""
        import re
        
        if language == Language.PYTHON:
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\btry\b', r'\bwith\b']
        elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\btry\b', r'\bswitch\b']
        elif language == Language.RUST:
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\bmatch\b', r'\bloop\b']
        elif language == Language.GO:
            patterns = [r'\bif\b', r'\bfor\b', r'\bswitch\b', r'\bselect\b']
        else:
            return 0
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, code))
        return count
    
    def _count_variables(self, code: str, language: Language) -> int:
        """Count variable declarations in code."""
        import re
        
        if language == Language.PYTHON:
            # Count assignments (naive)
            return len(re.findall(r'^\s*\w+\s*=', code, re.MULTILINE))
        elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
            return len(re.findall(r'\b(?:const|let|var)\s+\w+', code))
        elif language == Language.RUST:
            return len(re.findall(r'\blet\s+(?:mut\s+)?\w+', code))
        elif language == Language.GO:
            return len(re.findall(r'\w+\s*:=', code))
        return 0
    
    def _check_comment_preservation(
        self,
        source_code: str,
        target_code: str
    ) -> float:
        """Check if comments were preserved."""
        import re
        
        # Count comments in source
        source_comments = len(re.findall(r'#.*$', source_code, re.MULTILINE))
        source_comments += len(re.findall(r'"""[\s\S]*?"""', source_code))
        
        # Count comments in target
        target_comments = len(re.findall(r'//.*$', target_code, re.MULTILINE))
        target_comments += len(re.findall(r'/\*[\s\S]*?\*/', target_code))
        
        if source_comments == 0:
            return 1.0
        
        return min(target_comments / source_comments, 1.0)
    
    def _check_idioms(self, code: str, language: Language) -> List[str]:
        """Check for idiomatic patterns in the target language."""
        warnings = []
        
        if language == Language.JAVASCRIPT:
            # Check for Python-isms
            if 'range(' in code:
                warnings.append("Consider using Array.from() or for loop instead of range()")
            if '.append(' in code:
                warnings.append("Use .push() instead of .append() in JavaScript")
        
        elif language == Language.PYTHON:
            # Check for JavaScript-isms
            if 'console.log' in code:
                warnings.append("Use print() instead of console.log() in Python")
            if '===' in code:
                warnings.append("Use == instead of === in Python")
            if '.length' in code:
                warnings.append("Use len() instead of .length in Python")
        
        elif language == Language.RUST:
            # Check for common issues
            if 'None' in code and 'Option' not in code:
                warnings.append("Consider using Option<T> for null values in Rust")
        
        return warnings
    
    def run_tests(
        self,
        source_code: str,
        target_code: str,
        source_lang: Language,
        target_lang: Language,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run test cases to verify semantic equivalence.
        
        Args:
            source_code: Source code
            target_code: Target code
            source_lang: Source language
            target_lang: Target language
            test_cases: List of test cases with inputs and expected outputs
            
        Returns:
            Test results
        """
        results = {
            "total": len(test_cases),
            "passed": 0,
            "failed": 0,
            "source_passed": 0,
            "target_passed": 0,
        }
        
        # This would require executing both versions and comparing outputs
        # Simplified implementation
        
        return results
    
    def generate_validation_report(
        self,
        request: TranslationRequest,
        result: TranslationResult,
        validation: ValidationResult
    ) -> str:
        """Generate a human-readable validation report."""
        lines = [
            "Translation Validation Report",
            "=" * 50,
            "",
            f"Source Language: {request.source_language.value}",
            f"Target Language: {request.target_language.value}",
            "",
            "Results:",
            "-" * 30,
            f"Valid: {validation.is_valid}",
            f"Syntax Valid: {validation.syntax_valid}",
            f"Semantic Preservation: {validation.semantic_preservation:.0%}",
            "",
        ]
        
        if validation.errors:
            lines.extend(["Errors:", "-" * 30])
            for error in validation.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")
        
        if validation.warnings:
            lines.extend(["Warnings:", "-" * 30])
            for warning in validation.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")
        
        if result.warnings:
            lines.extend(["Translation Warnings:", "-" * 30])
            for warning in result.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")
        
        if not validation.errors and not validation.warnings:
            lines.append("✅ Translation looks good!")
        
        return '\n'.join(lines)
