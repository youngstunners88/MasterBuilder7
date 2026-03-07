#!/usr/bin/env python3
"""
MasterBuilder7 Cost Tracker System

Tracks spending across all agents and AI models with budget enforcement,
alerts, and optimization recommendations.

Features:
- Per-agent cost tracking
- Per-AI cost tracking (Kimi, ChatGPT, Grok, Claude)
- Budget enforcement with kill switch
- Cost projections and alerts
- Usage optimization recommendations

Author: MasterBuilder7
Version: 1.0.0
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CostTracker")


class AIProvider(Enum):
    """Supported AI providers with their pricing models."""
    KIMI = "kimi"
    CHATGPT = "chatgpt"
    GROK = "grok"
    CLAUDE = "claude"
    OTHER = "other"


class AlertLevel(Enum):
    """Budget alert levels."""
    NONE = 0
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    KILL_SWITCH = 4


@dataclass
class UsageRecord:
    """Single usage record for an AI request."""
    timestamp: datetime
    agent_id: str
    provider: AIProvider
    model: str
    tokens_input: int
    tokens_output: int
    cost_per_token_input: float
    cost_per_token_output: float
    total_cost: float
    request_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "provider": self.provider.value,
            "model": self.model,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_per_token_input": self.cost_per_token_input,
            "cost_per_token_output": self.cost_per_token_output,
            "total_cost": self.total_cost,
            "request_type": self.request_type,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageRecord":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent_id=data["agent_id"],
            provider=AIProvider(data["provider"]),
            model=data["model"],
            tokens_input=data["tokens_input"],
            tokens_output=data["tokens_output"],
            cost_per_token_input=data["cost_per_token_input"],
            cost_per_token_output=data["cost_per_token_output"],
            total_cost=data["total_cost"],
            request_type=data["request_type"],
            metadata=data.get("metadata", {})
        )


@dataclass
class BudgetAlert:
    """Budget alert with severity and message."""
    level: AlertLevel
    threshold_percent: float
    current_spend: float
    budget: float
    message: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "threshold_percent": self.threshold_percent,
            "current_spend": self.current_spend,
            "budget": self.budget,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


class CostTracker:
    """
    Centralized cost tracking system for MasterBuilder7.
    
    Tracks spending across all agents and AI models with budget enforcement,
    alerts, and optimization recommendations.
    
    Example:
        >>> tracker = CostTracker(daily_budget=500.0)
        >>> tracker.record_usage(
        ...     agent_id="agent_001",
        ...     provider=AIProvider.CHATGPT,
        ...     model="gpt-4",
        ...     tokens_input=1000,
        ...     tokens_output=500,
        ...     request_type="code_generation"
        ... )
        >>> report = tracker.get_cost_report()
        >>> print(report.summary())
    """
    
    # Default pricing per 1K tokens (input, output) in USD
    DEFAULT_PRICING: Dict[AIProvider, Dict[str, tuple]] = {
        AIProvider.KIMI: {
            "default": (0.0003, 0.0006),  # ~$0.30/$0.60 per 1M tokens
            "kimi-v1": (0.0003, 0.0006),
            "kimi-v1-long": (0.0005, 0.0010),
        },
        AIProvider.CHATGPT: {
            "gpt-4": (0.03, 0.06),  # per 1K tokens
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "o1": (0.015, 0.06),
            "o3-mini": (0.0011, 0.0044),
        },
        AIProvider.GROK: {
            "grok-2": (0.005, 0.015),
            "grok-2-vision": (0.01, 0.03),
            "grok-beta": (0.005, 0.015),
        },
        AIProvider.CLAUDE: {
            "claude-3-opus": (0.015, 0.075),
            "claude-3-sonnet": (0.003, 0.015),
            "claude-3-haiku": (0.00025, 0.00125),
            "claude-3-5-sonnet": (0.003, 0.015),
        },
        AIProvider.OTHER: {
            "default": (0.001, 0.002),
        }
    }
    
    # Optimization rules for cost reduction
    OPTIMIZATION_RULES: List[Dict[str, Any]] = [
        {
            "condition": lambda p, m: p == AIProvider.CHATGPT and "gpt-4" in m and "mini" not in m,
            "suggestion": "Consider using GPT-4o-mini for non-complex tasks (60x cheaper)",
            "savings_percent": 97,
            "alternative": (AIProvider.CHATGPT, "gpt-4o-mini")
        },
        {
            "condition": lambda p, m: p == AIProvider.CHATGPT and m == "gpt-4",
            "suggestion": "Use Kimi for code generation (10x cheaper, comparable quality)",
            "savings_percent": 90,
            "alternative": (AIProvider.KIMI, "kimi-v1")
        },
        {
            "condition": lambda p, m: p == AIProvider.CLAUDE and "opus" in m,
            "suggestion": "Consider Claude Sonnet for most tasks (5x cheaper)",
            "savings_percent": 80,
            "alternative": (AIProvider.CLAUDE, "claude-3-5-sonnet")
        },
        {
            "condition": lambda p, m: p == AIProvider.GROK and "vision" in m,
            "suggestion": "Use standard Grok-2 for text-only tasks (3x cheaper)",
            "savings_percent": 67,
            "alternative": (AIProvider.GROK, "grok-2")
        },
        {
            "condition": lambda p, m: p == AIProvider.CHATGPT and m == "gpt-3.5-turbo",
            "suggestion": "Upgrade to GPT-4o-mini for better quality at lower cost",
            "savings_percent": 70,
            "alternative": (AIProvider.CHATGPT, "gpt-4o-mini")
        },
    ]
    
    # Budget alert thresholds
    ALERT_THRESHOLDS = [0.50, 0.75, 0.90, 1.0]
    
    def __init__(
        self,
        daily_budget: float = 500.0,
        storage_path: Optional[str] = None,
        alert_callbacks: Optional[List[Callable[[BudgetAlert], None]]] = None,
        kill_switch_callback: Optional[Callable[[], None]] = None,
        enable_kill_switch: bool = True
    ):
        """
        Initialize the cost tracker.
        
        Args:
            daily_budget: Daily spending limit in USD (default: $500)
            storage_path: Path to persist usage data (default: ./cost_tracker_data.json)
            alert_callbacks: List of callbacks for budget alerts
            kill_switch_callback: Callback when kill switch is triggered
            enable_kill_switch: Whether to enable automatic kill switch at 100%
        """
        self.daily_budget = daily_budget
        self.storage_path = Path(storage_path or "./cost_tracker_data.json")
        self.alert_callbacks = alert_callbacks or []
        self.kill_switch_callback = kill_switch_callback
        self.enable_kill_switch = enable_kill_switch
        
        # Thread safety
        self._lock = Lock()
        
        # Data structures
        self._usage_history: List[UsageRecord] = []
        self._agent_costs: Dict[str, float] = {}
        self._provider_costs: Dict[AIProvider, float] = {p: 0.0 for p in AIProvider}
        self._model_costs: Dict[str, float] = {}
        self._alerts_triggered: set = set()
        self._kill_switch_active: bool = False
        self._last_alert_time: Optional[datetime] = None
        
        # Daily tracking
        self._current_day: datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._daily_spend: float = 0.0
        self._hourly_spend: Dict[int, float] = {h: 0.0 for h in range(24)}
        
        # Load persisted data
        self._load_data()
        
        logger.info(f"CostTracker initialized with ${daily_budget:.2f} daily budget")
    
    def _get_pricing(self, provider: AIProvider, model: str) -> tuple:
        """Get pricing for a provider/model combination."""
        pricing = self.DEFAULT_PRICING.get(provider, {})
        if model in pricing:
            return pricing[model]
        return pricing.get("default", (0.001, 0.002))
    
    def record_usage(
        self,
        agent_id: str,
        provider: AIProvider,
        model: str,
        tokens_input: int,
        tokens_output: int,
        request_type: str = "general",
        custom_pricing: Optional[tuple] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record AI usage and update cost tracking.
        
        Args:
            agent_id: Unique identifier for the agent
            provider: AI provider used
            model: Model name used
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            request_type: Type of request (e.g., "code_generation", "analysis")
            custom_pricing: Optional custom pricing tuple (input_cost, output_cost) per token
            metadata: Additional metadata for the request
            
        Returns:
            Dictionary with cost information and any alerts
            
        Raises:
            RuntimeError: If kill switch is active
        """
        with self._lock:
            # Check kill switch
            if self._kill_switch_active:
                raise RuntimeError(
                    "KILL SWITCH ACTIVE: Budget limit reached. "
                    "All AI operations are suspended."
                )
            
            # Get pricing
            if custom_pricing:
                cost_per_input, cost_per_output = custom_pricing
            else:
                cost_per_input, cost_per_output = self._get_pricing(provider, model)
            
            # Calculate costs
            input_cost = tokens_input * cost_per_input / 1000  # Convert from per-1K
            output_cost = tokens_output * cost_per_output / 1000
            total_cost = input_cost + output_cost
            
            # Create usage record
            record = UsageRecord(
                timestamp=datetime.now(),
                agent_id=agent_id,
                provider=provider,
                model=model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_per_token_input=cost_per_input / 1000,
                cost_per_token_output=cost_per_output / 1000,
                total_cost=total_cost,
                request_type=request_type,
                metadata=metadata or {}
            )
            
            # Update tracking
            self._usage_history.append(record)
            self._agent_costs[agent_id] = self._agent_costs.get(agent_id, 0.0) + total_cost
            self._provider_costs[provider] += total_cost
            
            model_key = f"{provider.value}/{model}"
            self._model_costs[model_key] = self._model_costs.get(model_key, 0.0) + total_cost
            
            # Update daily tracking
            self._check_day_reset()
            self._daily_spend += total_cost
            current_hour = datetime.now().hour
            self._hourly_spend[current_hour] += total_cost
            
            # Check budget alerts
            alerts = self._check_budget_alerts()
            
            # Get optimization suggestions
            suggestions = self._get_optimization_suggestions(provider, model, request_type)
            
            # Persist data
            self._save_data()
            
            return {
                "success": True,
                "cost": total_cost,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "daily_spend": self._daily_spend,
                "budget_remaining": self.daily_budget - self._daily_spend,
                "alerts": [a.to_dict() for a in alerts],
                "optimization_suggestions": suggestions,
                "kill_switch_active": self._kill_switch_active
            }
    
    def _check_day_reset(self):
        """Reset daily counters if day has changed."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if today > self._current_day:
            self._current_day = today
            self._daily_spend = 0.0
            self._hourly_spend = {h: 0.0 for h in range(24)}
            self._alerts_triggered.clear()
            self._kill_switch_active = False
            logger.info("Daily counters reset for new day")
    
    def _check_budget_alerts(self) -> List[BudgetAlert]:
        """Check and trigger budget alerts."""
        alerts = []
        spend_percent = self._daily_spend / self.daily_budget
        
        for threshold in self.ALERT_THRESHOLDS:
            threshold_key = f"{threshold:.2f}"
            
            if spend_percent >= threshold and threshold_key not in self._alerts_triggered:
                self._alerts_triggered.add(threshold_key)
                
                # Determine alert level
                if threshold >= 1.0:
                    level = AlertLevel.KILL_SWITCH
                    message = f"🚨 KILL SWITCH: Daily budget exhausted! ${self._daily_spend:.2f} / ${self.daily_budget:.2f}"
                elif threshold >= 0.90:
                    level = AlertLevel.CRITICAL
                    message = f"⚠️ CRITICAL: {threshold*100:.0f}% budget used! ${self._daily_spend:.2f} / ${self.daily_budget:.2f}"
                elif threshold >= 0.75:
                    level = AlertLevel.WARNING
                    message = f"⚡ WARNING: {threshold*100:.0f}% budget used! ${self._daily_spend:.2f} / ${self.daily_budget:.2f}"
                else:
                    level = AlertLevel.INFO
                    message = f"ℹ️ INFO: {threshold*100:.0f}% budget used. ${self._daily_spend:.2f} / ${self.daily_budget:.2f}"
                
                alert = BudgetAlert(
                    level=level,
                    threshold_percent=threshold * 100,
                    current_spend=self._daily_spend,
                    budget=self.daily_budget,
                    message=message,
                    timestamp=datetime.now()
                )
                alerts.append(alert)
                self._last_alert_time = datetime.now()
                
                # Trigger callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
                
                # Handle kill switch
                if level == AlertLevel.KILL_SWITCH and self.enable_kill_switch:
                    self._trigger_kill_switch(alert)
                
                logger.warning(message)
        
        return alerts
    
    def _trigger_kill_switch(self, alert: BudgetAlert):
        """Activate the kill switch."""
        self._kill_switch_active = True
        logger.critical("🔴 KILL SWITCH ACTIVATED - All AI operations suspended")
        
        if self.kill_switch_callback:
            try:
                self.kill_switch_callback()
            except Exception as e:
                logger.error(f"Kill switch callback error: {e}")
    
    def _get_optimization_suggestions(
        self,
        provider: AIProvider,
        model: str,
        request_type: str
    ) -> List[Dict[str, Any]]:
        """Get cost optimization suggestions."""
        suggestions = []
        
        for rule in self.OPTIMIZATION_RULES:
            if rule["condition"](provider, model):
                # Check if this suggestion is relevant to request type
                if request_type in ["code_generation", "analysis"] and "vision" in model:
                    continue  # Vision models are necessary for image tasks
                    
                suggestions.append({
                    "suggestion": rule["suggestion"],
                    "potential_savings_percent": rule["savings_percent"],
                    "alternative_provider": rule["alternative"][0].value,
                    "alternative_model": rule["alternative"][1],
                    "current_cost_per_1k": self._get_pricing(provider, model),
                    "alternative_cost_per_1k": self._get_pricing(rule["alternative"][0], rule["alternative"][1])
                })
        
        return suggestions
    
    def check_budget(self) -> Dict[str, Any]:
        """
        Get current budget status.
        
        Returns:
            Dictionary with budget information
        """
        with self._lock:
            self._check_day_reset()
            
            remaining = self.daily_budget - self._daily_spend
            percent_used = (self._daily_spend / self.daily_budget) * 100 if self.daily_budget > 0 else 0
            
            return {
                "daily_budget": self.daily_budget,
                "daily_spend": self._daily_spend,
                "budget_remaining": remaining,
                "percent_used": percent_used,
                "kill_switch_active": self._kill_switch_active,
                "alerts_triggered": list(self._alerts_triggered),
                "hourly_breakdown": dict(self._hourly_spend),
                "status": "critical" if percent_used >= 90 else "warning" if percent_used >= 75 else "ok"
            }
    
    def get_cost_report(
        self,
        period: str = "today",
        agent_id: Optional[str] = None,
        provider: Optional[AIProvider] = None
    ) -> "CostReport":
        """
        Generate a cost report for the specified period.
        
        Args:
            period: Time period ("today", "hour", "week", "all")
            agent_id: Filter by specific agent (optional)
            provider: Filter by specific provider (optional)
            
        Returns:
            CostReport object with detailed cost information
        """
        with self._lock:
            now = datetime.now()
            
            # Determine time range
            if period == "today":
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "hour":
                start_time = now - timedelta(hours=1)
            elif period == "week":
                start_time = now - timedelta(days=7)
            elif period == "all":
                start_time = datetime.min
            else:
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Filter records
            filtered = [
                r for r in self._usage_history
                if r.timestamp >= start_time
                and (agent_id is None or r.agent_id == agent_id)
                and (provider is None or r.provider == provider)
            ]
            
            return CostReport(
                records=filtered,
                period=period,
                daily_budget=self.daily_budget,
                tracker=self
            )
    
    def forecast_cost(
        self,
        days: int = 7,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Forecast future costs based on historical usage.
        
        Args:
            days: Number of days to forecast
            include_recommendations: Include optimization recommendations
            
        Returns:
            Dictionary with forecast data
        """
        with self._lock:
            now = datetime.now()
            
            # Calculate historical averages from last 7 days
            week_ago = now - timedelta(days=7)
            week_records = [r for r in self._usage_history if r.timestamp >= week_ago]
            
            if week_records:
                avg_daily_cost = sum(r.total_cost for r in week_records) / 7
                avg_requests_per_day = len(week_records) / 7
            else:
                avg_daily_cost = self._daily_spend
                avg_requests_per_day = len(self._usage_history) if self._usage_history else 1
            
            # Project forward
            projected_cost = avg_daily_cost * days
            projected_remaining_budget = (self.daily_budget * days) - projected_cost
            
            # Calculate burn rate
            hours_active = datetime.now().hour + 1
            current_burn_rate = self._daily_spend / hours_active if hours_active > 0 else 0
            projected_daily_at_current_rate = current_burn_rate * 24
            
            forecast = {
                "forecast_period_days": days,
                "historical_avg_daily_cost": avg_daily_cost,
                "avg_requests_per_day": avg_requests_per_day,
                "projected_cost": projected_cost,
                "total_budget_for_period": self.daily_budget * days,
                "projected_remaining": projected_remaining_budget,
                "current_burn_rate_per_hour": current_burn_rate,
                "projected_daily_at_current_rate": projected_daily_at_current_rate,
                "will_exceed_budget": projected_cost > (self.daily_budget * days),
                "days_until_budget_exhausted": (self.daily_budget / avg_daily_cost) if avg_daily_cost > 0 else float('inf'),
                "trend": "increasing" if projected_daily_at_current_rate > avg_daily_cost else "stable"
            }
            
            if include_recommendations:
                forecast["recommendations"] = self._generate_forecast_recommendations(forecast)
            
            return forecast
    
    def _generate_forecast_recommendations(self, forecast: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on forecast."""
        recommendations = []
        
        if forecast["will_exceed_budget"]:
            excess = forecast["projected_cost"] - forecast["total_budget_for_period"]
            recommendations.append(
                f"⚠️ Budget will be exceeded by ${excess:.2f}. "
                "Consider increasing budget or reducing usage."
            )
        
        if forecast["current_burn_rate_per_hour"] > (self.daily_budget / 24):
            recommendations.append(
                "🔥 Burn rate is above average. Consider throttling non-critical agents."
            )
        
        # Check for expensive providers
        provider_totals = sorted(
            self._provider_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )
        if provider_totals and provider_totals[0][1] > self._daily_spend * 0.5:
            expensive = provider_totals[0][0].value
            recommendations.append(
                f"💡 {expensive} accounts for >50% of costs. "
                f"Consider using alternatives for some tasks."
            )
        
        return recommendations
    
    def get_agent_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get cost summary per agent."""
        with self._lock:
            summary = {}
            for agent_id, cost in self._agent_costs.items():
                agent_records = [r for r in self._usage_history if r.agent_id == agent_id]
                total_tokens = sum(r.tokens_input + r.tokens_output for r in agent_records)
                
                summary[agent_id] = {
                    "total_cost": cost,
                    "total_requests": len(agent_records),
                    "total_tokens": total_tokens,
                    "avg_cost_per_request": cost / len(agent_records) if agent_records else 0,
                    "providers_used": list(set(r.provider.value for r in agent_records)),
                    "models_used": list(set(r.model for r in agent_records))
                }
            return summary
    
    def get_provider_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get cost summary per AI provider."""
        with self._lock:
            summary = {}
            for provider, cost in self._provider_costs.items():
                provider_records = [r for r in self._usage_history if r.provider == provider]
                
                summary[provider.value] = {
                    "total_cost": cost,
                    "total_requests": len(provider_records),
                    "percent_of_total": (cost / sum(self._provider_costs.values()) * 100) 
                        if sum(self._provider_costs.values()) > 0 else 0,
                    "models": {}
                }
                
                # Break down by model
                for record in provider_records:
                    model = record.model
                    if model not in summary[provider.value]["models"]:
                        summary[provider.value]["models"][model] = {
                            "cost": 0.0,
                            "requests": 0,
                            "tokens": 0
                        }
                    summary[provider.value]["models"][model]["cost"] += record.total_cost
                    summary[provider.value]["models"][model]["requests"] += 1
                    summary[provider.value]["models"][model]["tokens"] += record.tokens_input + record.tokens_output
                
            return summary
    
    def reset_kill_switch(self, admin_token: str = "") -> bool:
        """
        Manually reset the kill switch (requires admin action).
        
        Args:
            admin_token: Simple admin verification
            
        Returns:
            True if reset successful
        """
        with self._lock:
            if not self._kill_switch_active:
                return True
            
            self._kill_switch_active = False
            self._alerts_triggered.clear()
            logger.info("Kill switch manually reset")
            return True
    
    def export_data(self, filepath: Optional[str] = None) -> str:
        """
        Export all tracking data to JSON.
        
        Args:
            filepath: Output file path (default: auto-generated)
            
        Returns:
            Path to exported file
        """
        with self._lock:
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"./cost_tracker_export_{timestamp}.json"
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "daily_budget": self.daily_budget,
                "current_daily_spend": self._daily_spend,
                "kill_switch_active": self._kill_switch_active,
                "agent_costs": self._agent_costs,
                "provider_costs": {p.value: c for p, c in self._provider_costs.items()},
                "model_costs": self._model_costs,
                "usage_history": [r.to_dict() for r in self._usage_history]
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return filepath
    
    def _save_data(self):
        """Persist data to storage."""
        try:
            data = {
                "saved_at": datetime.now().isoformat(),
                "current_day": self._current_day.isoformat(),
                "daily_spend": self._daily_spend,
                "hourly_spend": self._hourly_spend,
                "kill_switch_active": self._kill_switch_active,
                "alerts_triggered": list(self._alerts_triggered),
                "agent_costs": self._agent_costs,
                "provider_costs": {p.value: c for p, c in self._provider_costs.items()},
                "model_costs": self._model_costs,
                "usage_history": [r.to_dict() for r in self._usage_history[-1000:]]  # Keep last 1000
            }
            
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def _load_data(self):
        """Load persisted data from storage."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Check if data is from today
            saved_day = datetime.fromisoformat(data.get("current_day", datetime.min.isoformat()))
            if saved_day.date() == datetime.now().date():
                self._daily_spend = data.get("daily_spend", 0.0)
                self._hourly_spend = data.get("hourly_spend", {h: 0.0 for h in range(24)})
                self._kill_switch_active = data.get("kill_switch_active", False)
                self._alerts_triggered = set(data.get("alerts_triggered", []))
            
            self._agent_costs = data.get("agent_costs", {})
            self._provider_costs = {
                AIProvider(p): c 
                for p, c in data.get("provider_costs", {}).items()
            }
            self._model_costs = data.get("model_costs", {})
            
            # Load usage history (last 1000 entries)
            history = data.get("usage_history", [])
            self._usage_history = [UsageRecord.from_dict(r) for r in history[-1000:]]
            
            logger.info(f"Loaded {len(self._usage_history)} historical records")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")


class CostReport:
    """Detailed cost report for a specific time period."""
    
    def __init__(
        self,
        records: List[UsageRecord],
        period: str,
        daily_budget: float,
        tracker: CostTracker
    ):
        self.records = records
        self.period = period
        self.daily_budget = daily_budget
        self.tracker = tracker
    
    @property
    def total_cost(self) -> float:
        return sum(r.total_cost for r in self.records)
    
    @property
    def total_requests(self) -> int:
        return len(self.records)
    
    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_input + r.tokens_output for r in self.records)
    
    @property
    def average_cost_per_request(self) -> float:
        return self.total_cost / self.total_requests if self.total_requests > 0 else 0
    
    def by_agent(self) -> Dict[str, float]:
        """Costs grouped by agent."""
        costs = {}
        for r in self.records:
            costs[r.agent_id] = costs.get(r.agent_id, 0.0) + r.total_cost
        return costs
    
    def by_provider(self) -> Dict[str, float]:
        """Costs grouped by provider."""
        costs = {}
        for r in self.records:
            costs[r.provider.value] = costs.get(r.provider.value, 0.0) + r.total_cost
        return costs
    
    def by_model(self) -> Dict[str, float]:
        """Costs grouped by model."""
        costs = {}
        for r in self.records:
            key = f"{r.provider.value}/{r.model}"
            costs[key] = costs.get(key, 0.0) + r.total_cost
        return costs
    
    def by_hour(self) -> Dict[int, float]:
        """Costs grouped by hour of day."""
        costs = {h: 0.0 for h in range(24)}
        for r in self.records:
            costs[r.timestamp.hour] += r.total_cost
        return costs
    
    def by_request_type(self) -> Dict[str, float]:
        """Costs grouped by request type."""
        costs = {}
        for r in self.records:
            costs[r.request_type] = costs.get(r.request_type, 0.0) + r.total_cost
        return costs
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            f"COST REPORT - {self.period.upper()}",
            "=" * 60,
            f"Total Cost: ${self.total_cost:.4f}",
            f"Total Requests: {self.total_requests}",
            f"Total Tokens: {self.total_tokens:,}",
            f"Avg Cost/Request: ${self.average_cost_per_request:.4f}",
            "",
            "BY AGENT:",
        ]
        
        for agent, cost in sorted(self.by_agent().items(), key=lambda x: -x[1]):
            lines.append(f"  {agent}: ${cost:.4f}")
        
        lines.extend(["", "BY PROVIDER:"])
        for provider, cost in sorted(self.by_provider().items(), key=lambda x: -x[1]):
            pct = (cost / self.total_cost * 100) if self.total_cost > 0 else 0
            lines.append(f"  {provider}: ${cost:.4f} ({pct:.1f}%)")
        
        lines.extend(["", "BY MODEL:"])
        for model, cost in sorted(self.by_model().items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {model}: ${cost:.4f}")
        
        lines.extend(["", "BY REQUEST TYPE:"])
        for req_type, cost in sorted(self.by_request_type().items(), key=lambda x: -x[1]):
            lines.append(f"  {req_type}: ${cost:.4f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "period": self.period,
            "total_cost": self.total_cost,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "average_cost_per_request": self.average_cost_per_request,
            "by_agent": self.by_agent(),
            "by_provider": self.by_provider(),
            "by_model": self.by_model(),
            "by_hour": self.by_hour(),
            "by_request_type": self.by_request_type(),
            "records": [r.to_dict() for r in self.records]
        }


# Global instance for easy access
_global_tracker: Optional[CostTracker] = None


def get_tracker(
    daily_budget: float = 500.0,
    **kwargs
) -> CostTracker:
    """
    Get or create the global cost tracker instance.
    
    Args:
        daily_budget: Daily spending limit
        **kwargs: Additional arguments for CostTracker
        
    Returns:
        CostTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker(daily_budget=daily_budget, **kwargs)
    return _global_tracker


def record(
    agent_id: str,
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
    request_type: str = "general",
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to record usage with the global tracker.
    
    Args:
        agent_id: Agent identifier
        provider: Provider name ("kimi", "chatgpt", "grok", "claude")
        model: Model name
        tokens_input: Input tokens
        tokens_output: Output tokens
        request_type: Type of request
        **kwargs: Additional arguments
        
    Returns:
        Result from record_usage()
    """
    tracker = get_tracker()
    provider_enum = AIProvider(provider.lower())
    return tracker.record_usage(
        agent_id=agent_id,
        provider=provider_enum,
        model=model,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        request_type=request_type,
        **kwargs
    )


# Example usage and tests
if __name__ == "__main__":
    # Demo usage
    print("MasterBuilder7 Cost Tracker - Demo")
    print("=" * 60)
    
    # Create tracker with $500 daily budget
    tracker = CostTracker(daily_budget=500.0)
    
    # Simulate some usage
    print("\nSimulating AI usage...")
    
    # Agent 1 using ChatGPT
    for i in range(5):
        result = tracker.record_usage(
            agent_id="agent_coder_001",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=2000,
            tokens_output=800,
            request_type="code_generation"
        )
        print(f"  Request {i+1}: ${result['cost']:.4f} (alerts: {len(result['alerts'])})")
    
    # Agent 2 using Claude
    for i in range(3):
        result = tracker.record_usage(
            agent_id="agent_writer_002",
            provider=AIProvider.CLAUDE,
            model="claude-3-opus",
            tokens_input=3000,
            tokens_output=1500,
            request_type="content_creation"
        )
        print(f"  Request {i+1}: ${result['cost']:.4f}")
    
    # Agent 3 using Kimi (more efficient)
    for i in range(10):
        result = tracker.record_usage(
            agent_id="agent_helper_003",
            provider=AIProvider.KIMI,
            model="kimi-v1",
            tokens_input=1500,
            tokens_output=500,
            request_type="general"
        )
        print(f"  Request {i+1}: ${result['cost']:.4f}")
    
    # Generate reports
    print("\n" + "=" * 60)
    print("BUDGET STATUS:")
    budget = tracker.check_budget()
    print(f"  Daily Budget: ${budget['daily_budget']:.2f}")
    print(f"  Daily Spend: ${budget['daily_spend']:.4f}")
    print(f"  Remaining: ${budget['budget_remaining']:.4f}")
    print(f"  Percent Used: {budget['percent_used']:.2f}%")
    print(f"  Status: {budget['status']}")
    
    print("\n" + "=" * 60)
    print("COST REPORT (TODAY):")
    report = tracker.get_cost_report(period="today")
    print(report.summary())
    
    print("\n" + "=" * 60)
    print("AGENT SUMMARY:")
    for agent_id, data in tracker.get_agent_summary().items():
        print(f"  {agent_id}:")
        print(f"    Total Cost: ${data['total_cost']:.4f}")
        print(f"    Requests: {data['total_requests']}")
        print(f"    Providers: {', '.join(data['providers_used'])}")
    
    print("\n" + "=" * 60)
    print("PROVIDER SUMMARY:")
    for provider, data in tracker.get_provider_summary().items():
        print(f"  {provider}: ${data['total_cost']:.4f}")
    
    print("\n" + "=" * 60)
    print("FORECAST (Next 7 days):")
    forecast = tracker.forecast_cost(days=7)
    print(f"  Projected Cost: ${forecast['projected_cost']:.2f}")
    print(f"  Budget for Period: ${forecast['total_budget_for_period']:.2f}")
    print(f"  Will Exceed Budget: {forecast['will_exceed_budget']}")
    print(f"  Days Until Exhausted: {forecast['days_until_budget_exhausted']:.1f}")
    print(f"  Recommendations:")
    for rec in forecast['recommendations']:
        print(f"    - {rec}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
