"""Code profiler using cProfile, line_profiler, and memory_profiler."""

import cProfile
import pstats
import io
import time
import tracemalloc
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from functools import wraps
import tempfile
import json

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

console = Console()


@dataclass
class FunctionProfile:
    """Profile data for a single function."""
    name: str
    file: str
    line: int
    call_count: int
    total_time: float
    cumulative_time: float
    per_call: float
    memory_usage: Optional[float] = None
    
    @property
    def is_hotspot(self) -> bool:
        """Check if this is a performance hotspot."""
        return self.cumulative_time > 0.1 or self.call_count > 1000


@dataclass
class ProfileResult:
    """Complete profiling results."""
    functions: List[FunctionProfile]
    total_time: float
    timestamp: str
    target: str
    memory_peak: Optional[float] = None
    memory_current: Optional[float] = None
    
    def get_hotspots(self, limit: int = 10) -> List[FunctionProfile]:
        """Get top performance hotspots."""
        return sorted(
            self.functions,
            key=lambda x: x.cumulative_time,
            reverse=True
        )[:limit]
    
    def get_by_file(self, file_pattern: str) -> List[FunctionProfile]:
        """Get functions matching file pattern."""
        return [f for f in self.functions if file_pattern in f.file]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'target': self.target,
            'total_time': self.total_time,
            'timestamp': self.timestamp,
            'memory_peak': self.memory_peak,
            'memory_current': self.memory_current,
            'functions': [
                {
                    'name': f.name,
                    'file': f.file,
                    'line': f.line,
                    'call_count': f.call_count,
                    'total_time': f.total_time,
                    'cumulative_time': f.cumulative_time,
                    'per_call': f.per_call,
                    'memory_usage': f.memory_usage
                }
                for f in self.functions
            ],
            'hotspots': [
                {
                    'name': f.name,
                    'file': f.file,
                    'cumulative_time': f.cumulative_time,
                    'call_count': f.call_count
                }
                for f in self.get_hotspots()
            ]
        }


class Profiler:
    """Performance profiler for Python code."""
    
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.results: List[ProfileResult] = []
        self._memory_tracing = False
    
    def profile_function(self, func: Callable, *args, 
                         memory: bool = False, **kwargs) -> tuple[ProfileResult, Any]:
        """Profile a single function execution."""
        self.profiler.enable()
        
        if memory:
            tracemalloc.start()
            self._memory_tracing = True
        
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        self.profiler.disable()
        
        # Get memory stats
        memory_peak = None
        memory_current = None
        if memory:
            current, peak = tracemalloc.get_traced_memory()
            memory_current = current / 1024 / 1024  # MB
            memory_peak = peak / 1024 / 1024  # MB
            tracemalloc.stop()
            self._memory_tracing = False
        
        # Parse stats
        profile_result = self._parse_stats(
            elapsed, 
            func.__name__,
            memory_peak=memory_peak,
            memory_current=memory_current
        )
        
        self.results.append(profile_result)
        return profile_result, result
    
    def profile_with_decorator(self, memory: bool = False):
        """Decorator for profiling functions."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                profile_result, result = self.profile_function(
                    func, *args, memory=memory, **kwargs
                )
                return result
            return wrapper
        return decorator
    
    def profile_module(self, module_name: str, 
                       run_func: Optional[str] = None) -> ProfileResult:
        """Profile an entire module."""
        import importlib
        
        module = importlib.import_module(module_name)
        
        self.profiler.enable()
        start_time = time.time()
        
        if run_func and hasattr(module, run_func):
            getattr(module, run_func)()
        
        elapsed = time.time() - start_time
        self.profiler.disable()
        
        profile_result = self._parse_stats(elapsed, module_name)
        self.results.append(profile_result)
        return profile_result
    
    def profile_script(self, script_path: str) -> ProfileResult:
        """Profile a Python script execution."""
        import runpy
        
        self.profiler.enable()
        start_time = time.time()
        
        runpy.run_path(script_path, run_name="__main__")
        
        elapsed = time.time() - start_time
        self.profiler.disable()
        
        profile_result = self._parse_stats(elapsed, script_path)
        self.results.append(profile_result)
        return profile_result
    
    def _parse_stats(self, elapsed: float, target: str,
                    memory_peak: Optional[float] = None,
                    memory_current: Optional[float] = None) -> ProfileResult:
        """Parse profiler statistics."""
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        
        functions = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            file, line, name = func
            functions.append(FunctionProfile(
                name=name,
                file=file,
                line=line,
                call_count=cc,
                total_time=tt,
                cumulative_time=ct,
                per_call=ct / cc if cc > 0 else 0
            ))
        
        return ProfileResult(
            functions=functions,
            total_time=elapsed,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            target=target,
            memory_peak=memory_peak,
            memory_current=memory_current
        )
    
    def start_continuous(self, interval: float = 1.0):
        """Start continuous profiling (use with care in production)."""
        self.profiler.enable()
        console.print(f"[blue]Continuous profiling started (interval: {interval}s)[/blue]")
    
    def stop_continuous(self) -> ProfileResult:
        """Stop continuous profiling and get results."""
        self.profiler.disable()
        result = self._parse_stats(0, "continuous")
        self.results.append(result)
        return result
    
    def export_to_pstats(self, output_path: str):
        """Export profiling data in pstats format."""
        stats = pstats.Stats(self.profiler)
        stats.dump_stats(output_path)
        console.print(f"[green]✓[/green] Profile data saved to {output_path}")
    
    def generate_flamegraph(self, output_path: str):
        """Generate flamegraph visualization."""
        # Export to format compatible with flamegraph tools
        self.export_to_pstats(output_path.replace('.svg', '.prof'))
        
        # Try to use py-spy for flamegraph
        try:
            import subprocess
            subprocess.run([
                'py-spy', 'record',
                '-f', 'flamegraph',
                '-o', output_path,
                '--', 'python', '-c', f"exec(open('{self.results[-1].target}').read())"
            ], check=True)
            console.print(f"[green]✓[/green] Flamegraph saved to {output_path}")
        except Exception as e:
            console.print(f"[yellow]Could not generate flamegraph:[/yellow] {e}")
    
    def display_results(self, result: Optional[ProfileResult] = None):
        """Display profiling results in console."""
        result = result or (self.results[-1] if self.results else None)
        
        if not result:
            console.print("[yellow]No profiling results available[/yellow]")
            return
        
        # Summary panel
        summary = (
            f"Target: {result.target}\n"
            f"Total Time: {result.total_time:.4f}s\n"
            f"Functions Profiled: {len(result.functions)}"
        )
        
        if result.memory_peak:
            summary += f"\nPeak Memory: {result.memory_peak:.2f} MB"
        
        console.print(Panel(summary, title="📊 Profile Summary", border_style="cyan"))
        
        # Hotspots table
        hotspots = result.get_hotspots(15)
        
        table = Table(title="🔥 Top Performance Hotspots")
        table.add_column("Function", style="cyan", no_wrap=True)
        table.add_column("File", style="dim", max_width=40)
        table.add_column("Calls", justify="right")
        table.add_column("Total Time (s)", justify="right")
        table.add_column("Cumulative (s)", justify="right")
        table.add_column("Per Call (ms)", justify="right")
        
        for func in hotspots:
            table.add_row(
                func.name[:50],
                f"{Path(func.file).name}:{func.line}",
                f"{func.call_count:,}",
                f"{func.total_time:.4f}",
                f"{func.cumulative_time:.4f}",
                f"{func.per_call * 1000:.3f}"
            )
        
        console.print(table)
        
        # Memory info if available
        if result.memory_peak:
            console.print(f"\n[bold]Memory Usage:[/bold]")
            console.print(f"  Current: {result.memory_current:.2f} MB")
            console.print(f"  Peak: {result.memory_peak:.2f} MB")
    
    def compare_profiles(self, profile1: ProfileResult, 
                        profile2: ProfileResult) -> Dict[str, Any]:
        """Compare two profiles and show differences."""
        # Build function lookup
        funcs1 = {f.name: f for f in profile1.functions}
        funcs2 = {f.name: f for f in profile2.functions}
        
        comparison = {
            'improved': [],
            'degraded': [],
            'new': [],
            'removed': []
        }
        
        # Compare common functions
        for name in set(funcs1.keys()) & set(funcs2.keys()):
            f1, f2 = funcs1[name], funcs2[name]
            time_diff = f2.cumulative_time - f1.cumulative_time
            pct_diff = (time_diff / f1.cumulative_time * 100) if f1.cumulative_time > 0 else 0
            
            if pct_diff > 10:
                comparison['degraded'].append({
                    'name': name,
                    'before': f1.cumulative_time,
                    'after': f2.cumulative_time,
                    'diff_pct': pct_diff
                })
            elif pct_diff < -10:
                comparison['improved'].append({
                    'name': name,
                    'before': f1.cumulative_time,
                    'after': f2.cumulative_time,
                    'diff_pct': abs(pct_diff)
                })
        
        # Find new and removed functions
        for name in set(funcs2.keys()) - set(funcs1.keys()):
            comparison['new'].append({'name': name, 'time': funcs2[name].cumulative_time})
        
        for name in set(funcs1.keys()) - set(funcs2.keys()):
            comparison['removed'].append({'name': name, 'time': funcs1[name].cumulative_time})
        
        return comparison
    
    def save_report(self, output_path: str, result: Optional[ProfileResult] = None):
        """Save profiling report to JSON file."""
        result = result or (self.results[-1] if self.results else None)
        
        if result:
            Path(output_path).write_text(json.dumps(result.to_dict(), indent=2))
            console.print(f"[green]✓[/green] Report saved to {output_path}")
    
    @staticmethod
    def profile_lines(func: Callable, follow: Optional[List[Callable]] = None):
        """Profile line-by-line execution (requires line_profiler)."""
        try:
            from line_profiler import LineProfiler
            
            profiler = LineProfiler()
            profiler.add_function(func)
            
            if follow:
                for f in follow:
                    profiler.add_function(f)
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return profiler(func)(*args, **kwargs)
            
            wrapper.print_stats = profiler.print_stats
            return wrapper
            
        except ImportError:
            console.print("[yellow]line_profiler not installed. Using basic profiling.[/yellow]")
            return func
    
    @staticmethod
    def profile_memory(func: Callable):
        """Profile memory usage (requires memory_profiler)."""
        try:
            from memory_profiler import profile
            return profile(func)
        except ImportError:
            console.print("[yellow]memory_profiler not installed.[/yellow]")
            return func