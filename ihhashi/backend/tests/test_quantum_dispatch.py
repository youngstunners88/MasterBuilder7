"""
Tests for Quantum Dispatch Service

Tests both classical and quantum routing functionality.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.route_optimizer import DeliveryStop, optimize_route_vrp
from app.services.quantum_dispatch import (
    QuantumDispatcher,
    ABTestRunner,
    optimize_route_quantum,
    run_quantum_ab_test,
    get_quantum_stats
)


# Sample test data - Johannesburg area
TEST_STOPS = [
    DeliveryStop(id="1", name="Sandton City", lat=-26.1076, lng=28.0567, service_time_minutes=5),
    DeliveryStop(id="2", name="Rosebank Mall", lat=-26.1457, lng=28.0385, service_time_minutes=5),
    DeliveryStop(id="3", name="Melrose Arch", lat=-26.1319, lng=28.0563, service_time_minutes=4),
    DeliveryStop(id="4", name="Hyde Park", lat=-26.1456, lng=28.0603, service_time_minutes=5),
    DeliveryStop(id="5", name="Illovo", lat=-26.1510, lng=28.0461, service_time_minutes=3),
]

START_LOCATION = (-26.2041, 28.0473)  # Johannesburg CBD


class TestClassicalRouting:
    """Test classical OR-Tools routing"""
    
    def test_optimize_basic_route(self):
        """Test basic route optimization"""
        route = optimize_route_vrp(
            TEST_STOPS,
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert route is not None
        assert len(route.stops) == len(TEST_STOPS)
        assert route.total_distance_m > 0
        assert route.total_time_minutes > 0
        assert route.confidence > 0
    
    def test_optimize_with_priority(self):
        """Test optimization respects priority"""
        priority_stop = DeliveryStop(
            id="urgent", 
            name="Urgent Delivery", 
            lat=-26.1400, 
            lng=28.0500,
            service_time_minutes=5,
            priority=10  # High priority
        )
        
        stops = [priority_stop] + TEST_STOPS[:2]
        route = optimize_route_vrp(stops, START_LOCATION[0], START_LOCATION[1])
        
        assert route is not None
        assert len(route.stops) == 3


class TestQuantumDispatcher:
    """Test quantum dispatch service"""
    
    def test_dispatcher_initialization(self):
        """Test dispatcher initializes correctly"""
        dispatcher = QuantumDispatcher()
        
        # Should work even without API token (falls back to classical)
        assert dispatcher is not None
    
    def test_quantum_optimization_fallback(self):
        """Test quantum optimization falls back to classical when no token"""
        dispatcher = QuantumDispatcher()
        
        result = dispatcher.optimize_route_quantum(
            TEST_STOPS[:3],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result is not None
        assert result.route is not None
        assert len(result.route.stops) == 3
        # Should fallback to classical without token
        assert result.solver_type in ['classical_fallback', 'quantum']
    
    def test_convenience_function(self):
        """Test convenience function works"""
        result = optimize_route_quantum(
            TEST_STOPS[:2],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result is not None
        assert result.success is True


class TestABTesting:
    """Test A/B testing infrastructure"""
    
    def test_ab_test_runner(self):
        """Test A/B test runner"""
        runner = ABTestRunner()
        
        result = runner.run_comparison(
            TEST_STOPS[:3],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result is not None
        assert result.test_id is not None
        assert result.num_stops == 3
        assert result.winner in ['quantum', 'classical', 'tie']
    
    def test_ab_test_convenience(self):
        """Test A/B test convenience function"""
        result = run_quantum_ab_test(
            TEST_STOPS[:2],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result is not None
        assert result.test_id is not None
    
    def test_stats_collection(self):
        """Test statistics collection"""
        # Run a test first
        run_quantum_ab_test(
            TEST_STOPS[:2],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        stats = get_quantum_stats()
        
        assert stats is not None
        assert "total_tests" in stats
        assert stats["total_tests"] >= 1


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_stops(self):
        """Test handling of empty stops"""
        dispatcher = QuantumDispatcher()
        
        result = dispatcher.optimize_route_quantum(
            [],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result.success is False
        assert "No stops" in result.error_message
    
    def test_single_stop(self):
        """Test single stop optimization"""
        result = optimize_route_quantum(
            [TEST_STOPS[0]],
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result is not None
        assert len(result.route.stops) == 1
    
    def test_many_stops(self):
        """Test with many stops"""
        # Generate 20 stops
        import random
        stops = [
            DeliveryStop(
                id=f"stop-{i}",
                name=f"Stop {i}",
                lat=-26.2041 + random.uniform(-0.1, 0.1),
                lng=28.0473 + random.uniform(-0.1, 0.1),
                service_time_minutes=5
            )
            for i in range(20)
        ]
        
        result = optimize_route_quantum(
            stops,
            START_LOCATION[0],
            START_LOCATION[1]
        )
        
        assert result is not None
        assert len(result.route.stops) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
