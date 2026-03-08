#!/usr/bin/env python3
"""
Cost Calculator - Pricing logic for Render and ICP
Returns estimated cost, monthly projection, warnings, cycles
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CostEstimate:
    estimated_cost: float
    monthly_projection: float
    warnings: list
    cycles: Optional[int] = None


class RenderCostCalculator:
    PRICING = {
        "starter": {"monthly": 0, "cpu_seconds": 0.0001},
        "standard": {"monthly": 25, "cpu_seconds": 0.0002},
        "pro": {"monthly": 85, "cpu_seconds": 0.0005}
    }
    
    def estimate_deployment(self, plan: str, build_minutes: int) -> CostEstimate:
        if plan not in self.PRICING:
            raise ValueError(f"Unknown plan: {plan}")
        
        pricing = self.PRICING[plan]
        cpu_cost = build_minutes * 60 * pricing["cpu_seconds"]
        
        return CostEstimate(
            estimated_cost=round(cpu_cost, 4),
            monthly_projection=pricing["monthly"],
            warnings=self._get_warnings(plan, build_minutes),
            cycles=None
        )
    
    def _get_warnings(self, plan: str, build_minutes: int) -> list:
        warnings = []
        if plan == "starter" and build_minutes > 30:
            warnings.append("Starter plan may timeout on builds > 30 min")
        if build_minutes > 60:
            warnings.append("Consider caching dependencies to reduce build time")
        return warnings


class ICPCostCalculator:
    CYCLE_PRICING = {
        "update": 0.0001,
        "query": 0.00001,
        "storage_gb": 0.50
    }
    
    def estimate_canister(self, requests_per_day: int, storage_gb: float) -> CostEstimate:
        daily_cost = (
            requests_per_day * 0.9 * self.CYCLE_PRICING["query"] +
            requests_per_day * 0.1 * self.CYCLE_PRICING["update"]
        )
        storage_cost = storage_gb * self.CYCLE_PRICING["storage_gb"] / 30
        monthly = (daily_cost + storage_cost) * 30
        
        return CostEstimate(
            estimated_cost=round(daily_cost + storage_cost, 6),
            monthly_projection=round(monthly, 4),
            warnings=[],
            cycles=self._usd_to_cycles(monthly)
        )
    
    def _usd_to_cycles(self, usd: float) -> int:
        return int(usd * 1_000_000_000)  # 1 USD = 1T cycles


if __name__ == "__main__":
    render = RenderCostCalculator()
    icp = ICPCostCalculator()
    
    print("Render Starter (10 min build):", render.estimate_deployment("starter", 10))
    print("ICP (1000 req/day, 1GB):", icp.estimate_canister(1000, 1))
