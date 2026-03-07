"""Breaking change alerter for cross-repo impact detection."""

import hashlib
import json
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import asyncio

from rich.console import Console
from rich.table import Table

from .indexer import RepoIndexer, CodeIndex
from .dependency_mapper import DependencyMapper

console = Console()


@dataclass
class ChangeAlert:
    """Represents a detected breaking change."""
    id: str
    repo: str
    file_path: str
    change_type: str  # 'signature_change', 'removal', 'behavior_change', 'dependency_update'
    severity: str  # 'critical', 'high', 'medium', 'low'
    symbol: str
    old_state: Optional[str]
    new_state: Optional[str]
    affected_repos: List[str]
    detected_at: str
    description: str


@dataclass
class BaselineState:
    """Baseline state of a repository for comparison."""
    repo: str
    file_hashes: Dict[str, str]
    symbols: Dict[str, Dict[str, str]]  # file -> symbol -> signature
    exports: Dict[str, List[str]]  # file -> exports
    dependencies: Dict[str, List[str]]
    timestamp: str


class BreakingChangeAlerter:
    """Detects breaking changes across repositories and alerts on impact."""
    
    def __init__(self, indexer: RepoIndexer, mapper: Optional[DependencyMapper] = None):
        self.indexer = indexer
        self.mapper = mapper or DependencyMapper(indexer)
        self.baselines: Dict[str, BaselineState] = {}
        self.alerts: List[ChangeAlert] = []
        self.alert_handlers: List[Callable[[ChangeAlert], None]] = []
        
    def capture_baseline(self, repo_name: Optional[str] = None) -> Dict[str, BaselineState]:
        """Capture the current state as a baseline for future comparison."""
        repos = [repo_name] if repo_name else list(self.indexer.index.keys())
        
        for repo in repos:
            if repo not in self.indexer.index:
                console.print(f"[yellow]Warning:[/yellow] Repository {repo} not indexed")
                continue
            
            file_hashes = {}
            symbols = {}
            exports = {}
            
            for idx in self.indexer.index[repo]:
                file_hashes[idx.path] = idx.content_hash
                
                # Extract symbol signatures
                symbols[idx.path] = self._extract_signatures(repo, idx)
                exports[idx.path] = idx.exports
            
            baseline = BaselineState(
                repo=repo,
                file_hashes=file_hashes,
                symbols=symbols,
                exports=exports,
                dependencies=self.indexer.metadata.get(repo, {}).dependencies,
                timestamp=datetime.now().isoformat()
            )
            
            self.baselines[repo] = baseline
            console.print(f"[green]✓[/green] Baseline captured for {repo}")
        
        return self.baselines
    
    def _extract_signatures(self, repo: str, idx: CodeIndex) -> Dict[str, str]:
        """Extract function/class signatures from a file."""
        signatures = {}
        
        try:
            repo_path = Path(self.indexer.metadata[repo].full_name)
            file_path = repo_path / idx.path
            
            if not file_path.exists():
                return signatures
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            if idx.language == 'python':
                signatures = self._extract_python_signatures(lines)
            elif idx.language in ('javascript', 'typescript'):
                signatures = self._extract_js_signatures(lines)
            elif idx.language == 'rust':
                signatures = self._extract_rust_signatures(lines)
            elif idx.language == 'go':
                signatures = self._extract_go_signatures(lines)
            
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not extract signatures from {idx.path}: {e}")
        
        return signatures
    
    def _extract_python_signatures(self, lines: List[str]) -> Dict[str, str]:
        """Extract Python function/class signatures."""
        import re
        signatures = {}
        
        # Function definitions
        func_pattern = re.compile(r'^(async\s+)?def\s+(\w+)\s*\(([^)]*)\)')
        class_pattern = re.compile(r'^class\s+(\w+)\s*(?:\(([^)]*)\))?')
        
        for line in lines:
            # Match functions
            match = func_pattern.match(line.strip())
            if match:
                name = match.group(2)
                params = match.group(3)
                signatures[name] = f"def {name}({params})"
            
            # Match classes
            match = class_pattern.match(line.strip())
            if match:
                name = match.group(1)
                parent = match.group(2) or ""
                signatures[name] = f"class {name}({parent})"
        
        return signatures
    
    def _extract_js_signatures(self, lines: List[str]) -> Dict[str, str]:
        """Extract JavaScript/TypeScript signatures."""
        import re
        signatures = {}
        
        patterns = [
            re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'),
            re.compile(r'(?:export\s+)?class\s+(\w+)\s*(?:extends\s+(\w+))?'),
            re.compile(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>'),
            re.compile(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*function\s*\(([^)]*)\)'),
        ]
        
        for line in lines:
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    name = match.group(1)
                    sig = match.group(0).strip()
                    signatures[name] = sig[:100]  # Truncate long signatures
        
        return signatures
    
    def _extract_rust_signatures(self, lines: List[str]) -> Dict[str, str]:
        """Extract Rust function/struct signatures."""
        import re
        signatures = {}
        
        patterns = [
            re.compile(r'^(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)'),
            re.compile(r'^(?:pub\s+)?struct\s+(\w+)'),
            re.compile(r'^(?:pub\s+)?trait\s+(\w+)'),
            re.compile(r'^(?:pub\s+)?enum\s+(\w+)'),
        ]
        
        for line in lines:
            for pattern in patterns:
                match = pattern.match(line.strip())
                if match:
                    name = match.group(1)
                    sig = match.group(0).strip()
                    signatures[name] = sig[:100]
        
        return signatures
    
    def _extract_go_signatures(self, lines: List[str]) -> Dict[str, str]:
        """Extract Go function signatures."""
        import re
        signatures = {}
        
        func_pattern = re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)')
        
        for line in lines:
            match = func_pattern.match(line.strip())
            if match:
                name = match.group(1)
                params = match.group(2)
                signatures[name] = f"func {name}({params})"
        
        return signatures
    
    def detect_changes(self, repo_name: Optional[str] = None) -> List[ChangeAlert]:
        """Detect changes compared to baseline."""
        if not self.baselines:
            console.print("[yellow]Warning:[/yellow] No baseline captured. Call capture_baseline() first.")
            return []
        
        repos = [repo_name] if repo_name else list(self.baselines.keys())
        new_alerts = []
        
        for repo in repos:
            if repo not in self.baselines:
                continue
            
            baseline = self.baselines[repo]
            current_indices = {idx.path: idx for idx in self.indexer.index.get(repo, [])}
            
            # Check for file changes
            for file_path, current_idx in current_indices.items():
                if file_path not in baseline.file_hashes:
                    # New file
                    alert = self._create_alert(
                        repo, file_path, 'new_file', 'low',
                        file_path, None, None,
                        f"New file added: {file_path}"
                    )
                    new_alerts.append(alert)
                elif baseline.file_hashes[file_path] != current_idx.content_hash:
                    # File changed - check for breaking changes
                    file_alerts = self._analyze_file_changes(repo, file_path, baseline, current_idx)
                    new_alerts.extend(file_alerts)
            
            # Check for removed files
            for file_path in baseline.file_hashes:
                if file_path not in current_indices:
                    # Check if file was used by other repos
                    affected = self._get_affected_by_file_removal(repo, file_path)
                    severity = 'critical' if affected else 'medium'
                    
                    alert = self._create_alert(
                        repo, file_path, 'removal', severity,
                        file_path, baseline.file_hashes[file_path], None,
                        f"File removed: {file_path}",
                        affected
                    )
                    new_alerts.append(alert)
            
            # Check for dependency changes
            current_deps = self.indexer.metadata.get(repo, {}).dependencies
            dep_alerts = self._analyze_dependency_changes(repo, baseline.dependencies, current_deps)
            new_alerts.extend(dep_alerts)
        
        self.alerts.extend(new_alerts)
        
        # Notify handlers
        for alert in new_alerts:
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    console.print(f"[red]Alert handler error:[/red] {e}")
        
        return new_alerts
    
    def _analyze_file_changes(self, repo: str, file_path: str, 
                             baseline: BaselineState, current_idx: CodeIndex) -> List[ChangeAlert]:
        """Analyze changes in a single file."""
        alerts = []
        old_symbols = baseline.symbols.get(file_path, {})
        
        try:
            repo_path = Path(self.indexer.metadata[repo].full_name)
            file_path_full = repo_path / file_path
            content = file_path_full.read_text(encoding='utf-8', errors='ignore')
            
            # Re-extract current signatures
            lines = content.split('\n')
            if current_idx.language == 'python':
                new_symbols = self._extract_python_signatures(lines)
            elif current_idx.language in ('javascript', 'typescript'):
                new_symbols = self._extract_js_signatures(lines)
            elif current_idx.language == 'rust':
                new_symbols = self._extract_rust_signatures(lines)
            elif current_idx.language == 'go':
                new_symbols = self._extract_go_signatures(lines)
            else:
                new_symbols = {}
            
            # Compare symbols
            for symbol, old_sig in old_symbols.items():
                if symbol not in new_symbols:
                    # Symbol removed
                    affected = self._get_affected_by_symbol_removal(repo, symbol)
                    severity = 'critical' if affected else 'high'
                    
                    alerts.append(self._create_alert(
                        repo, file_path, 'removal', severity,
                        symbol, old_sig, None,
                        f"Symbol removed: {symbol} from {file_path}",
                        affected
                    ))
                elif old_sig != new_symbols[symbol]:
                    # Signature changed
                    affected = self._get_affected_by_signature_change(repo, symbol)
                    severity = 'high' if affected else 'medium'
                    
                    alerts.append(self._create_alert(
                        repo, file_path, 'signature_change', severity,
                        symbol, old_sig, new_symbols[symbol],
                        f"Signature changed: {symbol}",
                        affected
                    ))
            
            # New symbols (not breaking, but worth noting)
            for symbol in new_symbols:
                if symbol not in old_symbols:
                    alerts.append(self._create_alert(
                        repo, file_path, 'new_symbol', 'low',
                        symbol, None, new_symbols[symbol],
                        f"New symbol added: {symbol}"
                    ))
            
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not analyze changes in {file_path}: {e}")
        
        return alerts
    
    def _analyze_dependency_changes(self, repo: str, old_deps: Dict, new_deps: Dict) -> List[ChangeAlert]:
        """Analyze changes in dependencies."""
        alerts = []
        
        # Flatten dependency structures for comparison
        def flatten_deps(deps):
            flat = set()
            if isinstance(deps, dict):
                for v in deps.values():
                    if isinstance(v, list):
                        flat.update(v)
                    elif isinstance(v, dict):
                        flat.update(v.keys())
            return flat
        
        old_flat = flatten_deps(old_deps)
        new_flat = flatten_deps(new_deps)
        
        # Check for removed dependencies
        removed = old_flat - new_flat
        for dep in removed:
            alerts.append(self._create_alert(
                repo, "dependencies", 'dependency_update', 'high',
                dep, str(dep), None,
                f"Dependency removed: {dep}"
            ))
        
        # Check for added dependencies
        added = new_flat - old_flat
        for dep in added:
            alerts.append(self._create_alert(
                repo, "dependencies", 'dependency_update', 'low',
                dep, None, str(dep),
                f"New dependency added: {dep}"
            ))
        
        return alerts
    
    def _get_affected_by_symbol_removal(self, repo: str, symbol: str) -> List[str]:
        """Get repositories affected by removal of a symbol."""
        affected = []
        
        for dep in self.mapper.dependencies:
            if dep.target_repo == repo:
                # Check if any dependency detail mentions the symbol
                for detail in dep.details:
                    if symbol in detail:
                        affected.append(dep.source_repo)
                        break
        
        return list(set(affected))
    
    def _get_affected_by_signature_change(self, repo: str, symbol: str) -> List[str]:
        """Get repositories affected by a signature change."""
        return self._get_affected_by_symbol_removal(repo, symbol)
    
    def _get_affected_by_file_removal(self, repo: str, file_path: str) -> List[str]:
        """Get repositories affected by removal of a file."""
        affected = []
        
        for dep in self.mapper.dependencies:
            if dep.target_repo == repo:
                for detail in dep.details:
                    if file_path in detail:
                        affected.append(dep.source_repo)
                        break
        
        return list(set(affected))
    
    def _create_alert(self, repo: str, file_path: str, change_type: str,
                     severity: str, symbol: str, old_state: Optional[str],
                     new_state: Optional[str], description: str,
                     affected_repos: Optional[List[str]] = None) -> ChangeAlert:
        """Create a new change alert."""
        alert_id = hashlib.md5(
            f"{repo}:{file_path}:{symbol}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return ChangeAlert(
            id=alert_id,
            repo=repo,
            file_path=file_path,
            change_type=change_type,
            severity=severity,
            symbol=symbol,
            old_state=old_state,
            new_state=new_state,
            affected_repos=affected_repos or [],
            detected_at=datetime.now().isoformat(),
            description=description
        )
    
    def register_alert_handler(self, handler: Callable[[ChangeAlert], None]):
        """Register a handler to be called when alerts are generated."""
        self.alert_handlers.append(handler)
    
    def get_alerts(self, severity: Optional[str] = None, 
                   repo: Optional[str] = None) -> List[ChangeAlert]:
        """Get alerts, optionally filtered by severity or repo."""
        filtered = self.alerts
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if repo:
            filtered = [a for a in filtered if a.repo == repo]
        
        return filtered
    
    def display_alerts(self, alerts: Optional[List[ChangeAlert]] = None):
        """Display alerts in a formatted table."""
        alerts = alerts or self.alerts
        
        if not alerts:
            console.print("[green]No alerts to display[/green]")
            return
        
        table = Table(title="Breaking Change Alerts")
        table.add_column("ID", style="cyan")
        table.add_column("Repo", style="magenta")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Symbol", style="green")
        table.add_column("Affected", style="blue")
        
        for alert in alerts:
            severity_color = {
                'critical': 'red',
                'high': 'orange3',
                'medium': 'yellow',
                'low': 'green'
            }.get(alert.severity, 'white')
            
            table.add_row(
                alert.id,
                alert.repo,
                alert.change_type,
                f"[{severity_color}]{alert.severity}[/{severity_color}]",
                alert.symbol[:30],
                str(len(alert.affected_repos))
            )
        
        console.print(table)
    
    def save_baseline(self, path: str = "baseline.json"):
        """Save baselines to a JSON file."""
        data = {
            repo: {
                'repo': b.repo,
                'file_hashes': b.file_hashes,
                'symbols': b.symbols,
                'exports': b.exports,
                'dependencies': b.dependencies,
                'timestamp': b.timestamp
            }
            for repo, b in self.baselines.items()
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        console.print(f"[green]✓[/green] Baseline saved to {path}")
    
    def load_baseline(self, path: str = "baseline.json"):
        """Load baselines from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        
        for repo, b in data.items():
            self.baselines[repo] = BaselineState(
                repo=b['repo'],
                file_hashes=b['file_hashes'],
                symbols=b['symbols'],
                exports=b['exports'],
                dependencies=b['dependencies'],
                timestamp=b['timestamp']
            )
        
        console.print(f"[green]✓[/green] Baseline loaded from {path}")
    
    def export_alerts_to_github_issues(self, repo_full_name: str,
                                       github_token: Optional[str] = None):
        """Export critical alerts as GitHub issues."""
        from github import Github
        
        token = github_token or self.indexer.github_token
        if not token:
            raise ValueError("GitHub token required")
        
        g = Github(token)
        repo = g.get_repo(repo_full_name)
        
        critical_alerts = [a for a in self.alerts if a.severity in ('critical', 'high')]
        
        for alert in critical_alerts:
            title = f"[Breaking Change] {alert.symbol} in {alert.repo}"
            body = f"""## Breaking Change Detected

**Repository:** {alert.repo}
**File:** {alert.file_path}
**Type:** {alert.change_type}
**Severity:** {alert.severity}
**Detected:** {alert.detected_at}

### Description
{alert.description}

### Affected Repositories
{chr(10).join(f"- {r}" for r in alert.affected_repos) or "None detected"}

### Change Details
**Before:**
```
{alert.old_state or "N/A"}
```

**After:**
```
{alert.new_state or "N/A"}
```

---
*This issue was automatically generated by Multi-Repo Intelligence*
"""
            
            try:
                issue = repo.create_issue(title=title, body=body, labels=['breaking-change', alert.severity])
                console.print(f"[green]✓[/green] Created issue #{issue.number}: {title}")
            except Exception as e:
                console.print(f"[red]Failed to create issue:[/red] {e}")