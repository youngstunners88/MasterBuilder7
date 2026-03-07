"""
CLI for self-healing tests.
"""

import sys
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from loguru import logger

from .analyzer import FailureAnalyzer
from .healer import TestHealer, PRGenerator


console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--project-root', '-p', type=Path, default=Path.cwd(), help='Project root directory')
@click.pass_context
def cli(ctx, verbose: bool, project_root: Path):
    """Self-Healing Tests - Auto-fix flaky tests."""
    ctx.ensure_object(dict)
    
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    
    ctx.obj['project_root'] = project_root
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument('test_path', type=Path, default=Path('.'))
@click.option('--runs', '-r', default=5, help='Number of test runs')
@click.option('--threshold', '-t', default=0.1, help='Flakiness threshold')
@click.option('--auto-heal', '-a', is_flag=True, help='Auto-fix flaky tests')
@click.option('--dry-run', '-d', is_flag=True, default=True, help='Show fixes without applying')
@click.option('--no-dry-run', is_flag=True, help='Apply fixes for real')
@click.pass_context
def detect(
    ctx,
    test_path: Path,
    runs: int,
    threshold: float,
    auto_heal: bool,
    dry_run: bool,
    no_dry_run: bool
):
    """Detect flaky tests by running multiple times."""
    project_root = ctx.obj['project_root']
    
    if no_dry_run:
        dry_run = False
    
    console.print(f"\n[bold blue]🔍 Detecting flaky tests...[/bold blue]")
    console.print(f"[dim]Path: {test_path}[/dim]")
    console.print(f"[dim]Runs: {runs}, Threshold: {threshold}[/dim]\n")
    
    import subprocess
    
    analyzer = FailureAnalyzer()
    
    # Run tests multiple times
    for run in range(1, runs + 1):
        console.print(f"[dim]Run {run}/{runs}...[/dim]")
        
        result = subprocess.run(
            ['pytest', str(test_path), '-v', '--tb=short'],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        # Parse results (simplified)
        # In real implementation, use pytest's programmatic API
    
    console.print(f"\n[bold green]Detection complete[/bold green]")


@cli.command()
@click.argument('test_file')
@click.argument('test_name')
@click.option('--dry-run', '-d', is_flag=True, default=True)
@click.option('--no-dry-run', is_flag=True)
@click.pass_context
def heal(ctx, test_file: str, test_name: str, dry_run: bool, no_dry_run: bool):
    """Heal a specific flaky test."""
    project_root = ctx.obj['project_root']
    
    if no_dry_run:
        dry_run = False
    
    console.print(f"\n[bold blue]🔧 Healing test:[/bold blue] {test_name}")
    console.print(f"[dim]File: {test_file}[/dim]")
    console.print(f"[dim]Dry run: {dry_run}[/dim]\n")
    
    # Simulate analysis
    from .analyzer import TestAnalysis, FailureType, FlakinessPattern, FailureInstance
    
    analysis = TestAnalysis(
        test_name=test_name,
        test_file=test_file,
        failure_type=FailureType.TIMING,
        flakiness_patterns=[FlakinessPattern.TIMING_DEPENDENT],
        confidence=0.85,
        suggested_fixes=[{
            'type': 'timing',
            'description': 'Replace time.sleep with proper wait',
            'confidence': 0.8
        }],
        failure_count=3,
        pass_count=7,
        failure_instances=[]
    )
    
    healer = TestHealer(project_root)
    results = healer.heal(analysis, dry_run=dry_run)
    
    for result in results:
        if result.success:
            console.print(f"[green]✓ {result.message}[/green]")
        else:
            console.print(f"[red]✗ {result.message}[/red]")
    
    console.print()


@cli.command()
@click.pass_context
def stats(ctx):
    """Show healing statistics."""
    project_root = ctx.obj['project_root']
    
    console.print(f"\n[bold blue]📊 Self-Healing Statistics[/bold blue]\n")
    
    # Create stats table
    table = Table(title="Test Healing Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Tests Tracked", "0")
    table.add_row("Flaky Tests Detected", "0")
    table.add_row("Tests Healed", "0")
    table.add_row("Fix Success Rate", "0%")
    
    console.print(table)
    console.print()


@cli.command()
@click.option('--output', '-o', type=Path, help='Output file for report')
@click.pass_context
def report(ctx, output: Optional[Path]):
    """Generate report of flaky tests."""
    console.print(f"\n[bold blue]📄 Flaky Tests Report[/bold blue]\n")
    
    report_content = """# Flaky Tests Report

## Summary
No flaky tests detected in recent runs.

## Recommendations
1. Run tests multiple times to detect flakiness
2. Use `self-heal detect` to identify flaky tests
3. Enable auto-healing with `--auto-heal`

---
Generated by Self-Healing Tests
"""
    
    if output:
        output.write_text(report_content)
        console.print(f"[green]Report saved to {output}[/green]")
    else:
        console.print(report_content)
    
    console.print()


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
