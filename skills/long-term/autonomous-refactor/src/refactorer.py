"""
Refactorer: Applies automated refactorings to code.
"""

import ast
import re
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import astor

from .detector import CodeSmell, SmellType


class RefactoringType(Enum):
    """Types of automated refactorings."""
    EXTRACT_METHOD = auto()
    EXTRACT_CLASS = auto()
    RENAME_VARIABLE = auto()
    INLINE_VARIABLE = auto()
    MOVE_METHOD = auto()
    INTRODUCE_PARAMETER_OBJECT = auto()
    REPLACE_CONDITIONAL_WITH_POLYMORPHISM = auto()
    REMOVE_DUPLICATION = auto()
    ADD_DOCSTRING = auto()
    REMOVE_UNUSED_IMPORT = auto()
    SIMPLIFY_CONDITIONAL = auto()
    REPLACE_MAGIC_NUMBERS = auto()


@dataclass
class Refactoring:
    """A refactoring operation."""
    refactoring_type: RefactoringType
    description: str
    original_code: str
    refactored_code: str
    filename: str
    line_start: int
    line_end: int
    confidence: float
    breaking_change: bool = False
    tests_needed: bool = True
    verification_steps: List[str] = field(default_factory=list)


@dataclass
class RefactoringHistory:
    """History of refactorings applied."""
    refactorings: List[Refactoring] = field(default_factory=list)
    rejected: List[Tuple[Refactoring, str]] = field(default_factory=list)
    
    def add(self, refactoring: Refactoring):
        self.refactorings.append(refactoring)
    
    def reject(self, refactoring: Refactoring, reason: str):
        self.rejected.append((refactoring, reason))
    
    def get_success_rate(self) -> float:
        total = len(self.refactorings) + len(self.rejected)
        return len(self.refactorings) / total if total > 0 else 0.0


class Refactorer:
    """
    Applies automated refactorings to code.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.history = RefactoringHistory()
        self._load_refactoring_strategies()
    
    def _load_refactoring_strategies(self):
        """Load refactoring strategies for different smell types."""
        self.strategies = {
            SmellType.LONG_METHOD: self._refactor_long_method,
            SmellType.TOO_MANY_PARAMETERS: self._refactor_too_many_params,
            SmellType.MISSING_DOCSTRING: self._refactor_missing_docstring,
            SmellType.UNUSED_IMPORT: self._refactor_unused_import,
            SmellType.MAGIC_NUMBER: self._refactor_magic_numbers,
            SmellType.DEEP_NESTING: self._refactor_deep_nesting,
            SmellType.DATA_CLASS: self._refactor_data_class,
        }
    
    def refactor(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """
        Apply refactoring for a specific code smell.
        
        Args:
            code: Source code
            smell: Code smell to fix
            filename: File path
            
        Returns:
            Refactoring if successful, None otherwise
        """
        strategy = self.strategies.get(smell.smell_type)
        if not strategy:
            return None
        
        try:
            refactoring = strategy(code, smell, filename)
            if refactoring:
                self.history.add(refactoring)
            return refactoring
        except Exception as e:
            print(f"Refactoring failed: {e}")
            return None
    
    def refactor_all(
        self, 
        code: str, 
        smells: List[CodeSmell],
        filename: str
    ) -> List[Refactoring]:
        """
        Apply refactorings for all smells.
        
        Args:
            code: Source code
            smells: List of smells to fix
            filename: File path
            
        Returns:
            List of applied refactorings
        """
        refactorings = []
        current_code = code
        
        # Sort smells by severity and confidence
        sorted_smells = sorted(
            smells,
            key=lambda s: (self._severity_priority(s.severity), -s.confidence)
        )
        
        for smell in sorted_smells:
            refactoring = self.refactor(current_code, smell, filename)
            if refactoring:
                refactorings.append(refactoring)
                current_code = self._apply_refactoring(current_code, refactoring)
        
        return refactorings
    
    def _refactor_long_method(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Extract helper methods from long methods."""
        try:
            tree = ast.parse(code)
            method_name = smell.metadata.get("method_name", "unknown")
            
            # Find the method
            target_method = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == method_name:
                    target_method = node
                    break
            
            if not target_method:
                return None
            
            # Identify extraction candidates (cohesive code blocks)
            extraction_candidates = self._find_extraction_candidates(target_method)
            
            if not extraction_candidates:
                return None
            
            # Generate refactored code
            refactored = self._extract_methods(code, target_method, extraction_candidates)
            
            return Refactoring(
                refactoring_type=RefactoringType.EXTRACT_METHOD,
                description=f"Extracted {len(extraction_candidates)} helper methods from '{method_name}'",
                original_code=code,
                refactored_code=refactored,
                filename=filename,
                line_start=smell.line_start,
                line_end=smell.line_end,
                confidence=0.85,
                breaking_change=False,
                tests_needed=True,
                verification_steps=[
                    "Run existing tests",
                    "Verify extracted methods have correct signatures",
                    "Check that logic is preserved",
                ]
            )
        except Exception as e:
            print(f"Long method refactoring failed: {e}")
            return None
    
    def _refactor_too_many_params(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Introduce parameter object for too many parameters."""
        method_name = smell.metadata.get("method_name", "unknown")
        param_count = smell.metadata.get("param_count", 0)
        
        # Generate parameter object class
        param_class_name = f"{method_name.capitalize()}Params"
        
        refactored = f"""@dataclass
class {param_class_name}:
    \"\"\"Parameters for {method_name}.\"\"\"
    # TODO: Add parameter fields with proper types
    pass

# Original method signature:
# def {method_name}(..., {param_count} parameters)

# Refactored signature:
# def {method_name}(..., params: {param_class_name})
"""
        
        return Refactoring(
            refactoring_type=RefactoringType.INTRODUCE_PARAMETER_OBJECT,
            description=f"Introduced {param_class_name} to reduce parameter count from {param_count}",
            original_code=code,
            refactored_code=refactored,
            filename=filename,
            line_start=smell.line_start,
            line_end=smell.line_end,
            confidence=0.8,
            breaking_change=True,
            tests_needed=True,
            verification_steps=[
                "Update all call sites to use parameter object",
                "Add type hints for the new parameter class",
                "Run integration tests",
            ]
        )
    
    def _refactor_missing_docstring(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Add missing docstrings."""
        name = smell.metadata.get("name", "unknown")
        
        # Generate appropriate docstring
        docstring = f'''    """
    {name.replace('_', ' ').capitalize()}.
    
    TODO: Add detailed description.
    
    Args:
        TODO: Document parameters
        
    Returns:
        TODO: Document return value
        
    Raises:
        TODO: Document exceptions
    """
'''
        
        # Insert docstring after function/class definition
        lines = code.split('\n')
        line_idx = smell.line_start - 1
        
        if line_idx < len(lines):
            # Find the colon position
            line = lines[line_idx]
            indent = len(line) - len(line.lstrip())
            indented_docstring = ' ' * (indent + 4) + docstring.strip()
            
            # Insert after the definition line
            new_lines = lines[:line_idx + 1] + [indented_docstring] + lines[line_idx + 1:]
            refactored = '\n'.join(new_lines)
            
            return Refactoring(
                refactoring_type=RefactoringType.ADD_DOCSTRING,
                description=f"Added docstring to '{name}'",
                original_code=code,
                refactored_code=refactored,
                filename=filename,
                line_start=smell.line_start,
                line_end=smell.line_end,
                confidence=0.95,
                breaking_change=False,
                tests_needed=False,
                verification_steps=[
                    "Review generated docstring for accuracy",
                    "Fill in TODO sections",
                    "Run docstring style checker",
                ]
            )
        
        return None
    
    def _refactor_unused_import(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Remove unused imports."""
        import_name = smell.metadata.get("import_name", "")
        
        lines = code.split('\n')
        new_lines = []
        removed = False
        
        for i, line in enumerate(lines):
            if i + 1 == smell.line_start:
                # Check if this is the import line
                if import_name in line and ('import' in line or 'from' in line):
                    removed = True
                    continue
            new_lines.append(line)
        
        if removed:
            refactored = '\n'.join(new_lines)
            return Refactoring(
                refactoring_type=RefactoringType.REMOVE_UNUSED_IMPORT,
                description=f"Removed unused import: '{import_name}'",
                original_code=code,
                refactored_code=refactored,
                filename=filename,
                line_start=smell.line_start,
                line_end=smell.line_end,
                confidence=0.95,
                breaking_change=False,
                tests_needed=False,
                verification_steps=[
                    "Verify code still runs",
                    "Run linter to check for any issues",
                ]
            )
        
        return None
    
    def _refactor_magic_numbers(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Replace magic numbers with named constants."""
        number = smell.metadata.get("number", "0")
        
        # Generate constant name
        constant_name = self._generate_constant_name(number)
        
        refactored = f"""# Add at module level:
{constant_name} = {number}  # TODO: Add descriptive comment

# Replace occurrences of {number} with {constant_name}
"""
        
        return Refactoring(
            refactoring_type=RefactoringType.REPLACE_MAGIC_NUMBERS,
            description=f"Replaced magic number {number} with {constant_name}",
            original_code=code,
            refactored_code=refactored,
            filename=filename,
            line_start=smell.line_start,
            line_end=smell.line_end,
            confidence=0.7,
            breaking_change=False,
            tests_needed=False,
            verification_steps=[
                "Review constant name for clarity",
                "Add descriptive comment explaining the value",
                "Verify all occurrences are replaced",
            ]
        )
    
    def _refactor_deep_nesting(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Reduce nesting using guard clauses."""
        refactored = """# Before: Deep nesting
# if condition1:
#     if condition2:
#         if condition3:
#             do_something()

# After: Guard clauses
# if not condition1:
#     return
# if not condition2:
#     return
# if not condition3:
#     return
# do_something()

TODO: Apply guard clause pattern to reduce nesting
"""
        
        return Refactoring(
            refactoring_type=RefactoringType.SIMPLIFY_CONDITIONAL,
            description="Applied guard clauses to reduce nesting depth",
            original_code=code,
            refactored_code=refactored,
            filename=filename,
            line_start=smell.line_start,
            line_end=smell.line_end,
            confidence=0.75,
            breaking_change=False,
            tests_needed=True,
            verification_steps=[
                "Verify early return conditions are correct",
                "Ensure all code paths are preserved",
                "Run tests to verify behavior",
            ]
        )
    
    def _refactor_data_class(
        self, 
        code: str, 
        smell: CodeSmell,
        filename: str
    ) -> Optional[Refactoring]:
        """Convert to dataclass."""
        class_name = smell.metadata.get("class_name", "Unknown")
        
        refactored = f"""from dataclasses import dataclass

@dataclass
class {class_name}:
    \"\"\"{class_name} data class.\"\"\"
    # TODO: Add fields with type hints
    pass
    
    # Remove boilerplate __init__, __repr__, __eq__ if present
    # Dataclass generates these automatically
"""
        
        return Refactoring(
            refactoring_type=RefactoringType.EXTRACT_CLASS,
            description=f"Converted '{class_name}' to @dataclass",
            original_code=code,
            refactored_code=refactored,
            filename=filename,
            line_start=smell.line_start,
            line_end=smell.line_end,
            confidence=0.8,
            breaking_change=False,
            tests_needed=True,
            verification_steps=[
                "Add type hints for all fields",
                "Review for any custom methods that need to be preserved",
                "Run tests to verify serialization still works",
            ]
        )
    
    def _find_extraction_candidates(self, method: ast.FunctionDef) -> List[Tuple[int, int, str]]:
        """Find code blocks that can be extracted into methods."""
        candidates = []
        
        # Look for cohesive blocks (simple heuristic)
        current_block_start = None
        current_block = []
        
        for i, stmt in enumerate(method.body):
            if isinstance(stmt, (ast.For, ast.While)):
                # Loops are good extraction candidates
                if len(stmt.body) > 3:
                    block_code = astor.to_source(stmt)
                    candidates.append((stmt.lineno, stmt.end_lineno or stmt.lineno, block_code))
            elif isinstance(stmt, ast.If):
                # Large if blocks
                if len(stmt.body) > 5:
                    block_code = astor.to_source(stmt)
                    candidates.append((stmt.lineno, stmt.end_lineno or stmt.lineno, block_code))
        
        return candidates
    
    def _extract_methods(
        self, 
        code: str, 
        method: ast.FunctionDef,
        candidates: List[Tuple[int, int, str]]
    ) -> str:
        """Extract code blocks into separate methods."""
        # This is a simplified implementation
        # A full implementation would use AST transformations
        return code  # Placeholder
    
    def _generate_constant_name(self, number: str) -> str:
        """Generate a name for a magic number constant."""
        # Map common numbers to descriptive names
        common_names = {
            "60": "SECONDS_PER_MINUTE",
            "3600": "SECONDS_PER_HOUR",
            "86400": "SECONDS_PER_DAY",
            "1024": "BYTES_PER_KB",
            "1000": "MILLISECONDS_PER_SECOND",
            "7": "DAYS_PER_WEEK",
            "30": "DAYS_PER_MONTH",
            "365": "DAYS_PER_YEAR",
        }
        
        if number in common_names:
            return common_names[number]
        
        return f"CONSTANT_{number}"
    
    def _severity_priority(self, severity: str) -> int:
        """Convert severity to priority number."""
        priorities = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return priorities.get(severity, 4)
    
    def _apply_refactoring(self, code: str, refactoring: Refactoring) -> str:
        """Apply a refactoring to the code."""
        # In a real implementation, this would properly merge changes
        return refactoring.refactored_code
    
    def generate_refactoring_plan(
        self, 
        smells: List[CodeSmell],
        max_effort_hours: float = 4.0
    ) -> Dict[str, Any]:
        """
        Generate a refactoring plan prioritizing high-impact changes.
        
        Args:
            smells: List of smells to address
            max_effort_hours: Maximum effort to plan
            
        Returns:
            Refactoring plan
        """
        # Estimate effort for each smell type
        effort_estimates = {
            SmellType.UNUSED_IMPORT: 0.1,
            SmellType.MISSING_DOCSTRING: 0.25,
            SmellType.MAGIC_NUMBER: 0.5,
            SmellType.DEEP_NESTING: 1.0,
            SmellType.LONG_METHOD: 2.0,
            SmellType.TOO_MANY_PARAMETERS: 1.5,
            SmellType.GOD_CLASS: 4.0,
            SmellType.LONG_CLASS: 3.0,
        }
        
        # Sort by impact/effort ratio
        prioritized = []
        for smell in smells:
            effort = effort_estimates.get(smell.smell_type, 1.0)
            impact = self._severity_score(smell.severity) * smell.confidence
            ratio = impact / effort
            prioritized.append((smell, effort, impact, ratio))
        
        prioritized.sort(key=lambda x: -x[3])  # Sort by ratio descending
        
        # Select items fitting in budget
        plan = []
        total_effort = 0.0
        
        for smell, effort, impact, ratio in prioritized:
            if total_effort + effort <= max_effort_hours:
                plan.append({
                    "smell": smell,
                    "effort_hours": effort,
                    "impact_score": impact,
                    "refactoring_type": smell.smell_type.name,
                })
                total_effort += effort
        
        return {
            "total_smells": len(smells),
            "planned_refactorings": len(plan),
            "total_effort_hours": total_effort,
            "remaining_smells": len(smells) - len(plan),
            "items": plan,
        }
    
    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score."""
        scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return scores.get(severity, 1)
