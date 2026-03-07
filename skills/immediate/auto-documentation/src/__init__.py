"""
Auto-Documentation - Keeps AGENTS.md updated automatically.

This module monitors file changes in real-time and automatically
updates AGENTS.md with new features, routes, models, and changes.
"""

from .watcher import (
    DocumentationWatcher,
    AutoDocumentationManager,
    FileState,
    ChangeBatch,
    create_watcher,
    create_manager
)
from .diff import (
    DiffAnalyzer,
    CodeChange,
    ChangeType
)
from .generator import (
    AGENTSMDGenerator,
    WhatsNewGenerator,
    DocumentationSection
)

__version__ = "1.0.0"
__all__ = [
    "DocumentationWatcher",
    "AutoDocumentationManager",
    "FileState",
    "ChangeBatch",
    "DiffAnalyzer",
    "CodeChange",
    "ChangeType",
    "AGENTSMDGenerator",
    "WhatsNewGenerator",
    "DocumentationSection",
    "create_watcher",
    "create_manager",
]
