"""Tests for the profiler."""

import pytest
import time

import sys
sys.path.insert(0, '../src')

from profiler import Profiler, ProfileResult, FunctionProfile


class TestProfiler:
    """Test cases for Profiler."""
    
    def test_initialization(self):
        """Test profiler initialization."""
        profiler = Profiler()
        assert profiler.results == []
    
    def test_profile_function(self):
        """Test profiling a simple function."""
        def test_func():
            time.sleep(0.01)
            return 42
        
        profiler = Profiler()
        result, output = profiler.profile_function(test_func)
        
        assert isinstance(result, ProfileResult)
        assert output == 42
        assert result.total_time >= 0.01
        assert len(result.functions) > 0
    
    def test_profile_with_args(self):
        """Test profiling function with arguments."""
        def test_func(a, b, c=None):
            time.sleep(0.01)
            return a + b + (c or 0)
        
        profiler = Profiler()
        result, output = profiler.profile_function(test_func, 1, 2, c=3)
        
        assert output == 6
    
    def test_get_hotspots(self):
        """Test getting performance hotspots."""
        result = ProfileResult(
            functions=[
                FunctionProfile("fast", "file.py", 1, 100, 0.01, 0.01, 0.0001),
                FunctionProfile("slow", "file.py", 5, 10, 1.0, 1.0, 0.1),
                FunctionProfile("medium", "file.py", 10, 50, 0.5, 0.5, 0.01),
            ],
            total_time=1.51,
            timestamp="2024-01-01",
            target="test"
        )
        
        hotspots = result.get_hotspots(2)
        assert len(hotspots) == 2
        assert hotspots[0].name == "slow"  # Highest cumulative time
        assert hotspots[1].name == "medium"
    
    def test_is_hotspot(self):
        """Test hotspot detection."""
        hot = FunctionProfile("hot", "file.py", 1, 10000, 0.1, 0.1, 0.00001)
        assert hot.is_hotspot
        
        not_hot = FunctionProfile("normal", "file.py", 1, 10, 0.001, 0.001, 0.0001)
        assert not not_hot.is_hotspot
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ProfileResult(
            functions=[
                FunctionProfile("func", "file.py", 1, 1, 0.1, 0.1, 0.1)
            ],
            total_time=0.1,
            timestamp="2024-01-01",
            target="test"
        )
        
        data = result.to_dict()
        assert data['target'] == "test"
        assert data['total_time'] == 0.1
        assert 'functions' in data
        assert 'hotspots' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])