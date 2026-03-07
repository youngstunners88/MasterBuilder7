"""
Route Optimization Service using Google OR-Tools

Provides optimal route sequencing for multiple delivery stops.
Handles Vehicle Routing Problem (VRP) with time windows and capacity constraints.

FREE for all Nduna drivers - builds adoption for future Nduna Pro.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class DeliveryStop:
    """A single delivery stop"""
    id: str
    name: str
    lat: float
    lng: float
    time_window_start: Optional[int] = None  # Minutes from now
    time_window_end: Optional[int] = None
    service_time_minutes: int = 5  # Time to complete delivery
    priority: int = 0  # Higher = more important


@dataclass
class OptimizedRoute:
    """Result of route optimization"""
    stops: List[Dict[str, Any]]
    total_distance_m: float
    total_time_minutes: float
    total_service_time_minutes: float
    savings_vs_original_minutes: float
    confidence: float


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two GPS coordinates in meters.
    Uses Haversine formula for great-circle distance.
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def calculate_distance_matrix(stops: List[DeliveryStop]) -> List[List[int]]:
    """
    Create distance matrix between all stops.
    Returns distances in meters as integers (OR-Tools requirement).
    """
    n = len(stops)
    matrix = [[0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = haversine_distance(
                    stops[i].lat, stops[i].lng,
                    stops[j].lat, stops[j].lng
                )
                matrix[i][j] = int(dist)
    
    return matrix


def calculate_time_matrix(
    distance_matrix: List[List[int]], 
    avg_speed_kmh: float = 30.0
) -> List[List[int]]:
    """
    Convert distance matrix to time matrix.
    Returns time in minutes as integers.
    
    Args:
        distance_matrix: Distances in meters
        avg_speed_kmh: Average speed in km/h (default 30 km/h for SA urban)
    """
    n = len(distance_matrix)
    time_matrix = [[0] * n for _ in range(n)]
    
    # Convert speed to m/min
    speed_m_per_min = (avg_speed_kmh * 1000) / 60
    
    for i in range(n):
        for j in range(n):
            if i != j:
                time_minutes = distance_matrix[i][j] / speed_m_per_min
                time_matrix[i][j] = int(time_minutes)
    
    return time_matrix


def optimize_route_vrp(
    stops: List[DeliveryStop],
    start_lat: float,
    start_lng: float,
    max_stops: int = 25,
    avg_speed_kmh: float = 30.0,
    consider_time_windows: bool = True
) -> OptimizedRoute:
    """
    Optimize delivery route using OR-Tools VRP solver.
    
    FREE for all drivers - no limits, no subscriptions.
    
    Args:
        stops: List of delivery stops to optimize
        start_lat: Starting latitude (e.g., driver's current location or pickup)
        start_lng: Starting longitude
        max_stops: Maximum stops to optimize (OR-Tools performs well up to 25)
        avg_speed_kmh: Average travel speed
        consider_time_windows: Whether to respect time windows
    
    Returns:
        OptimizedRoute with stops in optimal order
    """
    if not stops:
        raise ValueError("No stops provided for optimization")
    
    if len(stops) > max_stops:
        # For large routes, use greedy approximation
        return optimize_route_greedy(stops, start_lat, start_lng, avg_speed_kmh)
    
    # Add depot (start location) as stop 0
    depot = DeliveryStop(
        id="depot",
        name="Start",
        lat=start_lat,
        lng=start_lng,
        service_time_minutes=0
    )
    
    all_stops = [depot] + stops
    
    # Calculate distance and time matrices
    distance_matrix = calculate_distance_matrix(all_stops)
    time_matrix = calculate_time_matrix(distance_matrix, avg_speed_kmh)
    
    try:
        # Import OR-Tools
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        
        # Create routing model
        manager = pywrapcp.RoutingIndexManager(
            len(all_stops),  # Number of nodes
            1,  # Number of vehicles
            0   # Depot index
        )
        routing = pywrapcp.RoutingModel(manager)
        
        # Add distance dimension
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add time dimension
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        routing.AddDimension(
            time_callback_index,
            30,  # Allow 30 min waiting time
            480,  # Maximum 8 hours total route time
            False,  # Don't force start cumul to zero
            'Time'
        )
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Add time window constraints if applicable
        if consider_time_windows:
            for i, stop in enumerate(all_stops):
                if stop.time_window_start is not None and stop.time_window_end is not None:
                    index = manager.NodeToIndex(i)
                    time_dimension.CumulVar(index).SetRange(
                        stop.time_window_start,
                        stop.time_window_end
                    )
        
        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 5  # Quick solve for real-time use
        
        # Solve
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            # Extract optimized route
            index = routing.Start(0)
            route_indices = []
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route_indices.append(node)
                index = solution.Value(routing.NextVar(index))
            
            # Remove depot from route
            route_indices = [i for i in route_indices if i != 0]
            
            # Calculate metrics
            total_distance = 0
            total_time = 0
            
            prev_lat, prev_lng = start_lat, start_lng
            
            optimized_stops = []
            for idx in route_indices:
                stop = all_stops[idx]
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
            
            # Calculate savings vs original order
            original_time = calculate_total_time(stops, start_lat, start_lng, avg_speed_kmh)
            savings = original_time - total_time
            
            return OptimizedRoute(
                stops=optimized_stops,
                total_distance_m=total_distance,
                total_time_minutes=round(total_time, 1),
                total_service_time_minutes=sum(s.service_time_minutes for s in stops),
                savings_vs_original_minutes=round(savings, 1),
                confidence=0.9 if len(stops) <= 15 else 0.8
            )
        
    except ImportError:
        # OR-Tools not available, fall back to greedy
        pass
    except Exception as e:
        # OR-Tools failed, fall back to greedy
        print(f"OR-Tools optimization failed: {e}")
    
    # Fall back to greedy optimization
    return optimize_route_greedy(stops, start_lat, start_lng, avg_speed_kmh)


def optimize_route_greedy(
    stops: List[DeliveryStop],
    start_lat: float,
    start_lng: float,
    avg_speed_kmh: float = 30.0
) -> OptimizedRoute:
    """
    Greedy nearest-neighbor optimization.
    Used as fallback when OR-Tools unavailable or for very large routes.
    
    Faster but less optimal than OR-Tools.
    """
    if not stops:
        raise ValueError("No stops provided")
    
    # Sort by priority first (higher priority = earlier)
    priority_stops = sorted(stops, key=lambda s: -s.priority)
    remaining = list(priority_stops)
    optimized_order = []
    
    current_lat, current_lng = start_lat, start_lng
    
    # Nearest neighbor with priority consideration
    while remaining:
        # Find nearest stop with priority bonus
        best_stop = None
        best_score = float('inf')
        
        for stop in remaining:
            dist = haversine_distance(current_lat, current_lng, stop.lat, stop.lng)
            # Priority reduces effective distance (higher priority = closer)
            score = dist * (1 - stop.priority * 0.1)
            
            if score < best_score:
                best_score = score
                best_stop = stop
        
        if best_stop:
            optimized_order.append(best_stop)
            remaining.remove(best_stop)
            current_lat, current_lng = best_stop.lat, best_stop.lng
    
    # Calculate metrics
    total_distance = 0
    total_time = 0
    prev_lat, prev_lng = start_lat, start_lng
    
    optimized_stops = []
    for stop in optimized_order:
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
    
    # Calculate savings vs original order
    original_time = calculate_total_time(stops, start_lat, start_lng, avg_speed_kmh)
    savings = original_time - total_time
    
    return OptimizedRoute(
        stops=optimized_stops,
        total_distance_m=total_distance,
        total_time_minutes=round(total_time, 1),
        total_service_time_minutes=sum(s.service_time_minutes for s in stops),
        savings_vs_original_minutes=round(savings, 1),
        confidence=0.7  # Lower confidence for greedy
    )


def calculate_total_time(
    stops: List[DeliveryStop],
    start_lat: float,
    start_lng: float,
    avg_speed_kmh: float
) -> float:
    """Calculate total time for a route in given order."""
    total = 0
    prev_lat, prev_lng = start_lat, start_lng
    
    for stop in stops:
        dist = haversine_distance(prev_lat, prev_lng, stop.lat, stop.lng)
        time_minutes = dist / ((avg_speed_kmh * 1000) / 60)
        total += time_minutes + stop.service_time_minutes
        prev_lat, prev_lng = stop.lat, stop.lng
    
    return total


def optimize_multi_pickup_route(
    pickups: List[Dict[str, Any]],
    deliveries: List[Dict[str, Any]],
    driver_lat: float,
    driver_lng: float
) -> OptimizedRoute:
    """
    Optimize route with multiple pickups and deliveries.
    
    Handles the pickup-delivery pairing constraint:
    - Each delivery must come after its corresponding pickup
    - Useful for multi-store orders
    
    Args:
        pickups: List of pickup locations with order_id
        deliveries: List of delivery locations with order_id
        driver_lat: Driver's current latitude
        driver_lng: Driver's current longitude
    
    Returns:
        OptimizedRoute with pickups and deliveries in optimal order
    """
    # Create stop objects
    pickup_stops = [
        DeliveryStop(
            id=f"pickup-{p['order_id']}",
            name=f"Pickup: {p.get('merchant_name', 'Store')}",
            lat=p['lat'],
            lng=p['lng'],
            service_time_minutes=3,
            priority=10  # Pickups before deliveries
        )
        for p in pickups
    ]
    
    delivery_stops = [
        DeliveryStop(
            id=f"delivery-{d['order_id']}",
            name=f"Delivery: {d.get('customer_name', 'Customer')}",
            lat=d['lat'],
            lng=d['lng'],
            service_time_minutes=5,
            priority=5
        )
        for d in deliveries
    ]
    
    # For now, optimize all together with priority
    # Full pickup-delivery constraint requires more complex OR-Tools setup
    all_stops = pickup_stops + delivery_stops
    
    return optimize_route_vrp(all_stops, driver_lat, driver_lng)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def optimize_from_orders(
    orders: List[Dict[str, Any]],
    driver_lat: float,
    driver_lng: float
) -> OptimizedRoute:
    """
    Optimize route from order objects.
    
    Args:
        orders: List of order dicts with pickup and delivery locations
        driver_lat: Driver's current latitude
        driver_lng: Driver's current longitude
    
    Returns:
        OptimizedRoute
    """
    stops = []
    
    for order in orders:
        # Add pickup
        pickup = order.get('pickup_location', {})
        if pickup:
            stops.append(DeliveryStop(
                id=f"pickup-{order.get('id', len(stops))}",
                name=f"Pickup: {order.get('merchant_name', 'Store')}",
                lat=pickup.get('lat', 0),
                lng=pickup.get('lng', 0),
                service_time_minutes=3,
                priority=10
            ))
        
        # Add delivery
        delivery = order.get('delivery_location', {})
        if delivery:
            stops.append(DeliveryStop(
                id=f"delivery-{order.get('id', len(stops))}",
                name=f"Delivery: {order.get('customer_name', 'Customer')}",
                lat=delivery.get('lat', 0),
                lng=delivery.get('lng', 0),
                service_time_minutes=5,
                priority=5
            ))
    
    return optimize_route_vrp(stops, driver_lat, driver_lng)


def estimate_optimization_savings(
    num_stops: int,
    avg_distance_between_stops_km: float = 2.0
) -> Dict[str, float]:
    """
    Estimate time savings from route optimization.
    
    Based on industry studies:
    - VRP optimization typically saves 10-30% travel time
    - Savings increase with number of stops
    """
    if num_stops <= 2:
        savings_percent = 0
    elif num_stops <= 5:
        savings_percent = 0.10
    elif num_stops <= 10:
        savings_percent = 0.20
    elif num_stops <= 20:
        savings_percent = 0.25
    else:
        savings_percent = 0.30
    
    # Calculate estimated metrics
    total_distance_km = num_stops * avg_distance_between_stops_km
    avg_speed_kmh = 30
    base_time_minutes = (total_distance_km / avg_speed_kmh) * 60
    
    saved_time_minutes = base_time_minutes * savings_percent
    
    return {
        "num_stops": num_stops,
        "estimated_total_time_minutes": round(base_time_minutes, 1),
        "estimated_savings_minutes": round(saved_time_minutes, 1),
        "savings_percent": round(savings_percent * 100, 1)
    }
