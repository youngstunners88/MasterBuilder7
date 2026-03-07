"""
Quantum Dispatch API Endpoints

Provides endpoints for:
- Quantum route optimization
- A/B testing quantum vs classical
- Performance statistics
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..services.quantum_dispatch import (
    optimize_route_quantum,
    run_quantum_ab_test,
    get_quantum_stats,
    QuantumDispatcher,
    ABTestRunner
)
from ..services.route_optimizer import DeliveryStop

router = APIRouter(prefix="/api/v1/quantum-dispatch", tags=["quantum-dispatch"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StopModel(BaseModel):
    """Single delivery stop"""
    id: str
    name: str
    lat: float
    lng: float
    time_window_start: Optional[int] = None
    time_window_end: Optional[int] = None
    service_time_minutes: int = 5
    priority: int = 0


class OptimizeRequest(BaseModel):
    """Request for route optimization"""
    stops: List[StopModel]
    start_lat: float
    start_lng: float
    avg_speed_kmh: float = 30.0


class ABTestRequest(BaseModel):
    """Request for A/B test"""
    stops: List[StopModel]
    start_lat: float
    start_lng: float
    avg_speed_kmh: float = 30.0


class StopResponse(BaseModel):
    """Stop in optimized route"""
    id: str
    name: str
    lat: float
    lng: float
    distance_from_previous_m: int
    time_from_previous_minutes: float
    service_time_minutes: int
    cumulative_time_minutes: float
    priority: int


class RouteResponse(BaseModel):
    """Optimized route response"""
    stops: List[StopResponse]
    total_distance_m: float
    total_time_minutes: float
    total_service_time_minutes: float
    savings_vs_original_minutes: float
    confidence: float
    solver_type: str
    solve_time_ms: float
    quantum_energy: Optional[float] = None
    success: bool
    error_message: Optional[str] = None


class ABTestResponse(BaseModel):
    """A/B test comparison response"""
    test_id: str
    timestamp: str
    num_stops: int
    quantum_distance_m: float
    quantum_time_minutes: float
    quantum_solve_time_ms: float
    quantum_success: bool
    classical_distance_m: float
    classical_time_minutes: float
    classical_solve_time_ms: float
    improvement_percent: float
    faster_percent: float
    winner: str


class StatsResponse(BaseModel):
    """A/B test statistics"""
    total_tests: int
    quantum_wins: int
    classical_wins: int
    ties: int
    quantum_win_rate: float
    avg_improvement_percent: float
    quantum_success_rate: float


class StatusResponse(BaseModel):
    """Quantum dispatcher status"""
    enabled: bool
    api_token_configured: bool
    solver_name: str
    status: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get quantum dispatcher status.
    
    Returns whether quantum optimization is enabled and configured.
    """
    import os
    api_token = os.environ.get('DWAVE_API_TOKEN')
    solver_name = os.environ.get('DWAVE_SOLVER', 'hybrid_binary_quadratic_model_version2')
    
    enabled = bool(api_token)
    status = "ready" if enabled else "not_configured"
    
    return StatusResponse(
        enabled=enabled,
        api_token_configured=bool(api_token),
        solver_name=solver_name,
        status=status
    )


@router.post("/optimize", response_model=RouteResponse)
async def optimize_route(request: OptimizeRequest):
    """
    Optimize delivery route using quantum annealing.
    
    Falls back to classical OR-Tools if quantum unavailable.
    
    **Free for all Nduna drivers.**
    """
    if not request.stops:
        raise HTTPException(status_code=400, detail="No stops provided")
    
    # Convert to DeliveryStop objects
    stops = [
        DeliveryStop(
            id=s.id,
            name=s.name,
            lat=s.lat,
            lng=s.lng,
            time_window_start=s.time_window_start,
            time_window_end=s.time_window_end,
            service_time_minutes=s.service_time_minutes,
            priority=s.priority
        )
        for s in request.stops
    ]
    
    # Run quantum optimization
    result = optimize_route_quantum(
        stops,
        request.start_lat,
        request.start_lng,
        request.avg_speed_kmh
    )
    
    return RouteResponse(
        stops=[
            StopResponse(**stop) for stop in result.route.stops
        ],
        total_distance_m=result.route.total_distance_m,
        total_time_minutes=result.route.total_time_minutes,
        total_service_time_minutes=result.route.total_service_time_minutes,
        savings_vs_original_minutes=result.route.savings_vs_original_minutes,
        confidence=result.route.confidence,
        solver_type=result.solver_type,
        solve_time_ms=result.solve_time_ms,
        quantum_energy=result.quantum_energy,
        success=result.success,
        error_message=result.error_message
    )


@router.post("/ab-test", response_model=ABTestResponse)
async def run_ab_test(request: ABTestRequest):
    """
    Run A/B test comparing quantum vs classical routing.
    
    Returns detailed comparison metrics for analysis.
    """
    if not request.stops:
        raise HTTPException(status_code=400, detail="No stops provided")
    
    # Convert to DeliveryStop objects
    stops = [
        DeliveryStop(
            id=s.id,
            name=s.name,
            lat=s.lat,
            lng=s.lng,
            time_window_start=s.time_window_start,
            time_window_end=s.time_window_end,
            service_time_minutes=s.service_time_minutes,
            priority=s.priority
        )
        for s in request.stops
    ]
    
    # Run A/B test
    result = run_quantum_ab_test(
        stops,
        request.start_lat,
        request.start_lng,
        request.avg_speed_kmh
    )
    
    return ABTestResponse(
        test_id=result.test_id,
        timestamp=result.timestamp,
        num_stops=result.num_stops,
        quantum_distance_m=result.quantum_distance_m,
        quantum_time_minutes=result.quantum_time_ms / 60000,  # Convert to minutes
        quantum_solve_time_ms=result.quantum_solve_time_ms,
        quantum_success=result.quantum_success,
        classical_distance_m=result.classical_distance_m,
        classical_time_minutes=result.classical_time_ms / 60000,
        classical_solve_time_ms=result.classical_solve_time_ms,
        improvement_percent=result.improvement_percent,
        faster_percent=result.faster_percent,
        winner=result.winner
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get A/B test summary statistics.
    
    Returns aggregate performance metrics across all tests.
    """
    stats = get_quantum_stats()
    
    return StatsResponse(
        total_tests=stats.get("total_tests", 0),
        quantum_wins=stats.get("quantum_wins", 0),
        classical_wins=stats.get("classical_wins", 0),
        ties=stats.get("ties", 0),
        quantum_win_rate=stats.get("quantum_win_rate", 0),
        avg_improvement_percent=stats.get("avg_improvement_percent", 0),
        quantum_success_rate=stats.get("quantum_success_rate", 0)
    )


@router.post("/batch-ab-test")
async def run_batch_ab_test(
    num_tests: int = 10,
    min_stops: int = 5,
    max_stops: int = 15
):
    """
    Run multiple A/B tests with random routes.
    
    Useful for generating statistical data.
    
    Args:
        num_tests: Number of tests to run (default 10)
        min_stops: Minimum stops per route (default 5)
        max_stops: Maximum stops per route (default 15)
    """
    import random
    import uuid
    
    results = []
    
    # Johannesburg area coordinates
    jhb_center_lat = -26.2041
    jhb_center_lng = 28.0473
    
    for _ in range(num_tests):
        num_stops = random.randint(min_stops, max_stops)
        
        # Generate random stops
        stops = []
        for i in range(num_stops):
            stops.append(DeliveryStop(
                id=f"stop-{i}",
                name=f"Stop {i}",
                lat=jhb_center_lat + random.uniform(-0.05, 0.05),
                lng=jhb_center_lng + random.uniform(-0.05, 0.05),
                service_time_minutes=random.randint(3, 8),
                priority=random.randint(0, 10)
            ))
        
        # Run test
        start_lat = jhb_center_lat + random.uniform(-0.02, 0.02)
        start_lng = jhb_center_lng + random.uniform(-0.02, 0.02)
        
        result = run_quantum_ab_test(stops, start_lat, start_lng)
        results.append({
            "test_id": result.test_id,
            "num_stops": result.num_stops,
            "improvement_percent": result.improvement_percent,
            "winner": result.winner,
            "quantum_success": result.quantum_success
        })
    
    return {
        "total_tests": num_tests,
        "results": results,
        "summary": get_quantum_stats()
    }
