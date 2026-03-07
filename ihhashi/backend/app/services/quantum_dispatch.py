"""
Quantum Dispatch Service using D-Wave Leap API

Provides quantum-enhanced route optimization using quantum annealing.
Extends classical OR-Tools optimization with D-Wave hybrid solvers.

REQUIRES: D-Wave Leap account and API token
Set DWAVE_API_TOKEN in environment variables.
"""

import os
import math
import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Import from route_optimizer for shared data structures
from .route_optimizer import (
    DeliveryStop,
    OptimizedRoute,
    haversine_distance,
    calculate_distance_matrix
)


@dataclass
class QuantumOptimizationResult:
    """Result of quantum optimization with metadata"""
    route: OptimizedRoute
    solver_type: str  # 'quantum', 'hybrid', or 'classical_fallback'
    solve_time_ms: float
    quantum_energy: Optional[float] = None
    num_qubits: Optional[int] = None
    chain_break_fraction: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class ABTestResult:
    """A/B test comparison between quantum and classical"""
    test_id: str
    timestamp: str
    num_stops: int
    
    # Quantum results
    quantum_time_ms: float
    quantum_distance_m: float
    quantum_solve_time_ms: float
    quantum_success: bool
    
    # Classical results
    classical_time_ms: float
    classical_distance_m: float
    classical_solve_time_ms: float
    
    # Comparison
    improvement_percent: float  # Positive = quantum better
    faster_percent: float  # Time improvement
    winner: str  # 'quantum', 'classical', or 'tie'


class QuantumDispatcher:
    """
    Quantum-enhanced dispatch using D-Wave Leap API.
    
    Uses hybrid solvers for larger problems (up to 100 stops)
    and pure QPU for smaller instances.
    """
    
    def __init__(self):
        self.api_token = os.environ.get('DWAVE_API_TOKEN')
        self.solver_name = os.environ.get('DWAVE_SOLVER', 'hybrid_binary_quadratic_model_version2')
        self.enabled = bool(self.api_token)
        self._sampler = None
        
    def _get_sampler(self):
        """Lazy load D-Wave sampler"""
        if self._sampler is not None:
            return self._sampler
            
        if not self.enabled:
            logger.warning("D-Wave API token not configured. Using classical fallback.")
            return None
            
        try:
            from dwave.system import LeapHybridSolverCQMSampler
            self._sampler = LeapHybridSolverCQMSampler()
            return self._sampler
        except ImportError:
            logger.warning("dwave-system not installed. Install with: pip install dwave-system")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize D-Wave sampler: {e}")
            return None
    
    def optimize_route_quantum(
        self,
        stops: List[DeliveryStop],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float = 30.0,
        max_stops: int = 25
    ) -> QuantumOptimizationResult:
        """
        Optimize delivery route using D-Wave quantum annealing.
        
        Falls back to classical OR-Tools if quantum unavailable.
        
        Args:
            stops: List of delivery stops
            start_lat: Starting latitude
            start_lng: Starting longitude
            avg_speed_kmh: Average travel speed
            max_stops: Maximum stops (quantum scales better for 10-30)
        
        Returns:
            QuantumOptimizationResult with route and metadata
        """
        start_time = time.time()
        
        if not stops:
            return QuantumOptimizationResult(
                route=OptimizedRoute(stops=[], total_distance_m=0, total_time_minutes=0,
                                    total_service_time_minutes=0, savings_vs_original_minutes=0,
                                    confidence=0),
                solver_type='classical_fallback',
                solve_time_ms=0,
                success=False,
                error_message="No stops provided"
            )
        
        # Try quantum optimization
        if self.enabled and len(stops) <= max_stops:
            result = self._try_quantum_optimization(stops, start_lat, start_lng, avg_speed_kmh)
            if result.success:
                result.solve_time_ms = (time.time() - start_time) * 1000
                return result
        
        # Fallback to classical
        from .route_optimizer import optimize_route_vrp
        classical_route = optimize_route_vrp(stops, start_lat, start_lng, 
                                             max_stops=max_stops, avg_speed_kmh=avg_speed_kmh)
        
        return QuantumOptimizationResult(
            route=classical_route,
            solver_type='classical_fallback',
            solve_time_ms=(time.time() - start_time) * 1000,
            success=True
        )
    
    def _try_quantum_optimization(
        self,
        stops: List[DeliveryStop],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float
    ) -> QuantumOptimizationResult:
        """Attempt quantum optimization using D-Wave"""
        
        try:
            import dimod
            from dwave.system import LeapHybridSolverCQMSampler
            
            # Create distance matrix including depot
            depot = DeliveryStop(id="depot", name="Start", lat=start_lat, lng=start_lng)
            all_nodes = [depot] + stops
            
            n = len(all_nodes)
            distance_matrix = calculate_distance_matrix(all_nodes)
            
            # Build TSP QUBO using dwave-networkx approach
            # Variables: x[i,j] = 1 if node i is visited at position j
            cqm = dimod.ConstrainedQuadraticModel()
            
            # Decision variables
            x = {}
            for i in range(n):
                for j in range(n):
                    x[(i, j)] = dimod.Binary(f'x_{i}_{j}')
            
            # Objective: minimize total distance
            objective = 0
            for i in range(n):
                for k in range(n):
                    for j in range(n):
                        for l in range(n):
                            if j == (l + 1) % n or (j == 0 and l == n - 1):
                                # Adjacent positions in tour
                                objective += distance_matrix[i][k] * x[(i, j)] * x[(k, l)]
            
            cqm.set_objective(objective)
            
            # Constraint 1: Each node visited exactly once
            for i in range(n):
                cqm.add_constraint(sum(x[(i, j)] for j in range(n)) == 1, label=f'visit_{i}')
            
            # Constraint 2: Each position has exactly one node
            for j in range(n):
                cqm.add_constraint(sum(x[(i, j)] for i in range(n)) == 1, label=f'position_{j}')
            
            # Solve using hybrid solver
            sampler = self._get_sampler()
            if sampler is None:
                return self._create_fallback_result(stops, start_lat, start_lng, 
                                                   avg_speed_kmh, "Sampler not available")
            
            sampleset = sampler.sample_cqm(cqm, time_limit=5)
            
            # Extract best feasible solution
            feasible = sampleset.filter(lambda s: s.is_feasible)
            if len(feasible) == 0:
                return self._create_fallback_result(stops, start_lat, start_lng,
                                                   avg_speed_kmh, "No feasible quantum solution")
            
            best = feasible.first
            
            # Decode solution to route order
            route_order = self._decode_solution(best.sample, n)
            
            # Remove depot from route
            route_order = [i for i in route_order if i != 0]
            
            # Build optimized route
            optimized_route = self._build_route_from_order(
                route_order, all_nodes, start_lat, start_lng, avg_speed_kmh
            )
            
            return QuantumOptimizationResult(
                route=optimized_route,
                solver_type='quantum',
                solve_time_ms=0,  # Set by caller
                quantum_energy=best.energy,
                num_qubits=n * n,
                chain_break_fraction=getattr(best, 'chain_break_fraction', None),
                success=True
            )
            
        except ImportError as e:
            return self._create_fallback_result(stops, start_lat, start_lng, avg_speed_kmh,
                                               f"Missing dependency: {e}")
        except Exception as e:
            logger.error(f"Quantum optimization failed: {e}")
            return self._create_fallback_result(stops, start_lat, start_lng, avg_speed_kmh,
                                               f"Quantum error: {e}")
    
    def _decode_solution(self, sample: dict, n: int) -> List[int]:
        """Decode QUBO solution to route order"""
        route = []
        for j in range(n):
            for i in range(n):
                if sample.get(f'x_{i}_{j}', 0) == 1:
                    route.append(i)
                    break
        return route
    
    def _build_route_from_order(
        self,
        route_order: List[int],
        all_nodes: List[DeliveryStop],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float
    ) -> OptimizedRoute:
        """Build OptimizedRoute from ordered node indices"""
        
        total_distance = 0
        total_time = 0
        prev_lat, prev_lng = start_lat, start_lng
        
        optimized_stops = []
        for idx in route_order:
            stop = all_nodes[idx]
            dist = haversine_distance(prev_lat, prev_lng, stop.lat, stop.lng)
            time_minutes = dist / ((avg_speed_kmh * 1000) / 60)
            
            total_distance += dist
            total_time += time_minutes + stop.service_time_minutes
            
            optimized_stops.append({
                "id": stop.id,
                "name": stop.name,
                "lat": stop.lat,
                "lng": stop.lng,
                "distance_from_previous_m": int(dist),
                "time_from_previous_minutes": round(time_minutes, 1),
                "service_time_minutes": stop.service_time_minutes,
                "cumulative_time_minutes": round(total_time, 1),
                "priority": stop.priority
            })
            
            prev_lat, prev_lng = stop.lat, stop.lng
        
        # Calculate savings
        stops = all_nodes[1:]  # Exclude depot
        from .route_optimizer import calculate_total_time
        original_time = calculate_total_time(stops, start_lat, start_lng, avg_speed_kmh)
        savings = original_time - total_time
        
        return OptimizedRoute(
            stops=optimized_stops,
            total_distance_m=total_distance,
            total_time_minutes=round(total_time, 1),
            total_service_time_minutes=sum(s.service_time_minutes for s in stops),
            savings_vs_original_minutes=round(savings, 1),
            confidence=0.95 if len(stops) <= 15 else 0.85
        )
    
    def _create_fallback_result(
        self,
        stops: List[DeliveryStop],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float,
        error_msg: str
    ) -> QuantumOptimizationResult:
        """Create fallback result using classical optimizer"""
        from .route_optimizer import optimize_route_vrp
        
        route = optimize_route_vrp(stops, start_lat, start_lng, avg_speed_kmh=avg_speed_kmh)
        
        return QuantumOptimizationResult(
            route=route,
            solver_type='classical_fallback',
            solve_time_ms=0,
            success=False,
            error_message=error_msg
        )


# ============================================================================
# A/B TESTING INFRASTRUCTURE
# ============================================================================

class ABTestRunner:
    """
    Run A/B tests comparing quantum vs classical routing.
    
    Stores results for analysis and reports.
    """
    
    def __init__(self, results_path: str = "/tmp/quantum_ab_tests.json"):
        self.results_path = results_path
        self.results: List[Dict] = self._load_results()
    
    def _load_results(self) -> List[Dict]:
        """Load previous test results"""
        try:
            if os.path.exists(self.results_path):
                with open(self.results_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            pass
        return []
    
    def _save_results(self):
        """Save test results"""
        with open(self.results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def run_comparison(
        self,
        stops: List[DeliveryStop],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float = 30.0
    ) -> ABTestResult:
        """
        Run both quantum and classical optimization and compare.
        
        Returns detailed comparison metrics.
        """
        import uuid
        from .route_optimizer import optimize_route_vrp
        
        test_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()
        
        # Classical optimization
        classical_start = time.time()
        classical_route = optimize_route_vrp(stops, start_lat, start_lng, avg_speed_kmh)
        classical_time = (time.time() - classical_start) * 1000
        
        # Quantum optimization
        quantum_dispatcher = QuantumDispatcher()
        quantum_start = time.time()
        quantum_result = quantum_dispatcher.optimize_route_quantum(
            stops, start_lat, start_lng, avg_speed_kmh
        )
        quantum_time = (time.time() - quantum_start) * 1000
        
        # Calculate improvements
        distance_improvement = 0
        if classical_route.total_distance_m > 0:
            distance_improvement = (
                (classical_route.total_distance_m - quantum_result.route.total_distance_m) 
                / classical_route.total_distance_m * 100
            )
        
        time_improvement = 0
        if classical_route.total_time_minutes > 0:
            time_improvement = (
                (classical_route.total_time_minutes - quantum_result.route.total_time_minutes)
                / classical_route.total_time_minutes * 100
            )
        
        # Determine winner
        if distance_improvement > 2:
            winner = 'quantum'
        elif distance_improvement < -2:
            winner = 'classical'
        else:
            winner = 'tie'
        
        result = ABTestResult(
            test_id=test_id,
            timestamp=timestamp,
            num_stops=len(stops),
            quantum_time_ms=quantum_result.route.total_time_minutes * 60 * 1000,
            quantum_distance_m=quantum_result.route.total_distance_m,
            quantum_solve_time_ms=quantum_time,
            quantum_success=quantum_result.success and quantum_result.solver_type == 'quantum',
            classical_time_ms=classical_route.total_time_minutes * 60 * 1000,
            classical_distance_m=classical_route.total_distance_m,
            classical_solve_time_ms=classical_time,
            improvement_percent=round(distance_improvement, 2),
            faster_percent=round(time_improvement, 2),
            winner=winner
        )
        
        # Store result
        self.results.append(asdict(result))
        self._save_results()
        
        return result
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from all A/B tests"""
        if not self.results:
            return {"total_tests": 0}
        
        total = len(self.results)
        quantum_wins = sum(1 for r in self.results if r['winner'] == 'quantum')
        classical_wins = sum(1 for r in self.results if r['winner'] == 'classical')
        ties = sum(1 for r in self.results if r['winner'] == 'tie')
        
        avg_improvement = sum(r['improvement_percent'] for r in self.results) / total
        
        quantum_success_rate = sum(1 for r in self.results if r['quantum_success']) / total * 100
        
        return {
            "total_tests": total,
            "quantum_wins": quantum_wins,
            "classical_wins": classical_wins,
            "ties": ties,
            "quantum_win_rate": round(quantum_wins / total * 100, 1),
            "avg_improvement_percent": round(avg_improvement, 2),
            "quantum_success_rate": round(quantum_success_rate, 1)
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global instances
_quantum_dispatcher: Optional[QuantumDispatcher] = None
_ab_test_runner: Optional[ABTestRunner] = None


def get_quantum_dispatcher() -> QuantumDispatcher:
    """Get or create quantum dispatcher singleton"""
    global _quantum_dispatcher
    if _quantum_dispatcher is None:
        _quantum_dispatcher = QuantumDispatcher()
    return _quantum_dispatcher


def get_ab_test_runner() -> ABTestRunner:
    """Get or create A/B test runner singleton"""
    global _ab_test_runner
    if _ab_test_runner is None:
        _ab_test_runner = ABTestRunner()
    return _ab_test_runner


def optimize_route_quantum(
    stops: List[DeliveryStop],
    start_lat: float,
    start_lng: float,
    avg_speed_kmh: float = 30.0
) -> QuantumOptimizationResult:
    """
    Optimize route using quantum annealing (D-Wave).
    
    Falls back to classical OR-Tools if quantum unavailable.
    """
    return get_quantum_dispatcher().optimize_route_quantum(
        stops, start_lat, start_lng, avg_speed_kmh
    )


def run_quantum_ab_test(
    stops: List[DeliveryStop],
    start_lat: float,
    start_lng: float,
    avg_speed_kmh: float = 30.0
) -> ABTestResult:
    """
    Run A/B test comparing quantum vs classical routing.
    
    Returns detailed comparison metrics.
    """
    return get_ab_test_runner().run_comparison(
        stops, start_lat, start_lng, avg_speed_kmh
    )


def get_quantum_stats() -> Dict[str, Any]:
    """Get A/B test summary statistics"""
    return get_ab_test_runner().get_summary_stats()
