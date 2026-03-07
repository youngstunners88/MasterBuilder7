"""
Autonomous Refactoring Agent: Continuously improves codebase.

Identifies code smells, applies refactorings, and maintains refactoring history.
"""

from .detector import CodeSmellDetector, SmellType
from .refactorer import Refactorer, Refactoring
from .validator import RefactoringValidator
from .pr_creator import PRCreator

__version__ = "1.0.0"
__all__ = [
    "CodeSmellDetector",
    "SmellType", 
    "Refactorer",
    "Refactoring",
    "RefactoringValidator",
    "PRCreator",
]
