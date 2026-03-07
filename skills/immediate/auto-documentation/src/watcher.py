"""
Watcher module for auto-documentation.
Monitors file changes and triggers documentation updates.
"""

import time
import hashlib
import threading
from typing import Callable, List, Dict, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from loguru import logger

from .diff import DiffAnalyzer, CodeChange
from .generator import AGENTSMDGenerator, WhatsNewGenerator


@dataclass
class FileState:
    """Represents the state of a tracked file."""
    path: Path
    content_hash: str
    last_modified: datetime
    size: int
    
    @classmethod
    def from_path(cls, path: Path) -> 'FileState':
        """Create FileState from file path."""
        stat = path.stat()
        content = path.read_bytes()
        return cls(
            path=path,
            content_hash=hashlib.sha256(content).hexdigest(),
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size
        )


@dataclass
class ChangeBatch:
    """Batch of changes for processing."""
    changes: List[CodeChange]
    timestamp: datetime
    files_affected: Set[str]
    
    def is_significant(self) -> bool:
        """Check if batch contains significant changes."""
        return len(self.changes) > 0


class DocumentationWatcher(FileSystemEventHandler):
    """
    Watches for file changes and triggers documentation updates.
    """
    
    # File patterns to watch
    WATCH_PATTERNS = [
        '*.py', '*.js', '*.ts', '*.tsx', '*.jsx',
        '*.rs', '*.go', '*.java', '*.rb', '*.php',
        '*.yaml', '*.yml', '*.json'
    ]
    
    # Patterns to ignore
    IGNORE_PATTERNS = [
        '*.pyc', '*.pyo', '__pycache__/*',
        'node_modules/*', '.git/*', '.venv/*', 'venv/*',
        'dist/*', 'build/*', '.pytest_cache/*',
        '*.min.js', '*.bundle.js',
        '.kimi/auto-docs/*',  # Don't watch our own cache
    ]
    
    def __init__(
        self,
        project_root: Path,
        on_change: Optional[Callable[[List[CodeChange]], None]] = None,
        debounce_seconds: float = 2.0,
        batch_size: int = 10
    ):
        super().__init__()
        self.project_root = Path(project_root)
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self.batch_size = batch_size
        
        self.analyzer = DiffAnalyzer()
        self.file_states: Dict[str, FileState] = {}
        self.pending_changes: List[CodeChange] = []
        self.change_history: List[ChangeBatch] = []
        
        self._observer: Optional[Observer] = None
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = False
        
        # File content cache for diffing
        self._content_cache: Dict[str, str] = {}
    
    def start(self):
        """Start watching for file changes."""
        if self._running:
            return
        
        logger.info(f"Starting documentation watcher for {self.project_root}")
        
        # Initialize file states
        self._initialize_file_states()
        
        # Setup observer
        self._observer = Observer()
        self._observer.schedule(self, str(self.project_root), recursive=True)
        self._observer.start()
        
        self._running = True
        logger.info("Watcher started")
    
    def stop(self):
        """Stop watching for file changes."""
        if not self._running:
            return
        
        logger.info("Stopping documentation watcher")
        
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._running = False
        logger.info("Watcher stopped")
    
    def _initialize_file_states(self):
        """Initialize file state tracking."""
        logger.info("Initializing file states...")
        
        for pattern in self.WATCH_PATTERNS:
            for file_path in self.project_root.rglob(pattern):
                if not self._should_ignore(file_path):
                    try:
                        state = FileState.from_path(file_path)
                        relative_path = str(file_path.relative_to(self.project_root))
                        self.file_states[relative_path] = state
                        
                        # Cache content for diffing
                        self._content_cache[relative_path] = file_path.read_text(
                            encoding='utf-8', errors='ignore'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to initialize {file_path}: {e}")
        
        logger.info(f"Initialized {len(self.file_states)} files")
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        path_str = str(file_path)
        
        # Check ignore patterns
        for pattern in self.IGNORE_PATTERNS:
            if pattern.endswith('/*'):
                if pattern[:-2] in path_str:
                    return True
            elif pattern.startswith('*'):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        
        # Skip hidden files
        if any(part.startswith('.') for part in file_path.parts):
            return True
        
        return False
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._should_ignore(file_path):
            return
        
        relative_path = str(file_path.relative_to(self.project_root))
        
        try:
            # Get old content
            old_content = self._content_cache.get(relative_path)
            
            # Get new content
            new_content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Analyze changes
            changes = self.analyzer.analyze_file_changes(
                file_path, old_content, new_content
            )
            
            with self._lock:
                self.pending_changes.extend(changes)
                self._content_cache[relative_path] = new_content
            
            # Debounce processing
            self._debounce_process()
            
        except Exception as e:
            logger.error(f"Error processing change for {file_path}: {e}")
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._should_ignore(file_path):
            return
        
        relative_path = str(file_path.relative_to(self.project_root))
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Analyze as new file
            changes = self.analyzer.analyze_file_changes(file_path, None, content)
            
            with self._lock:
                self.pending_changes.extend(changes)
                self._content_cache[relative_path] = content
            
            self._debounce_process()
            
        except Exception as e:
            logger.error(f"Error processing creation for {file_path}: {e}")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        relative_path = str(file_path.relative_to(self.project_root))
        
        # Create a removal change
        change = CodeChange(
            file_path=relative_path,
            change_type=__import__('src.diff', fromlist=['ChangeType']).ChangeType.REMOVED,
            element_type='file',
            name=file_path.name,
            description=f"File deleted: {relative_path}"
        )
        
        with self._lock:
            self.pending_changes.append(change)
            self._content_cache.pop(relative_path, None)
        
        self._debounce_process()
    
    def _debounce_process(self):
        """Debounce change processing."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = threading.Timer(
            self.debounce_seconds,
            self._process_pending_changes
        )
        self._debounce_timer.start()
    
    def _process_pending_changes(self):
        """Process pending changes."""
        with self._lock:
            changes = self.pending_changes.copy()
            self.pending_changes.clear()
        
        if not changes:
            return
        
        logger.info(f"Processing {len(changes)} pending changes")
        
        # Create batch
        batch = ChangeBatch(
            changes=changes,
            timestamp=datetime.now(),
            files_affected=set(c.file_path for c in changes)
        )
        
        self.change_history.append(batch)
        
        # Trim history
        if len(self.change_history) > 100:
            self.change_history = self.change_history[-100:]
        
        # Trigger callback
        if self.on_change:
            try:
                self.on_change(changes)
            except Exception as e:
                logger.error(f"Error in on_change callback: {e}")
    
    def get_change_history(self, n: int = 10) -> List[ChangeBatch]:
        """Get recent change history."""
        return self.change_history[-n:]
    
    def get_all_changes(self) -> List[CodeChange]:
        """Get all changes from history."""
        changes = []
        for batch in self.change_history:
            changes.extend(batch.changes)
        return changes
    
    def get_stats(self) -> Dict[str, Any]:
        """Get watcher statistics."""
        return {
            'files_tracked': len(self.file_states),
            'pending_changes': len(self.pending_changes),
            'change_batches': len(self.change_history),
            'total_changes': sum(len(b.changes) for b in self.change_history),
            'is_running': self._running,
        }
    
    def force_process(self):
        """Force immediate processing of pending changes."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._process_pending_changes()


class AutoDocumentationManager:
    """
    Manages automatic documentation updates.
    Combines watching with generation.
    """
    
    def __init__(
        self,
        project_root: Path,
        agents_md_path: Optional[Path] = None,
        auto_update: bool = True,
        update_interval: int = 60  # seconds
    ):
        self.project_root = Path(project_root)
        self.agents_md_path = agents_md_path or (self.project_root / "AGENTS.md")
        self.auto_update = auto_update
        self.update_interval = update_interval
        
        self.watcher = DocumentationWatcher(
            project_root=self.project_root,
            on_change=self._on_changes_detected
        )
        self.generator = AGENTSMDGenerator(self.project_root)
        self.whats_new_gen = WhatsNewGenerator()
        
        self._update_timer: Optional[threading.Timer] = None
        self._last_update = datetime.now()
        self._accumulated_changes: List[CodeChange] = []
    
    def start(self):
        """Start auto-documentation."""
        logger.info("Starting Auto-Documentation Manager")
        
        self.watcher.start()
        
        # Schedule periodic updates
        if self.auto_update:
            self._schedule_update()
    
    def stop(self):
        """Stop auto-documentation."""
        logger.info("Stopping Auto-Documentation Manager")
        
        self.watcher.stop()
        
        if self._update_timer:
            self._update_timer.cancel()
    
    def _on_changes_detected(self, changes: List[CodeChange]):
        """Handle detected changes."""
        self._accumulated_changes.extend(changes)
        
        # Check if we should update immediately
        critical_changes = [c for c in changes if c.impact_level == 'critical']
        if critical_changes:
            self._update_documentation()
    
    def _schedule_update(self):
        """Schedule next documentation update."""
        self._update_documentation()
        
        self._update_timer = threading.Timer(
            self.update_interval,
            self._schedule_update
        )
        self._update_timer.daemon = True
        self._update_timer.start()
    
    def _update_documentation(self):
        """Update documentation with accumulated changes."""
        if not self._accumulated_changes:
            return
        
        changes = self._accumulated_changes.copy()
        self._accumulated_changes.clear()
        
        logger.info(f"Updating documentation with {len(changes)} changes")
        
        try:
            # Update AGENTS.md
            content = self.generator.update(changes)
            self.generator.save(content, self.agents_md_path)
            
            # Generate What's New
            whats_new = self.whats_new_gen.generate(changes)
            whats_new_path = self.project_root / ".kimi" / "WHATS_NEW.md"
            whats_new_path.parent.mkdir(parents=True, exist_ok=True)
            whats_new_path.write_text(whats_new, encoding='utf-8')
            
            self._last_update = datetime.now()
            logger.info("Documentation updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update documentation: {e}")
            # Restore changes for retry
            self._accumulated_changes.extend(changes)
    
    def force_update(self):
        """Force immediate documentation update."""
        self.watcher.force_process()
        self._update_documentation()
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status."""
        return {
            'watcher_stats': self.watcher.get_stats(),
            'accumulated_changes': len(self._accumulated_changes),
            'last_update': self._last_update.isoformat(),
            'agents_md_path': str(self.agents_md_path),
            'agents_md_exists': self.agents_md_path.exists(),
        }
    
    def generate_initial(self):
        """Generate initial AGENTS.md."""
        logger.info("Generating initial AGENTS.md")
        
        content = self.generator.generate([])
        self.generator.save(content, self.agents_md_path)
        
        logger.info(f"Initial AGENTS.md created at {self.agents_md_path}")


def create_watcher(
    project_root: str | Path,
    **kwargs
) -> DocumentationWatcher:
    """
    Factory function to create a DocumentationWatcher.
    
    Args:
        project_root: Project root directory
        **kwargs: Additional arguments for DocumentationWatcher
        
    Returns:
        Configured DocumentationWatcher instance
    """
    return DocumentationWatcher(
        project_root=Path(project_root),
        **kwargs
    )


def create_manager(
    project_root: str | Path,
    **kwargs
) -> AutoDocumentationManager:
    """
    Factory function to create an AutoDocumentationManager.
    
    Args:
        project_root: Project root directory
        **kwargs: Additional arguments for AutoDocumentationManager
        
    Returns:
        Configured AutoDocumentationManager instance
    """
    return AutoDocumentationManager(
        project_root=Path(project_root),
        **kwargs
    )
