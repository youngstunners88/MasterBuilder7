"""
Code Smell Detector: Identifies code quality issues.
"""

import ast
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict


class SmellType(Enum):
    """Types of code smells."""
    LONG_METHOD = auto()
    LONG_CLASS = auto()
    TOO_MANY_PARAMETERS = auto()
    DUPLICATE_CODE = auto()
    COMPLEX_CONDITIONAL = auto()
    DEEP_NESTING = auto()
    MISSING_DOCSTRING = auto()
    UNUSED_VARIABLE = auto()
    UNUSED_IMPORT = auto()
    MAGIC_NUMBER = auto()
    FEATURE_ENVY = auto()
    GOD_CLASS = auto()
    DATA_CLASS = auto()
    TEMPORARY_FIELD = auto()
    MESSAGE_CHAIN = auto()
    MIDDLE_MAN = auto()
    INAPPROPRIATE_INTIMACY = auto()
    PRIMITIVE_OBSESSION = auto()
    SWITCH_STATEMENTS = auto()
    PARALLEL_INHERITANCE = auto()
    SHOTGUN_SURGERY = auto()
    DIVERGENT_CHANGE = auto()
    LAZY_CLASS = auto()
    SPECULATIVE_GENERALITY = auto()


@dataclass
class CodeSmell:
    """A detected code smell."""
    smell_type: SmellType
    message: str
    filename: str
    line_start: int
    line_end: int
    severity: str  # critical, high, medium, low
    confidence: float  # 0.0 - 1.0
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodeSmellDetector:
    """
    Detects code smells in Python and JavaScript code.
    """
    
    DEFAULT_THRESHOLDS = {
        "max_method_lines": 50,
        "max_class_lines": 300,
        "max_parameters": 5,
        "max_nesting_depth": 3,
        "max_complexity": 10,
        "min_similarity_for_duplicate": 0.8,
        "max_class_methods": 20,
    }
    
    def __init__(self, thresholds: Optional[Dict[str, int]] = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._duplication_cache: Dict[str, List[str]] = {}
    
    def detect(self, code: str, filename: str, language: str = "python") -> List[CodeSmell]:
        """
        Detect all code smells in the given code.
        
        Args:
            code: Source code
            filename: File path
            language: Programming language
            
        Returns:
            List of detected code smells
        """
        smells = []
        
        if language == "python":
            smells.extend(self._detect_python_smells(code, filename))
        elif language in ["javascript", "typescript"]:
            smells.extend(self._detect_js_smells(code, filename))
        
        # Language-agnostic detection
        smells.extend(self._detect_general_smells(code, filename))
        
        return sorted(smells, key=lambda s: (-self._severity_score(s.severity), -s.confidence))
    
    def detect_in_file(self, filepath: Path) -> List[CodeSmell]:
        """Detect smells in a file."""
        code = filepath.read_text()
        language = self._detect_language(filepath.suffix)
        return self.detect(code, str(filepath), language)
    
    def detect_in_project(self, project_path: Path) -> Dict[str, List[CodeSmell]]:
        """Detect smells across an entire project."""
        all_smells = {}
        
        for file_path in project_path.rglob("*"):
            if file_path.is_file() and self._is_source_file(file_path):
                try:
                    smells = self.detect_in_file(file_path)
                    if smells:
                        all_smells[str(file_path)] = smells
                except Exception as e:
                    all_smells[str(file_path)] = [CodeSmell(
                        smell_type=SmellType.LAZY_CLASS,  # Using as generic error
                        message=f"Failed to analyze: {e}",
                        filename=str(file_path),
                        line_start=0,
                        line_end=0,
                        severity="error",
                        confidence=1.0
                    )]
        
        return all_smells
    
    def _detect_python_smells(self, code: str, filename: str) -> List[CodeSmell]:
        """Detect Python-specific smells."""
        smells = []
        
        try:
            tree = ast.parse(code)
            lines = code.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    smells.extend(self._check_method_smells(node, filename, lines))
                elif isinstance(node, ast.ClassDef):
                    smells.extend(self._check_class_smells(node, filename, lines))
                elif isinstance(node, ast.If):
                    smells.extend(self._check_conditional_smells(node, filename))
            
            # Module-level checks
            smells.extend(self._check_import_smells(tree, filename))
            smells.extend(self._check_docstring_smells(tree, filename))
            
        except SyntaxError as e:
            smells.append(CodeSmell(
                smell_type=SmellType.LAZY_CLASS,
                message=f"Syntax error: {e.msg}",
                filename=filename,
                line_start=e.lineno or 0,
                line_end=e.lineno or 0,
                severity="critical",
                confidence=1.0
            ))
        
        return smells
    
    def _check_method_smells(
        self, 
        func: ast.FunctionDef, 
        filename: str,
        lines: List[str]
    ) -> List[CodeSmell]:
        """Check a method for smells."""
        smells = []
        
        # Check method length
        start_line = func.lineno
        end_line = func.end_lineno or start_line
        method_lines = end_line - start_line
        
        if method_lines > self.thresholds["max_method_lines"]:
            smells.append(CodeSmell(
                smell_type=SmellType.LONG_METHOD,
                message=f"Method '{func.name}' is {method_lines} lines (max {self.thresholds['max_method_lines']})",
                filename=filename,
                line_start=start_line,
                line_end=end_line,
                severity="high",
                confidence=0.95,
                suggestions=[
                    f"Extract helper methods from '{func.name}'",
                    "Consider using the Extract Method pattern",
                    "Identify cohesive blocks of code to extract",
                ],
                metadata={"method_name": func.name, "lines": method_lines}
            ))
        
        # Check parameter count
        param_count = len(func.args.args) + len(func.args.kwonlyargs)
        if func.args.vararg:
            param_count += 1
        if func.args.kwarg:
            param_count += 1
        
        if param_count > self.thresholds["max_parameters"]:
            smells.append(CodeSmell(
                smell_type=SmellType.TOO_MANY_PARAMETERS,
                message=f"Method '{func.name}' has {param_count} parameters",
                filename=filename,
                line_start=start_line,
                line_end=start_line,
                severity="medium",
                confidence=0.85,
                suggestions=[
                    "Introduce a parameter object",
                    "Consider the Builder pattern",
                    "Use keyword-only arguments for optional params",
                ],
                metadata={"method_name": func.name, "param_count": param_count}
            ))
        
        # Check nesting depth
        max_depth = self._calculate_nesting_depth(func)
        if max_depth > self.thresholds["max_nesting_depth"]:
            smells.append(CodeSmell(
                smell_type=SmellType.DEEP_NESTING,
                message=f"Method '{func.name}' has nesting depth of {max_depth}",
                filename=filename,
                line_start=start_line,
                line_end=end_line,
                severity="high",
                confidence=0.9,
                suggestions=[
                    "Use early returns to reduce nesting",
                    "Extract nested logic into separate methods",
                    "Consider using guard clauses",
                ],
                metadata={"method_name": func.name, "nesting_depth": max_depth}
            ))
        
        # Check complexity
        complexity = self._calculate_cyclomatic_complexity(func)
        if complexity > self.thresholds["max_complexity"]:
            smells.append(CodeSmell(
                smell_type=SmellType.COMPLEX_CONDITIONAL,
                message=f"Method '{func.name}' has complexity of {complexity}",
                filename=filename,
                line_start=start_line,
                line_end=end_line,
                severity="high",
                confidence=0.9,
                suggestions=[
                    "Simplify complex conditionals",
                    "Extract complex conditions into named methods",
                    "Use polymorphism instead of conditionals",
                ],
                metadata={"method_name": func.name, "complexity": complexity}
            ))
        
        return smells
    
    def _check_class_smells(
        self, 
        cls: ast.ClassDef, 
        filename: str,
        lines: List[str]
    ) -> List[CodeSmell]:
        """Check a class for smells."""
        smells = []
        
        # Check class length
        start_line = cls.lineno
        end_line = cls.end_lineno or start_line
        class_lines = end_line - start_line
        
        if class_lines > self.thresholds["max_class_lines"]:
            smells.append(CodeSmell(
                smell_type=SmellType.LONG_CLASS,
                message=f"Class '{cls.name}' is {class_lines} lines",
                filename=filename,
                line_start=start_line,
                line_end=end_line,
                severity="medium",
                confidence=0.85,
                suggestions=[
                    "Split class by responsibility (SRP)",
                    "Extract cohesive groups of methods",
                ],
                metadata={"class_name": cls.name, "lines": class_lines}
            ))
        
        # Check for God Class
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
        if len(methods) > self.thresholds["max_class_methods"]:
            smells.append(CodeSmell(
                smell_type=SmellType.GOD_CLASS,
                message=f"Class '{cls.name}' has {len(methods)} methods (too many responsibilities)",
                filename=filename,
                line_start=start_line,
                line_end=end_line,
                severity="high",
                confidence=0.8,
                suggestions=[
                    "Apply Extract Class refactoring",
                    "Identify and extract cohesive responsibilities",
                    "Consider the Single Responsibility Principle",
                ],
                metadata={"class_name": cls.name, "method_count": len(methods)}
            ))
        
        # Check for Data Class (only attributes and getters/setters)
        public_methods = [m for m in methods if not m.name.startswith('_')]
        if public_methods and all(
            len(m.body) <= 2 and 
            (m.name.startswith('get_') or m.name.startswith('set_') or m.name.startswith('is_'))
            for m in public_methods
        ):
            smells.append(CodeSmell(
                smell_type=SmellType.DATA_CLASS,
                message=f"Class '{cls.name}' appears to be a data class",
                filename=filename,
                line_start=start_line,
                line_end=end_line,
                severity="low",
                confidence=0.7,
                suggestions=[
                    "Consider using @dataclass decorator",
                    "Move behavior from other classes into this class",
                    "Use a NamedTuple or simple dict if no behavior needed",
                ],
                metadata={"class_name": cls.name}
            ))
        
        return smells
    
    def _check_conditional_smells(
        self, 
        node: ast.If, 
        filename: str
    ) -> List[CodeSmell]:
        """Check conditionals for smells."""
        smells = []
        
        # Check for complex conditionals
        if isinstance(node.test, ast.BoolOp):
            conditions = len(node.test.values)
            if conditions > 3:
                smells.append(CodeSmell(
                    smell_type=SmellType.COMPLEX_CONDITIONAL,
                    message=f"Complex boolean expression with {conditions} conditions",
                    filename=filename,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    severity="medium",
                    confidence=0.8,
                    suggestions=[
                        "Extract conditions into well-named methods",
                        "Use De Morgan's laws to simplify",
                    ],
                    metadata={"condition_count": conditions}
                ))
        
        return smells
    
    def _check_import_smells(self, tree: ast.AST, filename: str) -> List[CodeSmell]:
        """Check for unused imports."""
        smells = []
        
        imported_names = {}
        used_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = node.lineno
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
        
        for name, lineno in imported_names.items():
            if name not in used_names and name != '*':
                smells.append(CodeSmell(
                    smell_type=SmellType.UNUSED_IMPORT,
                    message=f"Unused import: '{name}'",
                    filename=filename,
                    line_start=lineno,
                    line_end=lineno,
                    severity="low",
                    confidence=0.9,
                    suggestions=[f"Remove unused import: {name}"],
                    metadata={"import_name": name}
                ))
        
        return smells
    
    def _check_docstring_smells(self, tree: ast.AST, filename: str) -> List[CodeSmell]:
        """Check for missing docstrings."""
        smells = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    smells.append(CodeSmell(
                        smell_type=SmellType.MISSING_DOCSTRING,
                        message=f"Missing docstring for {node.__class__.__name__.lower()}: '{node.name}'",
                        filename=filename,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        severity="low",
                        confidence=0.95,
                        suggestions=[
                            "Add a docstring explaining purpose",
                            "Document parameters and return values",
                        ],
                        metadata={"name": node.name}
                    ))
        
        return smells
    
    def _detect_js_smells(self, code: str, filename: str) -> List[CodeSmell]:
        """Detect JavaScript-specific smells."""
        smells = []
        lines = code.split('\n')
        
        # Check function length using heuristics
        func_pattern = r'(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\(|\w+\s*\(.*\)\s*{|async\s+\w+\s*\()'
        
        # Check for magic numbers
        magic_number_pattern = r'[^\w.](\d{2,})[^\w.]'
        for i, line in enumerate(lines, 1):
            matches = re.finditer(magic_number_pattern, line)
            for match in matches:
                number = match.group(1)
                if number not in ['0', '1', '100']:
                    smells.append(CodeSmell(
                        smell_type=SmellType.MAGIC_NUMBER,
                        message=f"Magic number: {number}",
                        filename=filename,
                        line_start=i,
                        line_end=i,
                        severity="low",
                        confidence=0.6,
                        suggestions=[f"Extract {number} into a named constant"],
                        metadata={"number": number}
                    ))
        
        # Check nesting depth
        max_depth = 0
        current_depth = 0
        for i, line in enumerate(lines):
            opens = line.count('{') + line.count('(')
            closes = line.count('}') + line.count(')')
            current_depth += opens - closes
            max_depth = max(max_depth, current_depth)
        
        if max_depth > self.thresholds["max_nesting_depth"]:
            smells.append(CodeSmell(
                smell_type=SmellType.DEEP_NESTING,
                message=f"Deep nesting detected: depth {max_depth}",
                filename=filename,
                line_start=1,
                line_end=len(lines),
                severity="high",
                confidence=0.7,
                suggestions=["Reduce nesting with early returns"],
                metadata={"max_depth": max_depth}
            ))
        
        return smells
    
    def _detect_general_smells(self, code: str, filename: str) -> List[CodeSmell]:
        """Detect language-agnostic smells."""
        smells = []
        
        # Check for TODO/FIXME comments (potential technical debt)
        todo_pattern = r'#\s*(TODO|FIXME|XXX|HACK)'
        for i, line in enumerate(code.split('\n'), 1):
            if re.search(todo_pattern, line, re.IGNORECASE):
                smells.append(CodeSmell(
                    smell_type=SmellType.SPECULATIVE_GENERALITY,
                    message="TODO/FIXME comment found - technical debt",
                    filename=filename,
                    line_start=i,
                    line_end=i,
                    severity="low",
                    confidence=0.8,
                    suggestions=["Address TODO items", "Create tickets for tracked work"],
                    metadata={"line": line.strip()}
                ))
        
        return smells
    
    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth of a node."""
        max_depth = 0
        
        def visit(node, depth):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, 
                                     ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit(child, depth + 1)
                else:
                    visit(child, depth)
        
        visit(node, 0)
        return max_depth
    
    def _calculate_cyclomatic_complexity(self, func: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(func):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score."""
        scores = {"critical": 4, "high": 3, "medium": 2, "low": 1, "error": 5}
        return scores.get(severity, 0)
    
    def _detect_language(self, extension: str) -> str:
        """Detect language from file extension."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return mapping.get(extension, "python")
    
    def _is_source_file(self, path: Path) -> bool:
        """Check if file is a source code file."""
        return path.suffix in ['.py', '.js', '.jsx', '.ts', '.tsx']
    
    def detect_duplicates(
        self, 
        files: Dict[str, str], 
        min_lines: int = 5
    ) -> List[CodeSmell]:
        """
        Detect duplicate code across files.
        
        Args:
            files: Dictionary of filename -> content
            min_lines: Minimum lines to consider a duplicate
            
        Returns:
            List of duplicate code smells
        """
        smells = []
        blocks = defaultdict(list)
        
        # Extract code blocks
        for filename, code in files.items():
            lines = code.split('\n')
            for i in range(len(lines) - min_lines + 1):
                block = '\n'.join(lines[i:i + min_lines])
                # Normalize
                normalized = re.sub(r'\s+', ' ', block.strip())
                blocks[normalized].append((filename, i + 1))
        
        # Find duplicates
        for normalized, locations in blocks.items():
            if len(locations) > 1:
                files_involved = list(set(loc[0] for loc in locations))
                if len(files_involved) > 1:
                    smells.append(CodeSmell(
                        smell_type=SmellType.DUPLICATE_CODE,
                        message=f"Duplicate code found in {len(files_involved)} files",
                        filename=files_involved[0],
                        line_start=locations[0][1],
                        line_end=locations[0][1] + min_lines,
                        severity="medium",
                        confidence=0.8,
                        suggestions=[
                            "Extract duplicate code into a shared function",
                            "Create a utility module for common operations",
                        ],
                        metadata={
                            "files": files_involved,
                            "locations": locations,
                            "line_count": min_lines
                        }
                    ))
        
        return smells
    
    def generate_report(self, smells: List[CodeSmell]) -> str:
        """Generate a human-readable report."""
        if not smells:
            return "✅ No code smells detected!"
        
        lines = [
            "Code Smell Detection Report",
            "=" * 60,
            f"Total smells detected: {len(smells)}",
            "",
            "By Severity:",
        ]
        
        by_severity = defaultdict(list)
        for smell in smells:
            by_severity[smell.severity].append(smell)
        
        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                lines.append(f"  {severity.upper()}: {len(by_severity[severity])}")
        
        lines.extend(["", "By Type:"])
        by_type = defaultdict(list)
        for smell in smells:
            by_type[smell.smell_type.name].append(smell)
        
        for smell_type, type_smells in sorted(by_type.items()):
            lines.append(f"  {smell_type}: {len(type_smells)}")
        
        lines.extend(["", "Detailed Findings:", "-" * 60])
        
        for smell in smells[:20]:  # Limit to first 20
            lines.extend([
                "",
                f"[{smell.severity.upper()}] {smell.smell_type.name}",
                f"  File: {smell.filename}:{smell.line_start}",
                f"  Message: {smell.message}",
                f"  Confidence: {smell.confidence:.0%}",
            ])
            if smell.suggestions:
                lines.append("  Suggestions:")
                for suggestion in smell.suggestions:
                    lines.append(f"    - {suggestion}")
        
        if len(smells) > 20:
            lines.append(f"\n... and {len(smells) - 20} more issues")
        
        return '\n'.join(lines)
