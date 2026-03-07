"""Tests for analyzer module."""

import pytest
from pathlib import Path
import tempfile

from src.analyzer import (
    FailureAnalyzer,
    FailureInstance,
    TestAnalysis,
    FailureType,
    FlakinessPattern,
    TestCodeAnalyzer
)


class TestFailureInstance:
    """Test FailureInstance dataclass."""
    
    def test_creation(self):
        instance = FailureInstance(
            test_name="test_login",
            test_file="test_auth.py",
            error_type="AssertionError",
            error_message="assert failed",
            traceback="traceback...",
            line_number=42,
            duration=1.5,
            timestamp=1234567890
        )
        
        assert instance.test_name == "test_login"
        assert instance.line_number == 42
    
    def test_get_signature(self):
        instance = FailureInstance(
            test_name="test_login",
            test_file="test_auth.py",
            error_type="AssertionError",
            error_message="assert 1 == 2",
            traceback="",
            line_number=None,
            duration=0,
            timestamp=0
        )
        
        sig = instance.get_signature()
        assert len(sig) == 16
        assert isinstance(sig, str)


class TestFailureAnalyzer:
    """Test FailureAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        return FailureAnalyzer()
    
    def test_record_failure(self, analyzer):
        instance = analyzer.record_failure(
            test_name="test_login",
            test_file="test_auth.py",
            error_type="AssertionError",
            error_message="assert failed",
            traceback="...",
            duration=1.0,
            timestamp=1234567890
        )
        
        assert isinstance(instance, FailureInstance)
        key = "test_auth.py::test_login"
        assert len(analyzer.failure_history[key]) == 1
    
    def test_record_success(self, analyzer):
        analyzer.record_success("test_login", "test_auth.py", 0.5)
        
        key = "test_auth.py::test_login"
        assert len(analyzer.failure_history[key]) == 1
        assert analyzer.failure_history[key][0].error_type == "SUCCESS"
    
    def test_analyze_test_not_enough_data(self, analyzer):
        # Need at least 2 runs
        result = analyzer.analyze_test("test_login", "test_auth.py")
        assert result is None
    
    def test_analyze_test_flaky(self, analyzer):
        # Record mixed results
        for _ in range(3):
            analyzer.record_failure(
                "test_login", "test_auth.py",
                "AssertionError", "fail", "", 1.0, 1234567890
            )
        for _ in range(3):
            analyzer.record_success("test_login", "test_auth.py", 0.5)
        
        analysis = analyzer.analyze_test("test_login", "test_auth.py")
        
        assert analysis is not None
        assert analysis.test_name == "test_login"
        assert analysis.flakiness_rate == 0.5
        assert analysis.failure_count == 3
        assert analysis.pass_count == 3
    
    def test_determine_failure_type_timeout(self, analyzer):
        failures = [
            FailureInstance(
                "test", "file.py", "Error",
                "function timed out after 30 seconds", "",
                None, 0, 0
            )
        ]
        
        failure_type = analyzer._determine_failure_type(failures)
        assert failure_type == FailureType.TIMEOUT
    
    def test_determine_failure_type_mock(self, analyzer):
        failures = [
            FailureInstance(
                "test", "file.py", "Error",
                "Mock not called", "",
                None, 0, 0
            )
        ]
        
        failure_type = analyzer._determine_failure_type(failures)
        assert failure_type == FailureType.MOCK_ISSUE
    
    def test_calculate_confidence(self, analyzer):
        failures = [FailureInstance("t", "f.py", "E", "", "", None, 0, 0)] * 5
        successes = [FailureInstance("t", "f.py", "SUCCESS", "", "", None, 0, 0)] * 5
        patterns = [FlakinessPattern.TIMING_DEPENDENT]
        
        confidence = analyzer._calculate_confidence(failures, successes, patterns)
        
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # Should be fairly confident with 50% failure rate
    
    def test_get_stats_empty(self, analyzer):
        stats = analyzer.get_stats()
        assert stats['total_tests_tracked'] == 0
        assert stats['total_failure_instances'] == 0
    
    def test_get_stats_with_data(self, analyzer):
        analyzer.record_failure("t1", "f.py", "E", "msg", "", 1, 0)
        analyzer.record_failure("t1", "f.py", "E", "msg", "", 1, 0)
        analyzer.record_failure("t2", "f.py", "E", "msg", "", 1, 0)
        
        stats = analyzer.get_stats()
        assert stats['total_tests_tracked'] == 2
        assert stats['total_failure_instances'] == 3


class TestTestCodeAnalyzer:
    """Test TestCodeAnalyzer class."""
    
    @pytest.fixture
    def code_analyzer(self):
        return TestCodeAnalyzer()
    
    def test_parse_file(self, code_analyzer):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def test_example():
    assert True
""")
            f.flush()
            path = Path(f.name)
        
        try:
            tree = code_analyzer.parse_file(path)
            assert tree is not None
            assert path in code_analyzer.parsed_files
        finally:
            path.unlink()
    
    def test_find_test_function(self, code_analyzer):
        code = """
def test_login():
    assert True

def other_func():
    pass
"""
        tree = __import__('ast').parse(code)
        func = code_analyzer.find_test_function(tree, "test_login")
        
        assert func is not None
        assert func.name == "test_login"
    
    def test_analyze_test_dependencies(self, code_analyzer):
        code = """
def test_with_deps(mock_db):
    import time
    time.sleep(1)
    requests.get("/api")
"""
        tree = __import__('ast').parse(code)
        func = code_analyzer.find_test_function(tree, "test_with_deps")
        
        deps = code_analyzer.analyze_test_dependencies(func)
        
        assert deps['has_sleep'] is True
        assert 'requests' in deps['external_calls']
        assert 'mock_db' in deps['fixtures']
