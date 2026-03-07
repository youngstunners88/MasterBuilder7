"""
Analyzer module for self-healing tests.
Analyzes test failures and identifies patterns.
"""

import re
import ast
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from collections import defaultdict
import hashlib
from loguru import logger


class FailureType(Enum):
    """Types of test failures."""
    ASSERTION_ERROR = auto()
    TIMEOUT = auto()
    RACE_CONDITION = auto()
    MOCK_ISSUE = auto()
    ASYNC_ISSUE = auto()
    FIXTURE_ISSUE = auto()
    ENVIRONMENT = auto()
    DEPENDENCY = auto()
    UNKNOWN = auto()


class FlakinessPattern(Enum):
    """Patterns indicating flakiness."""
    TIMING_DEPENDENT = auto()
    ORDER_DEPENDENT = auto()
    STATE_LEAKAGE = auto()
    EXTERNAL_DEPENDENCY = auto()
    RANDOM_DATA = auto()
    CONCURRENCY = auto()
    RESOURCE_CONTENTION = auto()


@dataclass
class FailureInstance:
    """Single test failure instance."""
    test_name: str
    test_file: str
    error_type: str
    error_message: str
    traceback: str
    line_number: Optional[int]
    duration: float
    timestamp: float
    
    def get_signature(self) -> str:
        """Get unique signature for this failure."""
        content = f"{self.test_name}:{self.error_type}:{self.error_message[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class TestAnalysis:
    """Analysis of a flaky test."""
    test_name: str
    test_file: str
    failure_type: FailureType
    flakiness_patterns: List[FlakinessPattern]
    confidence: float  # 0-1
    suggested_fixes: List[Dict[str, Any]]
    failure_count: int
    pass_count: int
    failure_instances: List[FailureInstance]
    
    @property
    def flakiness_rate(self) -> float:
        """Calculate flakiness rate."""
        total = self.failure_count + self.pass_count
        if total == 0:
            return 0.0
        return self.failure_count / total


class FailureAnalyzer:
    """Analyzes test failures to identify patterns."""
    
    # Patterns for identifying failure types
    ERROR_PATTERNS = {
        FailureType.TIMEOUT: [
            r'timeout|timed out|TimeLimitExceeded|DeadlineExceeded',
            r'function timed out after',
        ],
        FailureType.RACE_CONDITION: [
            r'race condition|concurrent|thread|asyncio|deadlock',
            r'Lock|Semaphore|Barrier',
        ],
        FailureType.MOCK_ISSUE: [
            r'mock|Mock|MagicMock|patch|assert_called',
            r'not called|called with wrong',
        ],
        FailureType.ASYNC_ISSUE: [
            r'async|await|coroutine|event loop|Task',
            r'was never awaited|coroutine .* was never awaited',
        ],
        FailureType.FIXTURE_ISSUE: [
            r'fixture.*not found|Fixture .* not found',
            r'setup.*failed|teardown.*failed',
        ],
        FailureType.ENVIRONMENT: [
            r'environment|env|PATH|HOME|variable',
            r'FileNotFoundError|PermissionError',
        ],
        FailureType.DEPENDENCY: [
            r'ImportError|ModuleNotFoundError|No module named',
            r'ConnectionError|Connection refused|Connection reset',
        ],
    }
    
    # Patterns for identifying flakiness
    FLAKINESS_INDICATORS = {
        FlakinessPattern.TIMING_DEPENDENT: [
            r'time\.sleep|asyncio\.sleep|threading\.Timer',
            r'datetime\.now|time\.time',
            r'scheduler|cron|interval',
        ],
        FlakinessPattern.ORDER_DEPENDENT: [
            r'global|static|shared',
            r'@pytest\.mark\.order',
            r'\.append\(|\.extend\(',
        ],
        FlakinessPattern.STATE_LEAKAGE: [
            r'@pytest\.fixture.*scope=["\']session["\']',
            r'@pytest\.fixture.*scope=["\']module["\']',
            r'global\s+\w+',
        ],
        FlakinessPattern.EXTERNAL_DEPENDENCY: [
            r'requests\.|urllib|http\.client',
            r'database|db\.|connection|cursor',
            r'redis|kafka|rabbitmq',
        ],
        FlakinessPattern.RANDOM_DATA: [
            r'random|uuid|faker',
            r'secrets|token',
        ],
        FlakinessPattern.CONCURRENCY: [
            r'threading|multiprocessing|asyncio|concurrent',
            r'Pool|ThreadPool|ProcessPool',
        ],
        FlakinessPattern.RESOURCE_CONTENTION: [
            r'open\(|file\(|tempfile',
            r'socket|port|bind',
            r'lock|Lock|RLock',
        ],
    }
    
    def __init__(self):
        self.failure_history: Dict[str, List[FailureInstance]] = defaultdict(list)
        self.analyzed_tests: Dict[str, TestAnalysis] = {}
    
    def record_failure(
        self,
        test_name: str,
        test_file: str,
        error_type: str,
        error_message: str,
        traceback: str,
        duration: float,
        timestamp: float
    ) -> FailureInstance:
        """Record a test failure."""
        instance = FailureInstance(
            test_name=test_name,
            test_file=test_file,
            error_type=error_type,
            error_message=error_message,
            traceback=traceback,
            line_number=self._extract_line_number(traceback),
            duration=duration,
            timestamp=timestamp
        )
        
        key = f"{test_file}::{test_name}"
        self.failure_history[key].append(instance)
        
        logger.debug(f"Recorded failure for {key}: {error_type}")
        return instance
    
    def record_success(self, test_name: str, test_file: str, duration: float):
        """Record a test success (for flakiness calculation)."""
        key = f"{test_file}::{test_name}"
        
        # Store success as a special failure instance
        instance = FailureInstance(
            test_name=test_name,
            test_file=test_file,
            error_type="SUCCESS",
            error_message="",
            traceback="",
            line_number=None,
            duration=duration,
            timestamp=__import__('time').time()
        )
        
        self.failure_history[key].append(instance)
    
    def analyze_test(self, test_name: str, test_file: str) -> Optional[TestAnalysis]:
        """
        Analyze a test for flakiness patterns.
        
        Args:
            test_name: Name of the test
            test_file: Path to test file
            
        Returns:
            TestAnalysis if test is flaky, None otherwise
        """
        key = f"{test_file}::{test_name}"
        instances = self.failure_history.get(key, [])
        
        if len(instances) < 2:
            return None  # Not enough data
        
        # Count failures vs successes
        failures = [i for i in instances if i.error_type != "SUCCESS"]
        successes = [i for i in instances if i.error_type == "SUCCESS"]
        
        if len(failures) < 1:
            return None  # Test always passes
        
        # Check if flaky (both passes and fails)
        flakiness_rate = len(failures) / len(instances)
        if flakiness_rate < 0.1 or flakiness_rate > 0.9:
            # Either almost always passes or almost always fails
            # (not flaky in the traditional sense)
            pass
        
        # Determine failure type
        failure_type = self._determine_failure_type(failures)
        
        # Detect flakiness patterns
        patterns = self._detect_flakiness_patterns(test_file, test_name)
        
        # Calculate confidence
        confidence = self._calculate_confidence(failures, successes, patterns)
        
        # Generate suggested fixes
        suggested_fixes = self._suggest_fixes(failure_type, patterns, test_file, test_name)
        
        analysis = TestAnalysis(
            test_name=test_name,
            test_file=test_file,
            failure_type=failure_type,
            flakiness_patterns=patterns,
            confidence=confidence,
            suggested_fixes=suggested_fixes,
            failure_count=len(failures),
            pass_count=len(successes),
            failure_instances=failures
        )
        
        self.analyzed_tests[key] = analysis
        
        return analysis
    
    def get_flaky_tests(self, threshold: float = 0.1) -> List[TestAnalysis]:
        """
        Get all tests identified as flaky.
        
        Args:
            threshold: Minimum flakiness rate to consider flaky
            
        Returns:
            List of flaky test analyses
        """
        flaky = []
        
        for key, analysis in self.analyzed_tests.items():
            if analysis.flakiness_rate >= threshold:
                flaky.append(analysis)
        
        # Sort by flakiness rate (descending)
        flaky.sort(key=lambda x: x.flakiness_rate, reverse=True)
        
        return flaky
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        total_tests = len(self.failure_history)
        total_failures = sum(
            len([i for i in instances if i.error_type != "SUCCESS"])
            for instances in self.failure_history.values()
        )
        flaky_tests = len(self.get_flaky_tests())
        
        return {
            'total_tests_tracked': total_tests,
            'total_failure_instances': total_failures,
            'flaky_tests_detected': flaky_tests,
            'tests_analyzed': len(self.analyzed_tests),
        }
    
    def _extract_line_number(self, traceback: str) -> Optional[int]:
        """Extract line number from traceback."""
        import re
        
        # Look for patterns like "File "...", line 42"
        match = re.search(r'File "[^"]+", line (\d+)', traceback)
        if match:
            return int(match.group(1))
        
        return None
    
    def _determine_failure_type(self, failures: List[FailureInstance]) -> FailureType:
        """Determine the primary failure type."""
        if not failures:
            return FailureType.UNKNOWN
        
        # Count occurrences of each error type
        type_counts: Dict[FailureType, int] = defaultdict(int)
        
        for failure in failures:
            error_lower = failure.error_message.lower()
            
            for failure_type, patterns in self.ERROR_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, error_lower, re.IGNORECASE):
                        type_counts[failure_type] += 1
                        break
        
        # Return most common
        if type_counts:
            return max(type_counts.items(), key=lambda x: x[1])[0]
        
        return FailureType.ASSERTION_ERROR  # Default
    
    def _detect_flakiness_patterns(
        self,
        test_file: str,
        test_name: str
    ) -> List[FlakinessPattern]:
        """Detect flakiness patterns in test code."""
        patterns = []
        
        try:
            file_path = Path(test_file)
            if not file_path.exists():
                return patterns
            
            content = file_path.read_text(encoding='utf-8')
            
            # Find test function
            test_pattern = rf'def\s+{re.escape(test_name)}\s*\([^)]*\):([\s\S]*?)(?=\ndef\s+|\Z)'
            match = re.search(test_pattern, content)
            
            if not match:
                return patterns
            
            test_code = match.group(1)
            
            # Check each pattern
            for pattern_type, regexes in self.FLAKINESS_INDICATORS.items():
                for regex in regexes:
                    if re.search(regex, test_code):
                        patterns.append(pattern_type)
                        break
        
        except Exception as e:
            logger.warning(f"Error detecting patterns: {e}")
        
        return list(set(patterns))  # Remove duplicates
    
    def _calculate_confidence(
        self,
        failures: List[FailureInstance],
        successes: List[FailureInstance],
        patterns: List[FlakinessPattern]
    ) -> float:
        """Calculate confidence that test is flaky."""
        total = len(failures) + len(successes)
        if total < 2:
            return 0.0
        
        # Base confidence on flakiness rate
        flakiness_rate = len(failures) / total
        
        # Ideal flakiness is around 0.5 (sometimes passes, sometimes fails)
        # Rate close to 0.5 = higher confidence
        rate_confidence = 1.0 - abs(0.5 - flakiness_rate) * 2
        
        # Pattern confidence
        pattern_confidence = min(len(patterns) * 0.15, 0.4)
        
        # Sample size confidence
        sample_confidence = min(total / 10, 1.0) * 0.2
        
        return min(rate_confidence + pattern_confidence + sample_confidence, 1.0)
    
    def _suggest_fixes(
        self,
        failure_type: FailureType,
        patterns: List[FlakinessPattern],
        test_file: str,
        test_name: str
    ) -> List[Dict[str, Any]]:
        """Generate suggested fixes."""
        fixes = []
        
        # Timing-related fixes
        if FlakinessPattern.TIMING_DEPENDENT in patterns:
            fixes.append({
                'type': 'timing',
                'description': 'Replace time.sleep with proper synchronization',
                'suggestion': 'Use asyncio.Event, threading.Condition, or proper wait conditions',
                'confidence': 0.8,
            })
        
        # External dependency fixes
        if FlakinessPattern.EXTERNAL_DEPENDENCY in patterns:
            fixes.append({
                'type': 'mocking',
                'description': 'Mock external dependencies',
                'suggestion': 'Use @patch or @responses for HTTP, @mock for database',
                'confidence': 0.9,
            })
        
        # State leakage fixes
        if FlakinessPattern.STATE_LEAKAGE in patterns:
            fixes.append({
                'type': 'isolation',
                'description': 'Ensure test isolation',
                'suggestion': 'Use function-scoped fixtures, reset state in setup/teardown',
                'confidence': 0.85,
            })
        
        # Order dependency fixes
        if FlakinessPattern.ORDER_DEPENDENT in patterns:
            fixes.append({
                'type': 'ordering',
                'description': 'Remove order dependency',
                'suggestion': 'Avoid global state, make tests independent',
                'confidence': 0.75,
            })
        
        # Concurrency fixes
        if FlakinessPattern.CONCURRENCY in patterns:
            fixes.append({
                'type': 'async',
                'description': 'Fix async/await issues',
                'suggestion': 'Use pytest-asyncio, ensure proper event loop handling',
                'confidence': 0.8,
            })
        
        # Failure-specific fixes
        if failure_type == FailureType.TIMEOUT:
            fixes.append({
                'type': 'timeout',
                'description': 'Increase timeout or optimize test',
                'suggestion': 'Use @pytest.mark.timeout with higher value or @pytest.mark.flaky',
                'confidence': 0.7,
            })
        
        if failure_type == FailureType.MOCK_ISSUE:
            fixes.append({
                'type': 'mock_assertion',
                'description': 'Fix mock assertions',
                'suggestion': 'Check mock call order, use assert_any_call for unordered calls',
                'confidence': 0.85,
            })
        
        # Sort by confidence
        fixes.sort(key=lambda x: x['confidence'], reverse=True)
        
        return fixes[:5]  # Return top 5


class TestCodeAnalyzer:
    """Analyzes test code structure using AST."""
    
    def __init__(self):
        self.parsed_files: Dict[str, ast.Module] = {}
    
    def parse_file(self, file_path: Path) -> Optional[ast.Module]:
        """Parse a Python test file."""
        path_str = str(file_path)
        
        if path_str in self.parsed_files:
            return self.parsed_files[path_str]
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            self.parsed_files[path_str] = tree
            return tree
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None
    
    def find_test_function(
        self,
        tree: ast.Module,
        test_name: str
    ) -> Optional[ast.FunctionDef]:
        """Find a test function in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == test_name:
                return node
        return None
    
    def analyze_test_dependencies(self, test_func: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze what the test depends on."""
        dependencies = {
            'fixtures': [],
            'imports': [],
            'external_calls': [],
            'has_sleep': False,
            'has_async': False,
            'has_random': False,
        }
        
        for node in ast.walk(test_func):
            # Check for fixtures (function arguments)
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if not arg.arg.startswith('_'):
                        dependencies['fixtures'].append(arg.arg)
            
            # Check for time.sleep
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'sleep':
                        dependencies['has_sleep'] = True
                
                # Check for external calls
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['requests', 'urllib', 'http']:
                        dependencies['external_calls'].append(node.func.id)
            
            # Check for async/await
            if isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
                dependencies['has_async'] = True
            
            # Check for random
            if isinstance(node, ast.Name):
                if node.id in ['random', 'uuid', 'faker']:
                    dependencies['has_random'] = True
        
        return dependencies
