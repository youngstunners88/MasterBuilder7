"""
CLI for semantic code search.
"""

import sys
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from loguru import logger

from .search import SemanticSearchEngine, CodeNavigator
from .embeddings import EmbeddingManager


console = Console()


def get_project_root() -> Path:
    """Get project root from git or current directory."""
    cwd = Path.cwd()
    
    # Look for .git directory
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists():
            return parent
    
    return cwd


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--project-root', '-p', type=Path, help='Project root directory')
@click.pass_context
def cli(ctx, verbose: bool, project_root: Optional[Path]):
    """Semantic Code Search - Find code using natural language."""
    ctx.ensure_object(dict)
    
    # Configure logging
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="WARNING")
    
    # Set project root
    ctx.obj['project_root'] = project_root or get_project_root()
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument('query')
@click.option('--top-k', '-k', default=10, help='Number of results to show')
@click.option('--language', '-l', help='Filter by language (python, javascript, etc.)')
@click.option('--type', '-t', 'element_type', help='Filter by type (function, class, etc.)')
@click.option('--file', '-f', 'file_filter', help='Filter by file path pattern')
@click.option('--min-score', '-m', default=0.0, help='Minimum relevance score')
@click.option('--expand', '-e', is_flag=True, help='Expand query with synonyms')
@click.option('--show-code', '-c', is_flag=True, help='Show full code content')
@click.pass_context
def search(
    ctx,
    query: str,
    top_k: int,
    language: Optional[str],
    element_type: Optional[str],
    file_filter: Optional[str],
    min_score: float,
    expand: bool,
    show_code: bool
):
    """Search for code using natural language."""
    project_root = ctx.obj['project_root']
    
    console.print(f"\n[bold blue]🔍 Searching:[/bold blue] {query}")
    console.print(f"[dim]Project: {project_root}[/dim]\n")
    
    # Initialize and index
    engine = SemanticSearchEngine(project_root)
    
    cache_dir = project_root / ".kimi" / "semantic-search"
    index_file = cache_dir / "code_index.json"
    embeddings_file = cache_dir / "embeddings.json"
    
    if index_file.exists() and embeddings_file.exists():
        try:
            console.print("[dim]Loading cached index...[/dim]")
            engine.load(cache_dir)
        except Exception as e:
            console.print(f"[yellow]Cache load failed, reindexing: {e}[/yellow]")
            engine.index()
            engine.save(cache_dir)
    else:
        with console.status("[bold green]Indexing project..."):
            engine.index(languages=language and [language])
        engine.save(cache_dir)
    
    # Perform search
    if expand:
        results = engine.search_with_expansion(
            query,
            top_k=top_k,
            language_filter=language,
            type_filter=element_type,
            file_filter=file_filter,
            min_score=min_score
        )
    else:
        results = engine.search(
            query,
            top_k=top_k,
            language_filter=language,
            type_filter=element_type,
            file_filter=file_filter,
            min_score=min_score
        )
    
    # Display results
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    console.print(f"[bold green]Found {len(results)} results:[/bold green]\n")
    
    for i, result in enumerate(results, 1):
        # Create result panel
        header = f"[bold]{i}. {result.name}[/bold] [dim]({result.element_type})[/dim]"
        
        content_lines = [
            f"[dim]File:[/dim] {result.file_path}:{result.start_line}",
            f"[dim]Language:[/dim] {result.language}",
            f"[dim]Relevance:[/dim] [bold]{'⭐' * int(result.relevance_score * 5)}[/bold] {result.relevance_score:.3f}",
        ]
        
        if result.signature:
            content_lines.append(f"\n[dim]Signature:[/dim]\n[cyan]{result.signature}[/cyan]")
        
        if result.docstring:
            doc = result.docstring[:200] + "..." if len(result.docstring) > 200 else result.docstring
            content_lines.append(f"\n[dim]Documentation:[/dim]\n[italic]{doc}[/italic]")
        
        if show_code:
            code = result.content_preview
            if len(code) > 1000:
                code = code[:1000] + "\n... (truncated)"
            
            syntax = Syntax(
                code,
                result.language if result.language != 'tsx' else 'typescript',
                theme="monokai",
                line_numbers=True,
                start_line=result.start_line
            )
            content_lines.append(f"\n[dim]Code:[/dim]")
            console.print(Panel("\n".join(content_lines), title=header, expand=False))
            console.print(syntax)
        else:
            console.print(Panel("\n".join(content_lines), title=header, expand=False))
    
    console.print()


@cli.command()
@click.argument('file_path')
@click.argument('symbol_name')
@click.option('--line', type=int, help='Line number of the symbol')
@click.option('--top-k', '-k', default=5, help='Number of similar items to show')
@click.pass_context
def similar(ctx, file_path: str, symbol_name: str, line: Optional[int], top_k: int):
    """Find similar code elements."""
    project_root = ctx.obj['project_root']
    
    console.print(f"\n[bold blue]🔍 Finding similar to:[/bold blue] {symbol_name}")
    console.print(f"[dim]File: {file_path}[/dim]\n")
    
    engine = SemanticSearchEngine(project_root)
    cache_dir = project_root / ".kimi" / "semantic-search"
    
    if (cache_dir / "embeddings.json").exists():
        engine.load(cache_dir)
    else:
        engine.index()
        engine.save(cache_dir)
    
    # Try to find the element
    if line is None:
        # Search for the element
        elements = engine.indexer.get_elements()
        for elem in elements:
            if elem.name == symbol_name and file_path in elem.file_path:
                line = elem.start_line
                break
    
    if line is None:
        console.print(f"[red]Could not find {symbol_name} in {file_path}[/red]")
        console.print("[dim]Try specifying --line[/dim]")
        return
    
    try:
        results = engine.find_similar(file_path, symbol_name, line, top_k=top_k)
        
        if not results:
            console.print("[yellow]No similar elements found.[/yellow]")
            return
        
        console.print(f"[bold green]Top {len(results)} similar elements:[/bold green]\n")
        
        for i, result in enumerate(results, 1):
            tree = Tree(f"[bold]{i}. {result.name}[/bold] ({result.element_type})")
            tree.add(f"[dim]File:[/dim] {result.file_path}:{result.start_line}")
            tree.add(f"[dim]Similarity:[/dim] {result.relevance_score:.3f}")
            if result.signature:
                tree.add(f"[dim]Signature:[/dim] {result.signature}")
            console.print(tree)
            console.print()
    
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@cli.command()
@click.argument('symbol')
@click.pass_context
def definition(ctx, symbol: str):
    """Find the definition of a symbol."""
    project_root = ctx.obj['project_root']
    
    console.print(f"\n[bold blue]🔍 Finding definition of:[/bold blue] {symbol}\n")
    
    engine = SemanticSearchEngine(project_root)
    cache_dir = project_root / ".kimi" / "semantic-search"
    
    if (cache_dir / "embeddings.json").exists():
        engine.load(cache_dir)
    else:
        engine.index()
        engine.save(cache_dir)
    
    navigator = CodeNavigator(engine)
    result = navigator.find_definition(symbol)
    
    if result:
        console.print(Panel(
            f"[bold]{result.name}[/bold] ({result.element_type})\n\n"
            f"[dim]File:[/dim] {result.file_path}:{result.start_line}\n"
            f"[dim]Language:[/dim] {result.language}\n"
            f"{result.signature or ''}\n\n"
            f"[dim]{result.content_preview[:300]}...[/dim]",
            title="[bold green]Definition Found[/bold green]",
            expand=False
        ))
    else:
        console.print(f"[yellow]Could not find definition of {symbol}[/yellow]")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show indexing statistics."""
    project_root = ctx.obj['project_root']
    
    console.print(f"\n[bold blue]📊 Semantic Search Statistics[/bold blue]")
    console.print(f"[dim]Project: {project_root}[/dim]\n")
    
    engine = SemanticSearchEngine(project_root)
    cache_dir = project_root / ".kimi" / "semantic-search"
    
    if (cache_dir / "embeddings.json").exists():
        engine.load(cache_dir)
    else:
        console.print("[yellow]No index found. Run 'semantic-search search <query>' first.[/yellow]")
        return
    
    stats = engine.get_stats()
    
    # Create stats table
    table = Table(title="Index Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Status", stats['status'])
    table.add_row("Total Elements", str(stats['total_elements']))
    table.add_row("Languages", ", ".join(stats['languages']))
    
    # Element types breakdown
    for elem_type, count in sorted(stats['element_types'].items(), key=lambda x: -x[1]):
        table.add_row(f"  {elem_type}", str(count))
    
    console.print(table)
    console.print()


@cli.command()
@click.option('--languages', '-l', help='Comma-separated list of languages')
@click.pass_context
def index(ctx, languages: Optional[str]):
    """Force reindex the project."""
    project_root = ctx.obj['project_root']
    
    console.print(f"\n[bold blue]🔄 Indexing project...[/bold blue]")
    console.print(f"[dim]Project: {project_root}[/dim]\n")
    
    engine = SemanticSearchEngine(project_root)
    
    lang_list = languages.split(',') if languages else None
    
    with console.status("[bold green]Indexing..."):
        engine.index(languages=lang_list)
    
    cache_dir = project_root / ".kimi" / "semantic-search"
    engine.save(cache_dir)
    
    stats = engine.get_stats()
    console.print(f"[bold green]✓ Indexed {stats['total_elements']} elements[/bold green]")
    console.print(f"  Languages: {', '.join(stats['languages'])}\n")


@cli.command()
@click.pass_context
def languages(ctx):
    """Show supported languages."""
    table = Table(title="Supported Languages")
    table.add_column("Language", style="cyan")
    table.add_column("Extensions", style="green")
    
    lang_map = {
        'python': '.py',
        'javascript': '.js, .jsx',
        'typescript': '.ts, .tsx',
        'rust': '.rs',
        'go': '.go',
        'java': '.java',
    }
    
    for lang, exts in lang_map.items():
        table.add_row(lang, exts)
    
    console.print(table)
    console.print()


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
