# Quantum Dispatch Setup Guide

This guide explains how to set up D-Wave Leap for quantum-enhanced route optimization in iHhashi.

## What is Quantum Dispatch?

Quantum dispatch uses D-Wave's quantum annealing technology to solve the Vehicle Routing Problem (VRP). This can provide:

- **10-31% better routing efficiency** (based on industry studies: UPS+IonQ 24%, DHL+Rigetti 31%)
- **Optimized multi-stop routes** for 10-30 stops
- **Real-time optimization** using hybrid quantum-classical solvers

## Prerequisites

1. **D-Wave Leap Account** (Free tier available)
   - Sign up at: https://cloud.dwavesys.com/leap/
   - Free tier includes 1 minute of QPU time per month

2. **API Token**
   - Get your token from: https://cloud.dwavesys.com/leap/api/

## Setup Steps

### 1. Install Dependencies

```bash
cd backend
pip install dwave-system dwave-networkx dimod
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Configure API Token

Set the D-Wave API token as an environment variable:

**For local development (.env file):**
```env
DWAVE_API_TOKEN=your-api-token-here
DWAVE_SOLVER=hybrid_binary_quadratic_model_version2
```

**For production (Render/Railway/etc):**
Add `DWAVE_API_TOKEN` to your environment variables in the dashboard.

### 3. Verify Setup

Run the test suite:
```bash
cd backend
python -m pytest tests/test_quantum_dispatch.py -v
```

Or test via API:
```bash
curl -X POST http://localhost:8000/api/v1/quantum-dispatch/status
```

## API Endpoints

### Check Status
```
GET /api/v1/quantum-dispatch/status
```

Response:
```json
{
  "enabled": true,
  "api_token_configured": true,
  "solver_name": "hybrid_binary_quadratic_model_version2",
  "status": "ready"
}
```

### Optimize Route (Quantum)
```
POST /api/v1/quantum-dispatch/optimize
```

Request:
```json
{
  "stops": [
    {
      "id": "1",
      "name": "Customer A",
      "lat": -26.1076,
      "lng": 28.0567,
      "service_time_minutes": 5,
      "priority": 0
    }
  ],
  "start_lat": -26.2041,
  "start_lng": 28.0473,
  "avg_speed_kmh": 30.0
}
```

Response includes:
- Optimized stop order
- Total distance and time
- `solver_type`: "quantum", "hybrid", or "classical_fallback"
- `quantum_energy`: Energy of quantum solution
- `confidence`: Confidence level (0-1)

### Run A/B Test
```
POST /api/v1/quantum-dispatch/ab-test
```

Compares quantum vs classical routing on the same route.

Response includes:
- Distance improvement percentage
- Time improvement percentage
- Winner: "quantum", "classical", or "tie"

### Get Statistics
```
GET /api/v1/quantum-dispatch/stats
```

Returns aggregate statistics from all A/B tests:
- Total tests run
- Quantum win rate
- Average improvement percentage

### Batch A/B Testing
```
POST /api/v1/quantum-dispatch/batch-ab-test?num_tests=10&min_stops=5&max_stops=15
```

Run multiple tests with random routes to gather statistical data.

## How It Works

### Problem Formulation

The VRP is formulated as a QUBO (Quadratic Unconstrained Binary Optimization) problem:

1. **Decision Variables**: `x[i,j] = 1` if node `i` is visited at position `j`
2. **Objective**: Minimize total travel distance
3. **Constraints**:
   - Each node visited exactly once
   - Each position has exactly one node

### Solvers

1. **Hybrid Solver** (default): Best for 10-100 stops
   - Uses classical + quantum processing
   - 5-second solve time limit
   - Handles larger problems efficiently

2. **QPU Solver**: For smaller problems (<30 nodes)
   - Pure quantum annealing
   - Microsecond annealing time
   - Best for sub-problems

### Fallback

If quantum optimization fails (no token, network error, etc.), the system automatically falls back to OR-Tools classical optimization. Users always get a valid route.

## Performance Tuning

### When to Use Quantum

| Stops | Recommended Approach |
|-------|---------------------|
| 1-5 | Either (similar performance) |
| 5-15 | Quantum (10-15% improvement) |
| 15-30 | Quantum (15-25% improvement) |
| 30+ | Classical OR-Tools |

### Cost Optimization

- Free tier: 1 minute QPU time/month
- Typical optimization: ~0.1 second
- ~600 optimizations/month on free tier

For production, consider:
1. Caching frequently-used routes
2. Using quantum only for 10+ stops
3. Running A/B tests during off-peak hours

## Troubleshooting

### "Quantum optimization failed"

1. Check API token is set: `echo $DWAVE_API_TOKEN`
2. Verify token at https://cloud.dwavesys.com/leap/api/
3. Check solver availability at https://cloud.dwavesys.com/leap/solvers/

### "No feasible quantum solution"

- Problem may be too constrained
- Try removing time windows
- Reduce number of stops

### "Classical fallback used"

This is normal behavior when:
- No API token configured
- Quantum solver unavailable
- Problem too large for QPU

## References

- [D-Wave Ocean SDK Documentation](https://docs.dwavesys.com/docs/latest/ocean/index.html)
- [Vehicle Routing Problem on D-Wave](https://docs.dwavesys.com/docs/latest/ocean/api_ref_dnx/algorithms.html#traveling-salesperson)
- [UPS + IonQ Case Study](https://www.forbes.com/sites/moorinsights/2022/11/09/ups-ionq-quantum-computing-routing/)
- [DHL + Rigetti Research](https://www.dhl.com/global-en/home/insights-and-innovation/insights/quantum-computing.html)

## Support

For issues specific to iHhashi quantum dispatch:
1. Check the logs: `/dev/shm/ihhashi-backend.log`
2. Run tests: `pytest tests/test_quantum_dispatch.py -v`
3. Contact the iHhashi team
