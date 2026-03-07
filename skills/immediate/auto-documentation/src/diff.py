"""
Diff module for auto-documentation.
Analyzes code changes and determines documentation impact.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from loguru import logger


class ChangeType(Enum):
    """Type of code change."""
    NEW_FEATURE = "new_feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DEPRECATED = "deprecated"
    REMOVED = "removed"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass
class CodeChange:
    """Represents a detected code change."""
    file_path: str
    change_type: ChangeType
    element_type: str  # function, class, route, model, etc.
    name: str
    description: str
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    line_numbers: List[int] = field(default_factory=list)
    impact_level: str = "low"  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'change_type': self.change_type.value,
            'element_type': self.element_type,
            'name': self.name,
            'description': self.description,
            'old_signature': self.old_signature,
            'new_signature': self.new_signature,
            'line_numbers': self.line_numbers,
            'impact_level': self.impact_level,
        }


class DiffAnalyzer:
    """Analyzes code changes to determine documentation impact."""
    
    # Patterns for detecting change types
    CHANGE_PATTERNS = {
        ChangeType.NEW_FEATURE: [
            r'def\s+\w+.*\(',
            r'class\s+\w+',
            r'@app\.\w+',  # Flask/FastAPI routes
            r'router\.',  # Express routes
            r'@Get|@Post|@Put|@Delete',  # Decorators
        ],
        ChangeType.BUGFIX: [
            r'fix|Fix|FIX',
            r'bug|Bug|BUG',
            r'resolve|Resolve',
            r'handle.*error',
        ],
        ChangeType.REFACTOR: [
            r'refactor|Refactor|REFACTOR',
            r'rename|Rename',
            r'move|Move',
            r'extract|Extract',
        ],
        ChangeType.DEPRECATED: [
            r'deprecated|Deprecated|DEPRECATED',
            r'@deprecated',
            r'warn\(.*deprecated',
        ],
        ChangeType.REMOVED: [
            r'remove|Remove|REMOVE',
            r'delete|Delete|DELETE',
        ],
    }
    
    # Impact level indicators
    IMPACT_INDICATORS = {
        'critical': [
            r'auth|authentication|Auth',
            r'security|Security',
            r'database.*schema|migration',
            r'api.*version',
            r'breaking.*change',
        ],
        'high': [
            r'config|Config',
            r'public.*api|public.*method',
            r'model|Model',
            r'service|Service',
        ],
        'medium': [
            r'util|helper|Helper',
            r'internal',
            r'private',
        ],
    }
    
    def analyze_file_changes(
        self,
        file_path: Path,
        old_content: Optional[str],
        new_content: str
    ) -> List[CodeChange]:
        """
        Analyze changes in a single file.
        
        Args:
            file_path: Path to the file
            old_content: Previous content (None for new files)
            new_content: Current content
            
        Returns:
            List of detected changes
        """
        changes = []
        
        if old_content is None:
            # New file - analyze all elements
            changes.extend(self._analyze_new_file(file_path, new_content))
        else:
            # Modified file - compare contents
            changes.extend(self._analyze_modified_file(
                file_path, old_content, new_content
            ))
        
        return changes
    
    def _analyze_new_file(self, file_path: Path, content: str) -> List[CodeChange]:
        """Analyze a newly created file."""
        changes = []
        
        # Detect file type and extract elements
        file_type = self._detect_file_type(file_path)
        
        if file_type == 'python':
            changes.extend(self._extract_python_elements(file_path, content, is_new=True))
        elif file_type in ['javascript', 'typescript']:
            changes.extend(self._extract_js_elements(file_path, content, is_new=True))
        elif file_type == 'route':
            changes.extend(self._extract_route_changes(file_path, content, None))
        elif file_type == 'model':
            changes.extend(self._extract_model_changes(file_path, content, None))
        
        return changes
    
    def _analyze_modified_file(
        self,
        file_path: Path,
        old_content: str,
        new_content: str
    ) -> List[CodeChange]:
        """Analyze changes in a modified file."""
        changes = []
        file_type = self._detect_file_type(file_path)
        
        if file_type == 'route':
            changes.extend(self._extract_route_changes(
                file_path, new_content, old_content
            ))
        elif file_type == 'model':
            changes.extend(self._extract_model_changes(
                file_path, new_content, old_content
            ))
        elif file_type in ['python', 'javascript', 'typescript']:
            changes.extend(self._extract_code_changes(
                file_path, new_content, old_content, file_type
            ))
        
        return changes
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect the type of file."""
        path_str = str(file_path).lower()
        suffix = file_path.suffix.lower()
        
        # Check for route files
        if any(x in path_str for x in ['route', 'router', 'endpoint', 'api', 'controller']):
            return 'route'
        
        # Check for model files
        if any(x in path_str for x in ['model', 'schema', 'entity', 'orm']):
            return 'model'
        
        # Check for config files
        if suffix in ['.yaml', '.yml', '.json', '.toml']:
            return 'config'
        
        # Code files
        if suffix == '.py':
            return 'python'
        if suffix in ['.js', '.jsx']:
            return 'javascript'
        if suffix in ['.ts', '.tsx']:
            return 'typescript'
        
        return 'unknown'
    
    def _extract_python_elements(
        self,
        file_path: Path,
        content: str,
        is_new: bool
    ) -> List[CodeChange]:
        """Extract Python code elements."""
        changes = []
        
        # Find class definitions
        class_pattern = r'class\s+(\w+)\s*(?:\([^)]*\))?:'
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            change = CodeChange(
                file_path=str(file_path),
                change_type=ChangeType.NEW_FEATURE if is_new else ChangeType.REFACTOR,
                element_type='class',
                name=name,
                description=f"{'New' if is_new else 'Modified'} class: {name}",
                line_numbers=[line_num],
                impact_level=self._determine_impact(name, content)
            )
            changes.append(change)
        
        # Find function definitions
        func_pattern = r'def\s+(\w+)\s*\([^)]*\)'
        for match in re.finditer(func_pattern, content):
            name = match.group(1)
            if name.startswith('_'):  # Skip private
                continue
            
            line_num = content[:match.start()].count('\n') + 1
            signature = match.group(0)
            
            change = CodeChange(
                file_path=str(file_path),
                change_type=ChangeType.NEW_FEATURE if is_new else ChangeType.REFACTOR,
                element_type='function',
                name=name,
                description=f"{'New' if is_new else 'Modified'} function: {name}",
                new_signature=signature,
                line_numbers=[line_num],
                impact_level=self._determine_impact(name, content)
            )
            changes.append(change)
        
        return changes
    
    def _extract_js_elements(
        self,
        file_path: Path,
        content: str,
        is_new: bool
    ) -> List[CodeChange]:
        """Extract JavaScript/TypeScript code elements."""
        changes = []
        
        # Find class definitions
        class_pattern = r'class\s+(\w+)\s*(?:extends\s+\w+)?\s*\{'
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            change = CodeChange(
                file_path=str(file_path),
                change_type=ChangeType.NEW_FEATURE if is_new else ChangeType.REFACTOR,
                element_type='class',
                name=name,
                description=f"{'New' if is_new else 'Modified'} class: {name}",
                line_numbers=[line_num],
                impact_level=self._determine_impact(name, content)
            )
            changes.append(change)
        
        # Find function definitions
        func_patterns = [
            r'function\s+(\w+)\s*\(',
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(',
            r'(\w+)\s*:\s*(?:async\s*)?\(',
        ]
        
        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                name = match.group(1)
                if name.startswith('_'):
                    continue
                
                line_num = content[:match.start()].count('\n') + 1
                
                change = CodeChange(
                    file_path=str(file_path),
                    change_type=ChangeType.NEW_FEATURE if is_new else ChangeType.REFACTOR,
                    element_type='function',
                    name=name,
                    description=f"{'New' if is_new else 'Modified'} function: {name}",
                    line_numbers=[line_num],
                    impact_level=self._determine_impact(name, content)
                )
                changes.append(change)
        
        return changes
    
    def _extract_route_changes(
        self,
        file_path: Path,
        new_content: str,
        old_content: Optional[str]
    ) -> List[CodeChange]:
        """Extract API route changes."""
        changes = []
        
        # FastAPI/Flask patterns
        route_patterns = [
            r'@app\.(get|post|put|delete|patch)\s*\(["\']([^"\']+)',
            r'@router\.(get|post|put|delete|patch)\s*\(["\']([^"\']+)',
            r'router\.(get|post|put|delete|patch)\s*\(["\']([^"\']+)',
        ]
        
        old_routes = set()
        if old_content:
            for pattern in route_patterns:
                for match in re.finditer(pattern, old_content, re.IGNORECASE):
                    old_routes.add((match.group(1).upper(), match.group(2)))
        
        for pattern in route_patterns:
            for match in re.finditer(pattern, new_content, re.IGNORECASE):
                method = match.group(1).upper()
                path = match.group(2)
                line_num = new_content[:match.start()].count('\n') + 1
                
                if (method, path) not in old_routes:
                    change = CodeChange(
                        file_path=str(file_path),
                        change_type=ChangeType.NEW_FEATURE,
                        element_type='route',
                        name=f"{method} {path}",
                        description=f"New API endpoint: {method} {path}",
                        line_numbers=[line_num],
                        impact_level='high'
                    )
                    changes.append(change)
        
        return changes
    
    def _extract_model_changes(
        self,
        file_path: Path,
        new_content: str,
        old_content: Optional[str]
    ) -> List[CodeChange]:
        """Extract database model changes."""
        changes = []
        
        # Model class patterns
        model_patterns = [
            r'class\s+(\w+)\s*\([^)]*Model\)',
            r'class\s+(\w+)\s*\([^)]*Base\)',
        ]
        
        for pattern in model_patterns:
            for match in re.finditer(pattern, new_content):
                name = match.group(1)
                line_num = new_content[:match.start()].count('\n') + 1
                
                change = CodeChange(
                    file_path=str(file_path),
                    change_type=ChangeType.NEW_FEATURE if old_content is None else ChangeType.REFACTOR,
                    element_type='model',
                    name=name,
                    description=f"{'New' if old_content is None else 'Modified'} model: {name}",
                    line_numbers=[line_num],
                    impact_level='critical' if old_content else 'high'
                )
                changes.append(change)
        
        return changes
    
    def _extract_code_changes(
        self,
        file_path: Path,
        new_content: str,
        old_content: str,
        file_type: str
    ) -> List[CodeChange]:
        """Extract general code changes between versions."""
        changes = []
        
        # Simple line-based diff
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        # Find added lines with significant content
        old_line_set = set(line.strip() for line in old_lines)
        
        for i, line in enumerate(new_lines):
            stripped = line.strip()
            if stripped and stripped not in old_line_set:
                # Check if this is a significant addition
                if self._is_significant_line(stripped, file_type):
                    change_type = self._detect_change_type(stripped)
                    impact = self._determine_impact(stripped, new_content)
                    
                    change = CodeChange(
                        file_path=str(file_path),
                        change_type=change_type,
                        element_type='code',
                        name=f"line_{i+1}",
                        description=f"Modified: {stripped[:50]}...",
                        line_numbers=[i + 1],
                        impact_level=impact
                    )
                    changes.append(change)
        
        return changes
    
    def _is_significant_line(self, line: str, file_type: str) -> bool:
        """Check if a line contains significant code."""
        if not line:
            return False
        
        # Skip comments and whitespace
        if line.startswith('#') or line.startswith('//'):
            return False
        
        # Skip imports
        if line.startswith('import ') or line.startswith('from '):
            return False
        
        # Skip closing braces/parentheses
        if line in ['}', ')', '];', '},']:
            return False
        
        return True
    
    def _detect_change_type(self, content: str) -> ChangeType:
        """Detect the type of change from content."""
        content_lower = content.lower()
        
        for change_type, patterns in self.CHANGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return change_type
        
        return ChangeType.UNKNOWN
    
    def _determine_impact(self, name: str, context: str) -> str:
        """Determine the impact level of a change."""
        combined = f"{name} {context}".lower()
        
        for level, patterns in self.IMPACT_INDICATORS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    return level
        
        return 'low'
    
    def categorize_changes(self, changes: List[CodeChange]) -> Dict[str, List[CodeChange]]:
        """Categorize changes by type."""
        categorized = {
            'new_features': [],
            'bugfixes': [],
            'refactors': [],
            'deprecations': [],
            'removals': [],
            'other': [],
        }
        
        for change in changes:
            if change.change_type == ChangeType.NEW_FEATURE:
                categorized['new_features'].append(change)
            elif change.change_type == ChangeType.BUGFIX:
                categorized['bugfixes'].append(change)
            elif change.change_type == ChangeType.REFACTOR:
                categorized['refactors'].append(change)
            elif change.change_type == ChangeType.DEPRECATED:
                categorized['deprecations'].append(change)
            elif change.change_type == ChangeType.REMOVED:
                categorized['removals'].append(change)
            else:
                categorized['other'].append(change)
        
        return categorized
    
    def get_summary(self, changes: List[CodeChange]) -> Dict[str, Any]:
        """Generate a summary of changes."""
        if not changes:
            return {
                'total_changes': 0,
                'summary_text': "No significant changes detected."
            }
        
        categorized = self.categorize_changes(changes)
        
        # Count by impact
        impact_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for change in changes:
            impact_counts[change.impact_level] += 1
        
        # Count by element type
        element_types = {}
        for change in changes:
            element_types[change.element_type] = element_types.get(change.element_type, 0) + 1
        
        return {
            'total_changes': len(changes),
            'by_category': {
                k: len(v) for k, v in categorized.items() if v
            },
            'by_impact': impact_counts,
            'by_element_type': element_types,
            'critical_changes': [
                c.to_dict() for c in changes 
                if c.impact_level == 'critical'
            ],
            'high_impact_changes': [
                c.to_dict() for c in changes 
                if c.impact_level == 'high'
            ],
        }
