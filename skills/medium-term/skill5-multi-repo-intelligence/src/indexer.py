"""Repository indexer for multi-repo intelligence."""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
import aiohttp
from github import Github, Repository, ContentFile
import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class CodeIndex:
    """Index entry for a code file."""
    repo: str
    path: str
    content_hash: str
    language: str
    imports: List[str]
    exports: List[str]
    functions: List[str]
    classes: List[str]
    last_modified: str
    size_bytes: int


@dataclass
class RepoMetadata:
    """Metadata for a repository."""
    name: str
    full_name: str
    url: str
    default_branch: str
    languages: Dict[str, int]
    last_updated: str
    open_issues: int
    size_kb: int
    topics: List[str]
    dependencies: Dict[str, Any]


class RepoIndexer:
    """Indexes multiple GitHub repositories for analysis."""
    
    LANGUAGE_PATTERNS = {
        'python': ['*.py'],
        'javascript': ['*.js', '*.jsx', '*.ts', '*.tsx'],
        'rust': ['*.rs'],
        'go': ['*.go'],
        'java': ['*.java'],
        'ruby': ['*.rb'],
    }
    
    def __init__(self, github_token: Optional[str] = None, cache_dir: str = ".repo_cache"):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github = Github(self.github_token) if self.github_token else None
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index: Dict[str, List[CodeIndex]] = {}
        self.metadata: Dict[str, RepoMetadata] = {}
        
    def add_local_repo(self, path: str, name: Optional[str] = None) -> str:
        """Add a local repository to the index."""
        repo_path = Path(path).resolve()
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {path}")
        
        repo_name = name or repo_path.name
        
        console.print(f"[blue]Indexing local repository:[/blue] {repo_name}")
        
        try:
            git_repo = git.Repo(repo_path)
            metadata = RepoMetadata(
                name=repo_name,
                full_name=str(repo_path),
                url=git_repo.remotes.origin.url if git_repo.remotes else str(repo_path),
                default_branch=git_repo.active_branch.name,
                languages=self._detect_languages(repo_path),
                last_updated=datetime.now().isoformat(),
                open_issues=0,
                size_kb=self._get_dir_size(repo_path) // 1024,
                topics=[],
                dependencies=self._extract_dependencies(repo_path)
            )
            self.metadata[repo_name] = metadata
            
            # Index all code files
            self.index[repo_name] = self._index_directory(repo_path, repo_name)
            
            console.print(f"[green]✓[/green] Indexed {len(self.index[repo_name])} files from {repo_name}")
            return repo_name
            
        except git.InvalidGitRepositoryError:
            # Not a git repo, index anyway
            metadata = RepoMetadata(
                name=repo_name,
                full_name=str(repo_path),
                url=str(repo_path),
                default_branch="main",
                languages=self._detect_languages(repo_path),
                last_updated=datetime.now().isoformat(),
                open_issues=0,
                size_kb=self._get_dir_size(repo_path) // 1024,
                topics=[],
                dependencies=self._extract_dependencies(repo_path)
            )
            self.metadata[repo_name] = metadata
            self.index[repo_name] = self._index_directory(repo_path, repo_name)
            return repo_name
    
    def add_github_repo(self, repo_full_name: str) -> str:
        """Add a GitHub repository to the index."""
        if not self.github:
            raise ValueError("GitHub token required for GitHub repositories")
        
        console.print(f"[blue]Fetching GitHub repository:[/blue] {repo_full_name}")
        
        try:
            repo = self.github.get_repo(repo_full_name)
            repo_name = repo.name
            
            metadata = RepoMetadata(
                name=repo_name,
                full_name=repo.full_name,
                url=repo.html_url,
                default_branch=repo.default_branch,
                languages=repo.get_languages(),
                last_updated=repo.updated_at.isoformat(),
                open_issues=repo.open_issues_count,
                size_kb=repo.size,
                topics=repo.get_topics(),
                dependencies={}
            )
            self.metadata[repo_name] = metadata
            
            # Clone or use cached version
            cached_path = self.cache_dir / repo_name
            if cached_path.exists():
                console.print(f"[yellow]Using cached repository[/yellow]")
                git_repo = git.Repo(cached_path)
                git_repo.remotes.origin.pull()
            else:
                console.print(f"[blue]Cloning repository...[/blue]")
                git.Repo.clone_from(repo.clone_url, cached_path)
            
            # Index the repository
            self.index[repo_name] = self._index_directory(cached_path, repo_name)
            
            # Extract dependencies from package files
            self.metadata[repo_name].dependencies = self._extract_dependencies(cached_path)
            
            console.print(f"[green]✓[/green] Indexed {len(self.index[repo_name])} files from {repo_name}")
            return repo_name
            
        except Exception as e:
            console.print(f"[red]Error indexing {repo_full_name}:[/red] {e}")
            raise
    
    async def add_github_repos_async(self, repo_names: List[str]) -> List[str]:
        """Add multiple GitHub repositories concurrently."""
        tasks = [self._add_github_repo_async(name) for name in repo_names]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _add_github_repo_async(self, repo_full_name: str) -> str:
        """Async version of add_github_repo."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.add_github_repo, repo_full_name)
    
    def _index_directory(self, path: Path, repo_name: str) -> List[CodeIndex]:
        """Index all code files in a directory."""
        indices = []
        
        for pattern in ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx', '*.rs', '*.go', '*.java']:
            for file_path in path.rglob(pattern):
                if '.git' in str(file_path) or 'node_modules' in str(file_path):
                    continue
                
                try:
                    index = self._index_file(file_path, repo_name, path)
                    if index:
                        indices.append(index)
                except Exception as e:
                    console.print(f"[yellow]Warning:[/yellow] Could not index {file_path}: {e}")
        
        return indices
    
    def _index_file(self, file_path: Path, repo_name: str, repo_root: Path) -> Optional[CodeIndex]:
        """Index a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
        
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        language = self._detect_language(file_path)
        
        # Parse imports and exports based on language
        imports, exports = self._parse_imports_exports(content, language)
        functions, classes = self._parse_definitions(content, language)
        
        relative_path = str(file_path.relative_to(repo_root))
        
        return CodeIndex(
            repo=repo_name,
            path=relative_path,
            content_hash=content_hash,
            language=language,
            imports=imports,
            exports=exports,
            functions=functions,
            classes=classes,
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            size_bytes=file_path.stat().st_size
        )
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()
        mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.rb': 'ruby',
        }
        return mapping.get(ext, 'unknown')
    
    def _detect_languages(self, path: Path) -> Dict[str, int]:
        """Detect programming languages in a directory."""
        languages: Dict[str, int] = {}
        for pattern in ['*.py', '*.js', '*.ts', '*.rs', '*.go', '*.java']:
            count = len(list(path.rglob(pattern)))
            if count > 0:
                lang = self._detect_language(Path(f"file{pattern[1:]}"))
                languages[lang] = count
        return languages
    
    def _parse_imports_exports(self, content: str, language: str) -> tuple[List[str], List[str]]:
        """Parse imports and exports from code."""
        imports = []
        exports = []
        
        lines = content.split('\n')
        
        if language == 'python':
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
                elif line.startswith('__all__'):
                    exports.append(line)
        
        elif language in ('javascript', 'typescript'):
            for line in lines:
                line = line.strip()
                if 'import' in line and 'from' in line:
                    imports.append(line)
                elif line.startswith('export'):
                    exports.append(line)
                elif 'module.exports' in line:
                    exports.append(line)
        
        elif language == 'rust':
            for line in lines:
                line = line.strip()
                if line.startswith('use '):
                    imports.append(line)
                elif line.startswith('pub mod') or line.startswith('pub fn'):
                    exports.append(line)
        
        return imports, exports
    
    def _parse_definitions(self, content: str, language: str) -> tuple[List[str], List[str]]:
        """Parse function and class definitions."""
        functions = []
        classes = []
        
        import re
        
        if language == 'python':
            # Match function definitions
            func_pattern = re.compile(r'^def\s+(\w+)\s*\(', re.MULTILINE)
            functions = func_pattern.findall(content)
            
            # Match class definitions
            class_pattern = re.compile(r'^class\s+(\w+)', re.MULTILINE)
            classes = class_pattern.findall(content)
        
        elif language in ('javascript', 'typescript'):
            # Match function definitions
            func_pattern = re.compile(r'(?:function|const|let|var)\s+(\w+)\s*[=:]?\s*(?:async\s*)?\(', re.MULTILINE)
            functions = func_pattern.findall(content)
            
            # Match class definitions
            class_pattern = re.compile(r'class\s+(\w+)', re.MULTILINE)
            classes = class_pattern.findall(content)
        
        elif language == 'rust':
            # Match function definitions
            func_pattern = re.compile(r'fn\s+(\w+)\s*\(', re.MULTILINE)
            functions = func_pattern.findall(content)
            
            # Match struct/enum definitions
            class_pattern = re.compile(r'(?:struct|enum|trait)\s+(\w+)', re.MULTILINE)
            classes = class_pattern.findall(content)
        
        return functions, classes
    
    def _extract_dependencies(self, path: Path) -> Dict[str, Any]:
        """Extract dependencies from package files."""
        deps = {}
        
        # Python requirements.txt
        req_file = path / 'requirements.txt'
        if req_file.exists():
            deps['python'] = self._parse_requirements(req_file)
        
        # Python pyproject.toml
        pyproject = path / 'pyproject.toml'
        if pyproject.exists():
            deps['pyproject'] = self._parse_pyproject(pyproject)
        
        # Node package.json
        package_json = path / 'package.json'
        if package_json.exists():
            import json
            with open(package_json) as f:
                pkg = json.load(f)
                deps['node'] = {
                    'dependencies': pkg.get('dependencies', {}),
                    'devDependencies': pkg.get('devDependencies', {})
                }
        
        # Rust Cargo.toml
        cargo_toml = path / 'Cargo.toml'
        if cargo_toml.exists():
            deps['rust'] = self._parse_cargo_toml(cargo_toml)
        
        # Go go.mod
        go_mod = path / 'go.mod'
        if go_mod.exists():
            deps['go'] = self._parse_go_mod(go_mod)
        
        return deps
    
    def _parse_requirements(self, path: Path) -> List[str]:
        """Parse requirements.txt file."""
        deps = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    deps.append(line.split('==')[0].split('>=')[0].split('<')[0])
        return deps
    
    def _parse_pyproject(self, path: Path) -> Dict[str, List[str]]:
        """Parse pyproject.toml file."""
        try:
            import tomllib
            with open(path, 'rb') as f:
                data = tomllib.load(f)
            
            deps = {}
            if 'project' in data and 'dependencies' in data['project']:
                deps['main'] = data['project']['dependencies']
            if 'project' in data and 'optional-dependencies' in data['project']:
                deps['optional'] = data['project']['optional-dependencies']
            return deps
        except Exception:
            return {}
    
    def _parse_cargo_toml(self, path: Path) -> Dict[str, Any]:
        """Parse Cargo.toml file."""
        try:
            import tomllib
            with open(path, 'rb') as f:
                data = tomllib.load(f)
            return {
                'dependencies': list(data.get('dependencies', {}).keys()),
                'dev-dependencies': list(data.get('dev-dependencies', {}).keys())
            }
        except Exception:
            return {}
    
    def _parse_go_mod(self, path: Path) -> List[str]:
        """Parse go.mod file."""
        deps = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('require '):
                    deps.append(line.split()[1])
        return deps
    
    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total
    
    def search(self, query: str, repo: Optional[str] = None) -> List[CodeIndex]:
        """Search indexed code."""
        results = []
        repos = [repo] if repo else list(self.index.keys())
        
        for r in repos:
            if r not in self.index:
                continue
            for idx in self.index[r]:
                if (query in idx.path or 
                    query in idx.content_hash or
                    any(query in imp for imp in idx.imports) or
                    any(query in exp for exp in idx.exports) or
                    any(query in func for func in idx.functions) or
                    any(query in cls for cls in idx.classes)):
                    results.append(idx)
        
        return results
    
    def get_shared_symbols(self) -> Dict[str, List[str]]:
        """Find symbols (functions, classes) shared across repos."""
        symbol_to_repos: Dict[str, Set[str]] = {}
        
        for repo_name, indices in self.index.items():
            for idx in indices:
                for symbol in idx.functions + idx.classes:
                    if symbol not in symbol_to_repos:
                        symbol_to_repos[symbol] = set()
                    symbol_to_repos[symbol].add(repo_name)
        
        # Return only symbols that appear in multiple repos
        return {
            symbol: list(repos) 
            for symbol, repos in symbol_to_repos.items() 
            if len(repos) > 1
        }
    
    def save_index(self, path: str = "repo_index.json"):
        """Save the index to a JSON file."""
        data = {
            'metadata': {k: asdict(v) for k, v in self.metadata.items()},
            'index': {
                repo: [asdict(idx) for idx in indices]
                for repo, indices in self.index.items()
            },
            'saved_at': datetime.now().isoformat()
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        console.print(f"[green]✓[/green] Index saved to {path}")
    
    def load_index(self, path: str = "repo_index.json"):
        """Load the index from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        
        self.metadata = {
            k: RepoMetadata(**v) for k, v in data['metadata'].items()
        }
        self.index = {
            repo: [CodeIndex(**idx) for idx in indices]
            for repo, indices in data['index'].items()
        }
        
        console.print(f"[green]✓[/green] Index loaded from {path}")
        console.print(f"   {len(self.index)} repositories, {sum(len(v) for v in self.index.values())} files")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed repositories."""
        stats = {
            'total_repos': len(self.index),
            'total_files': sum(len(v) for v in self.index.values()),
            'languages': {},
            'total_functions': 0,
            'total_classes': 0,
            'repos': {}
        }
        
        for repo_name, indices in self.index.items():
            repo_stats = {
                'files': len(indices),
                'languages': {},
                'functions': 0,
                'classes': 0
            }
            
            for idx in indices:
                lang = idx.language
                stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
                repo_stats['languages'][lang] = repo_stats['languages'].get(lang, 0) + 1
                repo_stats['functions'] += len(idx.functions)
                repo_stats['classes'] += len(idx.classes)
                stats['total_functions'] += len(idx.functions)
                stats['total_classes'] += len(idx.classes)
            
            stats['repos'][repo_name] = repo_stats
        
        return stats