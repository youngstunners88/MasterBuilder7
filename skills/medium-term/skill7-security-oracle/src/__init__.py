"""Security Oracle - Proactive vulnerability detection."""

__version__ = "1.0.0"
__author__ = "RobeetsDay Team"

from .scanner import SecurityScanner, ScanResult, Vulnerability
from .reporter import SecurityReporter
from .remediator import Remediator

__all__ = [
    "SecurityScanner",
    "ScanResult",
    "Vulnerability",
    "SecurityReporter",
    "Remediator"
]