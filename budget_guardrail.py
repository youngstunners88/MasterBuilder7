#!/usr/bin/env python3
"""
Budget Guardrail - Tracks daily/monthly spending, enforces limits
"""

import json
import os
from datetime import datetime
from pathlib import Path


class BudgetGuardrail:
    def __init__(self, daily_limit: float, monthly_limit: float, state_file: str = ".budget_state.json"):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.state_file = Path(state_file)
        self._load_state()
    
    def _load_state(self):
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                self.spent_today = state.get("spent_today", 0.0)
                self.spent_this_month = state.get("spent_this_month", 0.0)
                self.last_reset = state.get("last_reset", datetime.now().isoformat())
        else:
            self.spent_today = 0.0
            self.spent_this_month = 0.0
            self.last_reset = datetime.now().isoformat()
    
    def _persist_state(self):
        with open(self.state_file, "w") as f:
            json.dump({
                "spent_today": self.spent_today,
                "spent_this_month": self.spent_this_month,
                "last_reset": self.last_reset
            }, f)
    
    def can_execute(self, estimated_cost: float) -> bool:
        if self.spent_today + estimated_cost > self.daily_limit:
            return False
        if self.spent_this_month + estimated_cost > self.monthly_limit:
            return False
        return True
    
    def charge(self, actual_cost: float):
        self.spent_today += actual_cost
        self.spent_this_month += actual_cost
        self._persist_state()
    
    def get_status(self) -> dict:
        return {
            "daily_limit": self.daily_limit,
            "monthly_limit": self.monthly_limit,
            "spent_today": round(self.spent_today, 4),
            "spent_this_month": round(self.spent_this_month, 4),
            "daily_remaining": round(self.daily_limit - self.spent_today, 4),
            "monthly_remaining": round(self.monthly_limit - self.spent_this_month, 4)
        }
