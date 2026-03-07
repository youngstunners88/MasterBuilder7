"""Database query analyzer for detecting N+1 queries and optimization opportunities."""

import re
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import sqlparse
from sqlparse.sql import Statement, Token
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

console = Console()


class QueryIssueType(Enum):
    N_PLUS_ONE = "n_plus_one"
    MISSING_INDEX = "missing_index"
    FULL_TABLE_SCAN = "full_table_scan"
    SELECT_STAR = "select_star"
    UNBOUNDED_QUERY = "unbounded_query"
    INEFFICIENT_JOIN = "inefficient_join"
    NESTED_SUBQUERY = "nested_subquery"
    MISSING_WHERE = "missing_where"
    OR_IN_CONDITION = "or_in_condition"
    IMPLICIT_CONVERSION = "implicit_conversion"


@dataclass
class QueryIssue:
    """Issue found in a database query."""
    issue_type: QueryIssueType
    description: str
    severity: str  # critical, high, medium, low
    query: str
    line_number: int
    file_path: str
    suggestion: str
    estimated_impact: str


@dataclass
class QueryPattern:
    """Pattern detected in queries."""
    name: str
    count: int
    total_time: float
    example: str


class QueryAnalyzer:
    """Analyzes database queries for performance issues."""
    
    # Patterns that indicate N+1 queries
    N_PLUS_ONE_PATTERNS = [
        r'for\s+\w+\s+in\s+\w+.*:\s*\n\s*\w+\.(filter|get|all)\s*\(',
        r'\.forEach\s*\(\s*.*\)\s*\{[^}]*\.(find|findOne|query)',
        r'await\s+Promise\.all\s*\(\s*\w+\.map\s*\(',
    ]
    
    # SQL anti-patterns
    SQL_ANTI_PATTERNS = {
        'select_star': r'SELECT\s+\*\s+FROM',
        'missing_where': r'SELECT.*FROM[^;]*$(?!.*WHERE)',
        'or_in_condition': r'WHERE.*\bOR\b.*IN\s*\(',
        'not_in': r'NOT\s+IN\s*\(',
        'implicit_conversion': r'WHERE\s+\w+\s*=\s*[\'"\d]+\s*AND\s+\w+\s*=',
    }
    
    def __init__(self):
        self.issues: List[QueryIssue] = []
        self.query_patterns: Dict[str, QueryPattern] = {}
        self.queries_analyzed = 0
    
    def analyze_code(self, file_path: str, 
                     patterns: Optional[List[str]] = None) -> List[QueryIssue]:
        """Analyze code file for query issues."""
        path = Path(file_path)
        if not path.exists():
            return []
        
        content = path.read_text(encoding='utf-8', errors='ignore')
        issues = []
        
        # Detect N+1 patterns
        issues.extend(self._detect_n_plus_one(content, str(path)))
        
        # Detect raw SQL issues
        issues.extend(self._detect_sql_issues(content, str(path)))
        
        # Detect ORM anti-patterns
        issues.extend(self._detect_orm_issues(content, str(path)))
        
        self.issues.extend(issues)
        return issues
    
    def analyze_directory(self, directory: str, 
                         pattern: str = "**/*.py") -> List[QueryIssue]:
        """Analyze all files in a directory."""
        directory = Path(directory)
        all_issues = []
        
        for file_path in directory.glob(pattern):
            if 'node_modules' in str(file_path) or '__pycache__' in str(file_path):
                continue
            
            issues = self.analyze_code(str(file_path))
            all_issues.extend(issues)
        
        return all_issues
    
    def analyze_sql(self, query: str, file_path: str = "unknown", 
                   line_number: int = 0) -> List[QueryIssue]:
        """Analyze a single SQL query."""
        issues = []
        self.queries_analyzed += 1
        
        # Parse SQL
        try:
            parsed = sqlparse.parse(query)[0]
        except Exception:
            parsed = None
        
        # Check for SELECT *
        if re.search(self.SQL_ANTI_PATTERNS['select_star'], query, re.IGNORECASE):
            if not self._is_count_query(query):
                issues.append(QueryIssue(
                    issue_type=QueryIssueType.SELECT_STAR,
                    description="SELECT * retrieves all columns, increasing I/O and memory usage",
                    severity="medium",
                    query=query[:200],
                    line_number=line_number,
                    file_path=file_path,
                    suggestion="Specify only needed columns instead of *",
                    estimated_impact="20-50% reduction in query time for wide tables"
                ))
        
        # Check for missing WHERE
        if re.search(r'^\s*SELECT', query, re.IGNORECASE):
            if not re.search(r'\bWHERE\b', query, re.IGNORECASE):
                if not re.search(r'\bLIMIT\s+1\b', query, re.IGNORECASE):
                    issues.append(QueryIssue(
                        issue_type=QueryIssueType.MISSING_WHERE,
                        description="Query without WHERE clause may return entire table",
                        severity="high",
                        query=query[:200],
                        line_number=line_number,
                        file_path=file_path,
                        suggestion="Add appropriate WHERE conditions or use LIMIT",
                        estimated_impact="Prevents memory exhaustion on large tables"
                    ))
        
        # Check for unbounded queries
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            if re.search(r'\bORDER\s+BY\b', query, re.IGNORECASE):
                issues.append(QueryIssue(
                    issue_type=QueryIssueType.UNBOUNDED_QUERY,
                    description="Unbounded ORDER BY query can cause memory issues",
                    severity="medium",
                    query=query[:200],
                    line_number=line_number,
                    file_path=file_path,
                    suggestion="Add LIMIT clause to bound result set",
                    estimated_impact="Prevents memory issues with large sorts"
                ))
        
        # Check for inefficient OR with IN
        if re.search(self.SQL_ANTI_PATTERNS['or_in_condition'], query, re.IGNORECASE):
            issues.append(QueryIssue(
                issue_type=QueryIssueType.OR_IN_CONDITION,
                description="OR with IN can prevent index usage",
                severity="medium",
                query=query[:200],
                line_number=line_number,
                file_path=file_path,
                suggestion="Consider UNION or restructuring the query",
                estimated_impact="Potential index usage improvement"
            ))
        
        # Check for NOT IN
        if re.search(self.SQL_ANTI_PATTERNS['not_in'], query, re.IGNORECASE):
            issues.append(QueryIssue(
                issue_type=QueryIssueType.INEFFICIENT_JOIN,
                description="NOT IN can be slow with NULL values",
                severity="low",
                query=query[:200],
                line_number=line_number,
                file_path=file_path,
                suggestion="Use NOT EXISTS instead",
                estimated_impact="Better performance with NULL handling"
            ))
        
        # Check join complexity
        join_count = len(re.findall(r'\bJOIN\b', query, re.IGNORECASE))
        if join_count > 4:
            issues.append(QueryIssue(
                issue_type=QueryIssueType.INEFFICIENT_JOIN,
                description=f"Query has {join_count} joins, which may impact performance",
                severity="low",
                query=query[:200],
                line_number=line_number,
                file_path=file_path,
                suggestion="Consider denormalizing or breaking into multiple queries",
                estimated_impact="Reduce join overhead"
            ))
        
        # Nested subqueries
        subquery_count = len(re.findall(r'\(\s*SELECT\b', query, re.IGNORECASE))
        if subquery_count > 1:
            issues.append(QueryIssue(
                issue_type=QueryIssueType.NESTED_SUBQUERY,
                description=f"Query has {subquery_count} nested subqueries",
                severity="medium",
                query=query[:200],
                line_number=line_number,
                file_path=file_path,
                suggestion="Consider using JOINs or CTEs instead",
                estimated_impact="Often 2-10x faster with proper rewrites"
            ))
        
        return issues
    
    def _detect_n_plus_one(self, content: str, file_path: str) -> List[QueryIssue]:
        """Detect N+1 query patterns in code."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.N_PLUS_ONE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(QueryIssue(
                        issue_type=QueryIssueType.N_PLUS_ONE,
                        description="Potential N+1 query pattern detected",
                        severity="critical",
                        query=line.strip()[:200],
                        line_number=i,
                        file_path=file_path,
                        suggestion="Use select_related(), prefetch_related() or batch loading",
                        estimated_impact="Can reduce queries from N+1 to 2"
                    ))
        
        # Check for specific ORM patterns
        if '.objects.filter(' in content or '.query().' in content:
            # Look for loop + query pattern
            issues.extend(self._detect_loop_query_pattern(content, file_path))
        
        return issues
    
    def _detect_loop_query_pattern(self, content: str, file_path: str) -> List[QueryIssue]:
        """Detect queries inside loops."""
        issues = []
        lines = content.split('\n')
        
        in_loop = False
        loop_start = 0
        indent_level = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)
            
            # Detect loop start
            if re.match(r'^(for|while)\s+', stripped):
                in_loop = True
                loop_start = i
                indent_level = current_indent
                continue
            
            # Check for query inside loop
            if in_loop and current_indent > indent_level:
                if any(pattern in stripped for pattern in 
                       ['.filter(', '.get(', '.all()', '.first()', 'execute(', 'query(']):
                    issues.append(QueryIssue(
                        issue_type=QueryIssueType.N_PLUS_ONE,
                        description="Database query detected inside loop",
                        severity="critical",
                        query=stripped[:200],
                        line_number=i,
                        file_path=file_path,
                        suggestion="Move query outside loop or use batch operations",
                        estimated_impact="Can reduce queries from O(n) to O(1)"
                    ))
            
            # Exit loop on dedent
            if in_loop and current_indent <= indent_level and stripped:
                if not stripped.startswith('#'):
                    in_loop = False
        
        return issues
    
    def _detect_sql_issues(self, content: str, file_path: str) -> List[QueryIssue]:
        """Detect issues in raw SQL strings."""
        issues = []
        
        # Find SQL strings (simplified)
        sql_patterns = [
            r'["\'](SELECT\s+.*?)["\']',
            r'["\'](INSERT\s+.*?)["\']',
            r'["\'](UPDATE\s+.*?)["\']',
            r'["\'](DELETE\s+.*?)["\']',
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern in sql_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    sql = match.group(1)
                    issues.extend(self.analyze_sql(sql, file_path, i))
        
        return issues
    
    def _detect_orm_issues(self, content: str, file_path: str) -> List[QueryIssue]:
        """Detect ORM-specific anti-patterns."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Django: Count without values
            if re.search(r'\.count\s*\(\s*\)', line):
                if '.values(' in line or '.values_list(' in line:
                    pass  # OK, using values
                else:
                    issues.append(QueryIssue(
                        issue_type=QueryIssueType.FULL_TABLE_SCAN,
                        description="Count without values() may load full objects",
                        severity="low",
                        query=line.strip()[:200],
                        line_number=i,
                        file_path=file_path,
                        suggestion="Use .values('id').count() for better performance",
                        estimated_impact="Reduces memory usage for counts"
                    ))
            
            # Django: Multiple filters without Q objects
            if re.search(r'\.filter\([^)]+\)\.filter\(', line):
                issues.append(QueryIssue(
                    issue_type=QueryIssueType.INEFFICIENT_JOIN,
                    description="Chained filters may create inefficient queries",
                    severity="low",
                    query=line.strip()[:200],
                    line_number=i,
                    file_path=file_path,
                    suggestion="Combine filters into single .filter() call",
                    estimated_impact="Simpler query generation"
                ))
        
        return issues
    
    def _is_count_query(self, query: str) -> bool:
        """Check if query is a COUNT query."""
        return bool(re.search(r'SELECT\s+COUNT\s*\(', query, re.IGNORECASE))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of detected issues."""
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        
        for issue in self.issues:
            type_name = issue.issue_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            severity = issue.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            'total_issues': len(self.issues),
            'queries_analyzed': self.queries_analyzed,
            'by_type': by_type,
            'by_severity': by_severity,
            'critical_issues': by_severity.get('critical', 0),
            'high_issues': by_severity.get('high', 0)
        }
    
    def display_issues(self, severity_filter: Optional[str] = None):
        """Display detected issues in console."""
        issues = self.issues
        if severity_filter:
            issues = [i for i in issues if i.severity == severity_filter]
        
        if not issues:
            console.print("[green]No query issues found![/green]")
            return
        
        # Summary
        summary = self.get_summary()
        console.print(f"\n[bold]Query Analysis Summary:[/bold]")
        console.print(f"  Total Issues: {summary['total_issues']}")
        console.print(f"  Critical: {summary['critical_issues']}")
        console.print(f"  High: {summary['high_issues']}")
        
        # Table of issues
        table = Table(title="Query Performance Issues")
        table.add_column("Type", style="cyan")
        table.add_column("Severity", style="red")
        table.add_column("Location", style="dim")
        table.add_column("Description", style="yellow")
        
        severity_colors = {
            'critical': 'red',
            'high': 'orange3',
            'medium': 'yellow',
            'low': 'green'
        }
        
        for issue in sorted(issues, 
                          key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.severity, 4)):
            color = severity_colors.get(issue.severity, 'white')
            table.add_row(
                issue.issue_type.value,
                f"[{color}]{issue.severity}[/{color}]",
                f"{Path(issue.file_path).name}:{issue.line_number}",
                issue.description[:60] + "..." if len(issue.description) > 60 else issue.description
            )
        
        console.print(table)
    
    def generate_index_recommendations(self) -> List[Dict[str, str]]:
        """Generate index recommendations based on detected queries."""
        recommendations = []
        
        # Analyze detected queries for index opportunities
        for issue in self.issues:
            if issue.issue_type == QueryIssueType.MISSING_WHERE:
                # Extract table name if possible
                match = re.search(r'FROM\s+(\w+)', issue.query, re.IGNORECASE)
                if match:
                    table = match.group(1)
                    recommendations.append({
                        'table': table,
                        'columns': 'unknown',  # Would need more analysis
                        'reason': 'WHERE clause filtering',
                        'priority': 'high'
                    })
        
        return recommendations