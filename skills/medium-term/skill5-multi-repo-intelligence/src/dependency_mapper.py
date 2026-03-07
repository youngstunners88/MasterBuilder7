"""Dependency mapper for cross-repo dependency analysis."""

import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict

from .indexer import RepoIndexer, CodeIndex


@dataclass
class DependencyLink:
    """Represents a dependency link between repositories."""
    source_repo: str
    target_repo: str
    dependency_type: str  # 'import', 'shared_lib', 'api', 'config'
    strength: int  # 1-10 scale
    details: List[str]


@dataclass
class SharedLibrary:
    """Represents a shared library or package."""
    name: str
    version: str
    used_by: List[str]
    type: str  # 'internal', 'external', 'vendor'


class DependencyMapper:
    """Maps dependencies across multiple repositories."""
    
    def __init__(self, indexer: RepoIndexer):
        self.indexer = indexer
        self.dependencies: List[DependencyLink] = []
        self.shared_libs: Dict[str, SharedLibrary] = {}
        self.api_dependencies: Dict[str, List[str]] = defaultdict(list)
        
    def map_dependencies(self) -> List[DependencyLink]:
        """Map all dependencies across indexed repositories."""
        self.dependencies = []
        
        # Find import-based dependencies
        self._map_import_dependencies()
        
        # Find shared library dependencies
        self._map_shared_libraries()
        
        # Find API dependencies
        self._map_api_dependencies()
        
        # Find configuration dependencies
        self._map_config_dependencies()
        
        return self.dependencies
    
    def _map_import_dependencies(self):
        """Map dependencies based on imports between repos."""
        repos = list(self.indexer.index.keys())
        
        for source_repo in repos:
            for idx in self.indexer.index[source_repo]:
                for imp in idx.imports:
                    # Check if this import references another indexed repo
                    for target_repo in repos:
                        if target_repo == source_repo:
                            continue
                        
                        # Check if import contains target repo name or path
                        if self._is_repo_reference(imp, target_repo):
                            self._add_dependency(
                                source_repo, target_repo, 'import',
                                f"{idx.path}: {imp[:80]}"
                            )
    
    def _map_shared_libraries(self):
        """Map shared library dependencies."""
        # Collect all dependencies from package files
        all_deps: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        for repo_name, metadata in self.indexer.metadata.items():
            for lang, deps in metadata.dependencies.items():
                if isinstance(deps, list):
                    for dep in deps:
                        all_deps[lang][dep].add(repo_name)
                elif isinstance(deps, dict):
                    for category, dep_list in deps.items():
                        if isinstance(dep_list, list):
                            for dep in dep_list:
                                all_deps[lang][dep].add(repo_name)
                        elif isinstance(dep_list, dict):
                            for dep in dep_list.keys():
                                all_deps[lang][dep].add(repo_name)
        
        # Find libraries used by multiple repos
        for lang, deps in all_deps.items():
            for lib_name, repos in deps.items():
                if len(repos) > 1:
                    shared_lib = SharedLibrary(
                        name=lib_name,
                        version="unknown",
                        used_by=list(repos),
                        type='external' if not lib_name.startswith('.') else 'internal'
                    )
                    self.shared_libs[f"{lang}:{lib_name}"] = shared_lib
                    
                    # Create dependency links for each pair
                    repo_list = list(repos)
                    for i, repo1 in enumerate(repo_list):
                        for repo2 in repo_list[i+1:]:
                            self._add_dependency(
                                repo1, repo2, 'shared_lib',
                                f"Shared {lang} library: {lib_name}",
                                strength=len(repos)
                            )
    
    def _map_api_dependencies(self):
        """Map API endpoint dependencies between services."""
        # Pattern to match API calls
        api_patterns = [
            re.compile(r'https?://[^\s\'"]+'),  # URLs
            re.compile(r'fetch\([\'"]([^\'"]+)[\'"]'),  # fetch calls
            re.compile(r'axios\.[get|post|put|delete]+\([\'"]([^\'"]+)[\'"]'),  # axios
            re.compile(r'requests\.[get|post|put|delete]+\([\'"]([^\'"]+)[\'"]'),  # Python requests
            re.compile(r'@app\.(route|get|post|put|delete)\s*\([\'"]([^\'"]+)[\'"]'),  # Flask/FastAPI
        ]
        
        # Find API definitions and calls
        api_definitions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # repo -> [(path, endpoint)]
        api_calls: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # repo -> [(path, url)]
        
        for repo_name, indices in self.indexer.index.items():
            for idx in indices:
                # Read file content to find API patterns
                try:
                    file_path = Path(self.indexer.metadata[repo_name].full_name) / idx.path
                    if file_path.exists():
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        
                        # Look for API definitions
                        for pattern in api_patterns[-1:]:  # Route definitions
                            matches = pattern.findall(content)
                            for match in matches:
                                if isinstance(match, tuple):
                                    match = match[1] if len(match) > 1 else match[0]
                                api_definitions[repo_name].append((idx.path, match))
                        
                        # Look for API calls
                        for pattern in api_patterns[:-1]:  # URL/call patterns
                            matches = pattern.findall(content)
                            for match in matches:
                                if isinstance(match, tuple):
                                    match = match[0]
                                if 'localhost' in match or '127.0.0.1' in match:
                                    continue  # Skip local dev URLs
                                api_calls[repo_name].append((idx.path, match))
                except Exception:
                    pass
        
        # Map API dependencies
        for source_repo, calls in api_calls.items():
            for file_path, url in calls:
                # Check if URL matches any API definition
                for target_repo, definitions in api_definitions.items():
                    if target_repo == source_repo:
                        continue
                    
                    for def_path, endpoint in definitions:
                        if endpoint in url or url.endswith(endpoint):
                            self._add_dependency(
                                source_repo, target_repo, 'api',
                                f"{file_path} calls {endpoint} from {target_repo}"
                            )
                            break
    
    def _map_config_dependencies(self):
        """Map configuration file dependencies."""
        # Find shared configuration files
        config_patterns = ['*.yaml', '*.yml', '*.json', '*.toml', '*.env*']
        
        shared_configs: Dict[str, Set[str]] = defaultdict(set)
        
        for repo_name, indices in self.indexer.index.items():
            for idx in indices:
                if any(idx.path.endswith(ext.lstrip('*')) for ext in config_patterns):
                    config_name = Path(idx.path).name
                    shared_configs[config_name].add(repo_name)
        
        # Create dependencies for shared configs
        for config_name, repos in shared_configs.items():
            if len(repos) > 1:
                repo_list = list(repos)
                for i, repo1 in enumerate(repo_list):
                    for repo2 in repo_list[i+1:]:
                        self._add_dependency(
                            repo1, repo2, 'config',
                            f"Shared config: {config_name}",
                            strength=len(repos)
                        )
    
    def _is_repo_reference(self, import_stmt: str, repo_name: str) -> bool:
        """Check if an import statement references a specific repo."""
        # Clean repo name for comparison
        repo_clean = repo_name.lower().replace('-', '_').replace('.', '_')
        import_clean = import_stmt.lower().replace('-', '_').replace('.', '_')
        
        # Check direct reference
        if repo_clean in import_clean:
            return True
        
        # Check for common patterns
        patterns = [
            rf'\b{repo_clean}\b',
            rf'from\s+{repo_clean}',
            rf'import\s+{repo_clean}',
            rf'@{repo_clean}',
        ]
        
        return any(re.search(p, import_clean) for p in patterns)
    
    def _add_dependency(self, source: str, target: str, dep_type: str, 
                       detail: str, strength: int = 1):
        """Add a dependency link."""
        # Check if similar dependency already exists
        for dep in self.dependencies:
            if (dep.source_repo == source and dep.target_repo == target and 
                dep.dependency_type == dep_type):
                if detail not in dep.details:
                    dep.details.append(detail)
                    dep.strength = min(10, dep.strength + strength)
                return
        
        self.dependencies.append(DependencyLink(
            source_repo=source,
            target_repo=target,
            dependency_type=dep_type,
            strength=strength,
            details=[detail]
        ))
    
    def get_dependency_matrix(self) -> Dict[str, Dict[str, int]]:
        """Get a matrix of dependency strengths between repos."""
        repos = list(self.indexer.index.keys())
        matrix = {repo: {other: 0 for other in repos} for repo in repos}
        
        for dep in self.dependencies:
            matrix[dep.source_repo][dep.target_repo] += dep.strength
        
        return matrix
    
    def get_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies between repositories."""
        # Build adjacency list
        graph: Dict[str, Set[str]] = defaultdict(set)
        
        for dep in self.dependencies:
            graph[dep.source_repo].add(dep.target_repo)
        
        # Find cycles using DFS
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def get_repo_dependencies(self, repo_name: str) -> Dict[str, List[DependencyLink]]:
        """Get all dependencies for a specific repository."""
        return {
            'incoming': [d for d in self.dependencies if d.target_repo == repo_name],
            'outgoing': [d for d in self.dependencies if d.source_repo == repo_name]
        }
    
    def get_impact_analysis(self, repo_name: str) -> Dict[str, any]:
        """Analyze the impact of changes to a repository."""
        deps = self.get_repo_dependencies(repo_name)
        
        # Direct dependents
        direct_dependents = set(d.source_repo for d in deps['incoming'])
        
        # Transitive dependents (2 levels deep)
        transitive_dependents = set()
        for dep in deps['incoming']:
            sub_deps = self.get_repo_dependencies(dep.source_repo)
            transitive_dependents.update(d.source_repo for d in sub_deps['incoming'])
        
        transitive_dependents -= direct_dependents
        
        # Shared libraries that would be affected
        affected_libs = [
            lib for lib in self.shared_libs.values()
            if repo_name in lib.used_by
        ]
        
        return {
            'repo': repo_name,
            'direct_dependents': list(direct_dependents),
            'transitive_dependents': list(transitive_dependents),
            'total_affected': len(direct_dependents) + len(transitive_dependents),
            'shared_libraries_affected': affected_libs,
            'risk_level': 'high' if len(direct_dependents) > 3 else 
                         'medium' if len(direct_dependents) > 0 else 'low'
        }
    
    def generate_dependency_report(self) -> str:
        """Generate a markdown report of all dependencies."""
        lines = [
            "# Multi-Repository Dependency Report",
            "",
            f"Generated: {self._get_timestamp()}",
            f"Total Repositories: {len(self.indexer.index)}",
            f"Total Dependencies: {len(self.dependencies)}",
            f"Shared Libraries: {len(self.shared_libs)}",
            "",
            "## Dependency Links",
            ""
        ]
        
        # Group by type
        by_type: Dict[str, List[DependencyLink]] = defaultdict(list)
        for dep in self.dependencies:
            by_type[dep.dependency_type].append(dep)
        
        for dep_type, deps in sorted(by_type.items()):
            lines.append(f"### {dep_type.upper()} Dependencies")
            lines.append("")
            for dep in sorted(deps, key=lambda d: -d.strength):
                lines.append(f"- **{dep.source_repo}** → **{dep.target_repo}** (strength: {dep.strength})")
                for detail in dep.details[:3]:  # Show first 3 details
                    lines.append(f"  - {detail}")
                if len(dep.details) > 3:
                    lines.append(f"  - ... and {len(dep.details) - 3} more")
            lines.append("")
        
        # Shared libraries
        if self.shared_libs:
            lines.append("## Shared Libraries")
            lines.append("")
            for lib in sorted(self.shared_libs.values(), key=lambda l: -len(l.used_by)):
                lines.append(f"- **{lib.name}** ({lib.type})")
                lines.append(f"  - Used by: {', '.join(lib.used_by)}")
            lines.append("")
        
        # Circular dependencies
        cycles = self.get_circular_dependencies()
        if cycles:
            lines.append("## ⚠️ Circular Dependencies Detected")
            lines.append("")
            for i, cycle in enumerate(cycles, 1):
                lines.append(f"{i}. {' → '.join(cycle)}")
            lines.append("")
        
        # Impact analysis for each repo
        lines.append("## Impact Analysis")
        lines.append("")
        for repo in sorted(self.indexer.index.keys()):
            impact = self.get_impact_analysis(repo)
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[impact['risk_level']]
            lines.append(f"### {emoji} {repo}")
            lines.append(f"- Risk Level: **{impact['risk_level'].upper()}**")
            lines.append(f"- Direct Dependents: {len(impact['direct_dependents'])}")
            lines.append(f"- Transitive Dependents: {len(impact['transitive_dependents'])}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()