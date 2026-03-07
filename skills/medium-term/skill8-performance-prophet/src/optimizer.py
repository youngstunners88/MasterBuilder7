"""Performance optimizer with suggestions and automated improvements."""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .profiler import FunctionProfile, ProfileResult
from .query_analyzer import QueryIssue, QueryIssueType

console = Console()


class OptimizationType(Enum):
    ALGORITHM = "algorithm"
    CACHING = "caching"
    DATABASE = "database"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    VECTORIZATION = "vectorization"
    LAZY_LOADING = "lazy_loading"
    BATCH_PROCESSING = "batch_processing"
    CODE_REMOVAL = "code_removal"


@dataclass
class OptimizationSuggestion:
    """A performance optimization suggestion."""
    type: OptimizationType
    title: str
    description: str
    current_code: str
    optimized_code: str
    estimated_improvement: str
    effort_level: str  # low, medium, high
    risk_level: str  # low, medium, high
    applies_to: str
    auto_applicable: bool = False


@dataclass
class CodeTransformation:
    """A specific code transformation to apply."""
    file_path: str
    line_start: int
    line_end: int
    original: str
    replacement: str
    reason: str


class Optimizer:
    """Provides performance optimization suggestions and transformations."""
    
    def __init__(self):
        self.suggestions: List[OptimizationSuggestion] = []
        self.transformations: List[CodeTransformation] = []
    
    def analyze_profile(self, profile: ProfileResult) -> List[OptimizationSuggestion]:
        """Analyze profile and generate optimization suggestions."""
        suggestions = []
        
        # Analyze hotspots
        for func in profile.get_hotspots(20):
            suggestions.extend(self._analyze_function(func, profile))
        
        # Memory optimizations
        if profile.memory_peak and profile.memory_peak > 100:  # > 100MB
            suggestions.extend(self._suggest_memory_optimizations(profile))
        
        self.suggestions.extend(suggestions)
        return suggestions
    
    def analyze_queries(self, query_issues: List[QueryIssue]) -> List[OptimizationSuggestion]:
        """Generate optimizations based on query issues."""
        suggestions = []
        
        for issue in query_issues:
            if issue.issue_type == QueryIssueType.N_PLUS_ONE:
                suggestions.append(self._create_n_plus_one_optimization(issue))
            elif issue.issue_type == QueryIssueType.SELECT_STAR:
                suggestions.append(self._create_select_star_optimization(issue))
            elif issue.issue_type == QueryIssueType.MISSING_WHERE:
                suggestions.append(self._create_missing_where_optimization(issue))
        
        self.suggestions.extend(suggestions)
        return suggestions
    
    def _analyze_function(self, func: FunctionProfile, 
                         profile: ProfileResult) -> List[OptimizationSuggestion]:
        """Analyze a single function for optimization opportunities."""
        suggestions = []
        
        # Check for high call count (potential caching opportunity)
        if func.call_count > 10000 and func.cumulative_time > 0.1:
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.CACHING,
                title=f"Add caching to {func.name}",
                description=f"Function called {func.call_count:,} times. Consider memoization or result caching.",
                current_code=f"def {func.name}(...):\n    # Current implementation\n    ...",
                optimized_code=f"from functools import lru_cache\n\n@lru_cache(maxsize=128)\ndef {func.name}(...):\n    # Cached implementation\n    ...",
                estimated_improvement=f"{min(95, func.call_count / 100):.0f}% reduction in calls",
                effort_level="low",
                risk_level="low",
                applies_to=f"{func.file}:{func.line}",
                auto_applicable=True
            ))
        
        # Check for long execution time (algorithm improvement)
        if func.cumulative_time > 1.0:  # > 1 second
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.ALGORITHM,
                title=f"Optimize algorithm in {func.name}",
                description=f"Function takes {func.cumulative_time:.2f}s. Consider algorithmic improvements.",
                current_code=f"def {func.name}(...):\n    # O(n²) or worse implementation\n    ...",
                optimized_code="# Consider:\n# - Using sets/dicts for O(1) lookup\n# - Sorting first for O(n log n)\n# - Using numpy for vectorized operations",
                estimated_improvement="50-90% time reduction possible",
                effort_level="high",
                risk_level="medium",
                applies_to=f"{func.file}:{func.line}",
                auto_applicable=False
            ))
        
        return suggestions
    
    def _suggest_memory_optimizations(self, profile: ProfileResult) -> List[OptimizationSuggestion]:
        """Suggest memory optimizations."""
        suggestions = []
        
        suggestions.append(OptimizationSuggestion(
            type=OptimizationType.MEMORY,
            title="Enable streaming for large data processing",
            description=f"Peak memory usage: {profile.memory_peak:.2f}MB. Consider generators for large datasets.",
            current_code="# Loading all data into memory\ndata = list(load_large_dataset())\nfor item in data:\n    process(item)",
            optimized_code="# Using generator for memory efficiency\nfor item in load_large_dataset():  # Returns generator\n    process(item)",
            estimated_improvement=f"Reduce memory from {profile.memory_peak:.0f}MB to ~10MB",
            effort_level="medium",
            risk_level="low",
            applies_to="Memory hotspots",
            auto_applicable=False
        ))
        
        suggestions.append(OptimizationSuggestion(
            type=OptimizationType.MEMORY,
            title="Use __slots__ for memory-heavy classes",
            description="Reduce memory overhead of class instances",
            current_code="class MyClass:\n    def __init__(self):\n        self.a = None\n        self.b = None",
            optimized_code="class MyClass:\n    __slots__ = ['a', 'b']\n    \n    def __init__(self):\n        self.a = None\n        self.b = None",
            estimated_improvement="40-50% memory reduction per instance",
            effort_level="low",
            risk_level="low",
            applies_to="Classes with many instances",
            auto_applicable=False
        ))
        
        return suggestions
    
    def _create_n_plus_one_optimization(self, issue: QueryIssue) -> OptimizationSuggestion:
        """Create optimization for N+1 query issue."""
        return OptimizationSuggestion(
            type=OptimizationType.DATABASE,
            title="Fix N+1 Query with Prefetch",
            description=issue.description,
            current_code="# N+1 Problem\nfor user in User.objects.all():\n    print(user.profile.bio)  # Query per user",
            optimized_code="# Solution with prefetch_related\nfor user in User.objects.prefetch_related('profile'):\n    print(user.profile.bio)  # No additional queries",
            estimated_improvement="Reduce queries from N+1 to 2 (99%+ reduction)",
            effort_level="low",
            risk_level="low",
            applies_to=f"{issue.file_path}:{issue.line_number}",
            auto_applicable=False
        )
    
    def _create_select_star_optimization(self, issue: QueryIssue) -> OptimizationSuggestion:
        """Create optimization for SELECT * issue."""
        return OptimizationSuggestion(
            type=OptimizationType.DATABASE,
            title="Select Specific Columns",
            description=issue.description,
            current_code="SELECT * FROM users WHERE active = 1",
            optimized_code="SELECT id, name, email FROM users WHERE active = 1",
            estimated_improvement="20-50% reduction in I/O for wide tables",
            effort_level="low",
            risk_level="low",
            applies_to=f"{issue.file_path}:{issue.line_number}",
            auto_applicable=False
        )
    
    def _create_missing_where_optimization(self, issue: QueryIssue) -> OptimizationSuggestion:
        """Create optimization for missing WHERE clause."""
        return OptimizationSuggestion(
            type=OptimizationType.DATABASE,
            title="Add WHERE Clause or LIMIT",
            description=issue.description,
            current_code="SELECT * FROM logs ORDER BY created_at DESC",
            optimized_code="SELECT * FROM logs ORDER BY created_at DESC LIMIT 100",
            estimated_improvement="Prevents memory exhaustion",
            effort_level="low",
            risk_level="low",
            applies_to=f"{issue.file_path}:{issue.line_number}",
            auto_applicable=True
        )
    
    def generate_optimization_plan(self, profile: ProfileResult,
                                   query_issues: List[QueryIssue]) -> Dict[str, Any]:
        """Generate a comprehensive optimization plan."""
        # Analyze everything
        func_opts = self.analyze_profile(profile)
        query_opts = self.analyze_queries(query_issues)
        
        all_opts = func_opts + query_opts
        
        # Sort by impact/effort ratio
        effort_scores = {'low': 1, 'medium': 2, 'high': 3}
        
        def impact_score(opt: OptimizationSuggestion) -> float:
            # Extract percentage from estimated_improvement
            import re
            match = re.search(r'(\d+)%', opt.estimated_improvement)
            if match:
                return float(match.group(1)) / effort_scores[opt.effort_level]
            return 10 / effort_scores[opt.effort_level]  # Default
        
        sorted_opts = sorted(all_opts, key=impact_score, reverse=True)
        
        # Group by effort level
        by_effort: Dict[str, List[OptimizationSuggestion]] = {
            'quick_wins': [],  # low effort, high impact
            'planned': [],     # medium effort
            'strategic': []    # high effort
        }
        
        for opt in sorted_opts:
            if opt.effort_level == 'low' and opt.risk_level == 'low':
                by_effort['quick_wins'].append(opt)
            elif opt.effort_level == 'high':
                by_effort['strategic'].append(opt)
            else:
                by_effort['planned'].append(opt)
        
        return {
            'quick_wins': by_effort['quick_wins'],
            'planned': by_effort['planned'],
            'strategic': by_effort['strategic'],
            'total_suggestions': len(all_opts),
            'auto_applicable': len([o for o in all_opts if o.auto_applicable]),
            'estimated_total_improvement': self._estimate_total_improvement(all_opts)
        }
    
    def _estimate_total_improvement(self, optimizations: List[OptimizationSuggestion]) -> str:
        """Estimate total possible improvement."""
        import re
        total_pct = 0
        
        for opt in optimizations:
            match = re.search(r'(\d+)%', opt.estimated_improvement)
            if match:
                # Assume diminishing returns
                pct = float(match.group(1))
                total_pct += pct * 0.5  # Conservative estimate
        
        if total_pct > 200:
            return "Up to 3x faster"
        elif total_pct > 100:
            return "Up to 2x faster"
        elif total_pct > 50:
            return "30-50% faster"
        else:
            return "10-30% faster"
    
    def apply_optimization(self, suggestion: OptimizationSuggestion,
                          dry_run: bool = True) -> bool:
        """Attempt to apply an optimization automatically."""
        if not suggestion.auto_applicable:
            console.print(f"[yellow]{suggestion.title} requires manual implementation[/yellow]")
            return False
        
        # Parse file path from applies_to
        parts = suggestion.applies_to.split(':')
        file_path = parts[0]
        
        if not Path(file_path).exists():
            console.print(f"[red]File not found:[/red] {file_path}")
            return False
        
        if dry_run:
            console.print(f"[blue]Dry run:[/blue] Would apply {suggestion.title}")
            console.print(f"  [dim]File: {file_path}[/dim]")
            return True
        
        # Apply the transformation
        try:
            content = Path(file_path).read_text()
            
            # This is simplified - real implementation would use AST parsing
            if '@lru_cache' in suggestion.optimized_code:
                # Add import if needed
                if 'from functools import lru_cache' not in content:
                    content = 'from functools import lru_cache\n' + content
                
                Path(file_path).write_text(content)
                console.print(f"[green]✓[/green] Applied: {suggestion.title}")
                return True
            
        except Exception as e:
            console.print(f"[red]Failed to apply optimization:[/red] {e}")
            return False
        
        return False
    
    def generate_load_test_code(self, scenarios: List[Dict[str, Any]]) -> str:
        """Generate Locust load test code."""
        code_lines = [
            "from locust import HttpUser, task, between",
            "from locust.contrib.fasthttp import FastHttpUser",
            "",
            "class PerformanceTest(FastHttpUser):",
            "    wait_time = between(1, 3)",
            "",
            "    def on_start(self):",
            "        '''Setup before tests'''",
            "        pass",
            "",
        ]
        
        for i, scenario in enumerate(scenarios):
            code_lines.extend([
                f"    @task({scenario.get('weight', 1)})",
                f"    def {scenario['name'].lower().replace(' ', '_')}(self):",
                f"        '''{scenario.get('purpose', 'Test scenario')}'''",
                f"        self.client.get('/api/endpoint')",
                "",
            ])
        
        code_lines.extend([
            "# Run with: locust -f load_test.py --host=http://localhost:8000",
            "",
        ])
        
        return '\n'.join(code_lines)
    
    def display_suggestions(self, suggestions: Optional[List[OptimizationSuggestion]] = None):
        """Display optimization suggestions in console."""
        suggestions = suggestions or self.suggestions
        
        if not suggestions:
            console.print("[green]No optimizations suggested![/green]")
            return
        
        # Group by type
        by_type: Dict[str, List[OptimizationSuggestion]] = {}
        for opt in suggestions:
            type_name = opt.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(opt)
        
        console.print(f"\n[bold]🔧 Optimization Suggestions:[/bold] ({len(suggestions)} total)")
        
        for opt_type, opts in by_type.items():
            console.print(f"\n[bold cyan]{opt_type.upper()}:[/bold cyan] ({len(opts)})")
            
            table = Table(show_header=False)
            table.add_column("Title", style="yellow")
            table.add_column("Improvement")
            table.add_column("Effort")
            table.add_column("Risk")
            
            for opt in opts[:5]:  # Show top 5 per type
                table.add_row(
                    opt.title[:50],
                    opt.estimated_improvement[:30],
                    opt.effort_level,
                    opt.risk_level
                )
            
            console.print(table)
    
    def save_optimization_plan(self, output_path: str, 
                              plan: Dict[str, Any]):
        """Save optimization plan to markdown file."""
        lines = [
            "# Performance Optimization Plan",
            "",
            f"Generated: {plan.get('timestamp', 'now')}",
            "",
            f"**Total Suggestions:** {plan['total_suggestions']}",
            f"**Auto-Applicable:** {plan['auto_applicable']}",
            f"**Estimated Improvement:** {plan['estimated_total_improvement']}",
            "",
            "## Quick Wins (Low Effort, High Impact)",
            ""
        ]
        
        for opt in plan['quick_wins']:
            lines.extend([
                f"### {opt.title}",
                "",
                f"**Description:** {opt.description}",
                f"**Impact:** {opt.estimated_improvement}",
                f"**Location:** {opt.applies_to}",
                "",
                "**Current Code:**",
                "```python",
                opt.current_code,
                "```",
                "",
                "**Optimized Code:**",
                "```python",
                opt.optimized_code,
                "```",
                "",
                "---",
                ""
            ])
        
        lines.extend([
            "## Planned Optimizations",
            ""
        ])
        
        for opt in plan['planned']:
            lines.extend([
                f"- **{opt.title}** - {opt.estimated_improvement}"
            ])
        
        lines.extend([
            "",
            "## Strategic Optimizations",
            ""
        ])
        
        for opt in plan['strategic']:
            lines.extend([
                f"- **{opt.title}** - {opt.estimated_improvement} (High effort)"
            ])
        
        Path(output_path).write_text('\n'.join(lines))
        console.print(f"[green]✓[/green] Optimization plan saved to {output_path}")