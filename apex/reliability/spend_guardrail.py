#!/usr/bin/env python3
"""
APEX Spend Guardrail
Monitors and controls AI spending with hard limits
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class SpendEntry:
    timestamp: str
    agent_id: str
    task_id: str
    cost_usd: float
    tokens_input: int
    tokens_output: int
    model: str


class SpendGuardrail:
    """Monitors and controls spending with automatic circuit breakers"""
    
    def __init__(self, 
                 daily_budget: float = 500.0,
                 hourly_budget: float = 50.0,
                 data_dir: str = "/home/teacherchris37/MasterBuilder7/apex/data"):
        self.daily_budget = daily_budget
        self.hourly_budget = hourly_budget
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.spend_log: List[SpendEntry] = []
        self.circuit_breaker_tripped = False
        self.load_spend_data()
    
    def load_spend_data(self):
        """Load historical spend data"""
        spend_path = os.path.join(self.data_dir, "spend_log.json")
        if os.path.exists(spend_path):
            with open(spend_path, 'r') as f:
                data = json.load(f)
                self.spend_log = [SpendEntry(**entry) for entry in data]
    
    def save_spend_data(self):
        """Save spend data to disk"""
        spend_path = os.path.join(self.data_dir, "spend_log.json")
        with open(spend_path, 'w') as f:
            json.dump([asdict(entry) for entry in self.spend_log], f, indent=2)
    
    def record_spend(self, agent_id: str, task_id: str, 
                     cost_usd: float, tokens_input: int, 
                     tokens_output: int, model: str) -> Dict:
        """Record a spend entry and check budgets"""
        
        entry = SpendEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            task_id=task_id,
            cost_usd=cost_usd,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model=model
        )
        
        self.spend_log.append(entry)
        self.save_spend_data()
        
        # Check budgets
        status = self.check_budgets()
        
        return {
            'recorded': True,
            'entry_id': len(self.spend_log),
            'budget_status': status
        }
    
    def check_budgets(self) -> Dict:
        """Check current spend against budgets"""
        now = datetime.now()
        
        # Calculate daily spend
        day_ago = now - timedelta(days=1)
        daily_spend = sum(
            entry.cost_usd for entry in self.spend_log
            if datetime.fromisoformat(entry.timestamp) > day_ago
        )
        
        # Calculate hourly spend
        hour_ago = now - timedelta(hours=1)
        hourly_spend = sum(
            entry.cost_usd for entry in self.spend_log
            if datetime.fromisoformat(entry.timestamp) > hour_ago
        )
        
        # Check thresholds
        daily_pct = (daily_spend / self.daily_budget) * 100
        hourly_pct = (hourly_spend / self.hourly_budget) * 100
        
        # Determine status
        status = 'ok'
        actions = []
        
        if daily_pct >= 100:
            status = 'critical'
            actions.append('kill_all_agents')
            self.circuit_breaker_tripped = True
        elif daily_pct >= 95:
            status = 'danger'
            actions.append('pause_new_tasks')
        elif daily_pct >= 80:
            status = 'warning'
            actions.append('reduce_parallel_agents')
        
        if hourly_pct >= 100:
            status = 'critical'
            actions.append('throttle_agents')
        
        return {
            'status': status,
            'daily_spend': round(daily_spend, 2),
            'daily_budget': self.daily_budget,
            'daily_pct': round(daily_pct, 1),
            'hourly_spend': round(hourly_spend, 2),
            'hourly_budget': self.hourly_budget,
            'hourly_pct': round(hourly_pct, 1),
            'actions_required': actions,
            'circuit_breaker': self.circuit_breaker_tripped
        }
    
    def get_spend_summary(self, days: int = 7) -> Dict:
        """Get spend summary for the last N days"""
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        recent_entries = [
            entry for entry in self.spend_log
            if datetime.fromisoformat(entry.timestamp) > cutoff
        ]
        
        total_spend = sum(entry.cost_usd for entry in recent_entries)
        total_tokens = sum(
            entry.tokens_input + entry.tokens_output 
            for entry in recent_entries
        )
        
        # Spend by agent
        by_agent = {}
        for entry in recent_entries:
            by_agent[entry.agent_id] = by_agent.get(entry.agent_id, 0) + entry.cost_usd
        
        # Spend by model
        by_model = {}
        for entry in recent_entries:
            by_model[entry.model] = by_model.get(entry.model, 0) + entry.cost_usd
        
        return {
            'period_days': days,
            'total_spend': round(total_spend, 2),
            'total_tokens': total_tokens,
            'entry_count': len(recent_entries),
            'by_agent': {k: round(v, 2) for k, v in by_agent.items()},
            'by_model': {k: round(v, 2) for k, v in by_model.items()},
            'avg_per_task': round(total_spend / len(recent_entries), 2) if recent_entries else 0
        }
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker (requires approval)"""
        self.circuit_breaker_tripped = False
        return {'reset': True, 'timestamp': datetime.now().isoformat()}
    
    def can_execute_task(self, estimated_cost: float = 0.10) -> Dict:
        """Check if a new task can be executed"""
        status = self.check_budgets()
        
        if self.circuit_breaker_tripped:
            return {
                'can_execute': False,
                'reason': 'circuit_breaker_tripped',
                'action_required': 'manual_reset_approval'
            }
        
        if status['status'] == 'critical':
            return {
                'can_execute': False,
                'reason': 'budget_critical',
                'action_required': 'wait_or_approve'
            }
        
        # Check if this task would exceed budget
        projected_daily = status['daily_spend'] + estimated_cost
        if projected_daily > self.daily_budget:
            return {
                'can_execute': False,
                'reason': 'would_exceed_budget',
                'projected_daily': round(projected_daily, 2)
            }
        
        return {
            'can_execute': True,
            'remaining_daily': round(self.daily_budget - status['daily_spend'], 2),
            'confidence': 'high' if status['daily_pct'] < 50 else 'medium'
        }


if __name__ == "__main__":
    # Test
    guardrail = SpendGuardrail(daily_budget=100.0)
    
    print("Testing APEX Spend Guardrail...")
    
    # Record some test spend
    for i in range(5):
        result = guardrail.record_spend(
            agent_id=f"agent-{i}",
            task_id=f"task-{i}",
            cost_usd=5.0,
            tokens_input=1000,
            tokens_output=500,
            model="kimi-k2-5"
        )
    
    status = guardrail.check_budgets()
    print(f"\nBudget Status: {status['status']}")
    print(f"Daily Spend: ${status['daily_spend']} / ${status['daily_budget']}")
    print(f"Percentage: {status['daily_pct']}%")
    
    summary = guardrail.get_spend_summary(days=1)
    print(f"\nTotal Entries: {summary['entry_count']}")
    print(f"Total Spend: ${summary['total_spend']}")
