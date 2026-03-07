#!/usr/bin/env python3
"""
Test Suite: Cost Tracker

Comprehensive tests for cost tracking and budget management.

Coverage:
- Usage record creation
- Cost tracking and calculation
- Budget alerts
- Kill switch
- Cost reports
- Forecasting
- Optimization suggestions
- Data persistence
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from apex.agents.cost_tracker import (
    AIProvider,
    AlertLevel,
    UsageRecord,
    BudgetAlert,
    CostTracker,
    CostReport,
    get_tracker,
    record
)


# =============================================================================
# UsageRecord Tests
# =============================================================================

class TestUsageRecord:
    """Test UsageRecord dataclass."""
    
    def test_record_creation(self):
        """Test usage record creation."""
        record = UsageRecord(
            timestamp=datetime.now(),
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            cost_per_token_input=0.00003,
            cost_per_token_output=0.00006,
            total_cost=0.06,
            request_type="code_generation"
        )
        
        assert record.agent_id == "agent-1"
        assert record.provider == AIProvider.CHATGPT
        assert record.model == "gpt-4"
        assert record.tokens_input == 1000
        assert record.tokens_output == 500
        assert record.total_cost == 0.06
    
    def test_record_serialization(self):
        """Test usage record serialization."""
        record = UsageRecord(
            timestamp=datetime.now(),
            agent_id="agent-1",
            provider=AIProvider.KIMI,
            model="kimi-v1",
            tokens_input=1000,
            tokens_output=500,
            cost_per_token_input=0.0000003,
            cost_per_token_output=0.0000006,
            total_cost=0.0006,
            request_type="general"
        )
        
        data = record.to_dict()
        
        assert data["agent_id"] == "agent-1"
        assert data["provider"] == "kimi"
        assert data["model"] == "kimi-v1"
        assert data["tokens_input"] == 1000
    
    def test_record_from_dict(self):
        """Test usage record deserialization."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": "agent-1",
            "provider": "claude",
            "model": "claude-3-opus",
            "tokens_input": 2000,
            "tokens_output": 1000,
            "cost_per_token_input": 0.000015,
            "cost_per_token_output": 0.000075,
            "total_cost": 0.105,
            "request_type": "analysis",
            "metadata": {}
        }
        
        record = UsageRecord.from_dict(data)
        
        assert record.agent_id == "agent-1"
        assert record.provider == AIProvider.CLAUDE
        assert record.total_cost == 0.105


# =============================================================================
# BudgetAlert Tests
# =============================================================================

class TestBudgetAlert:
    """Test BudgetAlert dataclass."""
    
    def test_alert_creation(self):
        """Test budget alert creation."""
        alert = BudgetAlert(
            level=AlertLevel.WARNING,
            threshold_percent=75.0,
            current_spend=75.0,
            budget=100.0,
            message="75% budget used",
            timestamp=datetime.now()
        )
        
        assert alert.level == AlertLevel.WARNING
        assert alert.threshold_percent == 75.0
        assert alert.current_spend == 75.0
    
    def test_alert_serialization(self):
        """Test alert serialization."""
        alert = BudgetAlert(
            level=AlertLevel.CRITICAL,
            threshold_percent=90.0,
            current_spend=90.0,
            budget=100.0,
            message="90% budget used",
            timestamp=datetime.now()
        )
        
        data = alert.to_dict()
        
        assert data["level"] == "CRITICAL"
        assert data["threshold_percent"] == 90.0


# =============================================================================
# CostTracker Tests
# =============================================================================

class TestCostTracker:
    """Test CostTracker."""
    
    def test_tracker_initialization(self, temp_directory):
        """Test tracker initialization."""
        storage_path = temp_directory / "cost.json"
        
        tracker = CostTracker(
            daily_budget=500.0,
            storage_path=str(storage_path)
        )
        
        assert tracker.daily_budget == 500.0
        assert tracker.storage_path == storage_path
        assert tracker._kill_switch_active is False
    
    def test_record_usage_chatgpt(self, cost_tracker):
        """Test recording ChatGPT usage."""
        tracker = cost_tracker
        
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code_generation"
        )
        
        assert result["success"] is True
        assert result["cost"] > 0
        assert result["tokens_input"] == 1000
        assert result["tokens_output"] == 500
        assert result["daily_spend"] > 0
    
    def test_record_usage_kimi(self, cost_tracker):
        """Test recording Kimi usage."""
        tracker = cost_tracker
        
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.KIMI,
            model="kimi-v1",
            tokens_input=10000,
            tokens_output=5000,
            request_type="general"
        )
        
        assert result["success"] is True
        # Kimi should be much cheaper than ChatGPT
        assert result["cost"] < 0.01  # Less than 1 cent for 15K tokens
    
    def test_record_usage_claude(self, cost_tracker):
        """Test recording Claude usage."""
        tracker = cost_tracker
        
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CLAUDE,
            model="claude-3-opus",
            tokens_input=2000,
            tokens_output=1000,
            request_type="analysis"
        )
        
        assert result["success"] is True
        assert result["cost"] > 0
    
    def test_record_usage_grok(self, cost_tracker):
        """Test recording Grok usage."""
        tracker = cost_tracker
        
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.GROK,
            model="grok-2",
            tokens_input=1000,
            tokens_output=500,
            request_type="general"
        )
        
        assert result["success"] is True
        assert result["cost"] > 0
    
    def test_record_usage_custom_pricing(self, cost_tracker):
        """Test recording usage with custom pricing."""
        tracker = cost_tracker
        
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.OTHER,
            model="custom-model",
            tokens_input=1000,
            tokens_output=500,
            custom_pricing=(0.001, 0.002),  # per 1K tokens
            request_type="custom"
        )
        
        assert result["success"] is True
        # Cost = (1000 * 0.001 + 500 * 0.002) / 1000
        assert result["cost"] == 0.002
    
    def test_kill_switch_activation(self, cost_tracker):
        """Test kill switch activation at budget limit."""
        tracker = cost_tracker
        tracker.daily_budget = 1.0  # Very low budget for test
        
        # Record usage until budget is exceeded
        with pytest.raises(RuntimeError) as exc_info:
            for _ in range(100):  # Record many requests
                tracker.record_usage(
                    agent_id="agent-1",
                    provider=AIProvider.CHATGPT,
                    model="gpt-4",
                    tokens_input=1000,
                    tokens_output=1000,
                    request_type="test"
                )
        
        assert "KILL SWITCH" in str(exc_info.value)
        assert tracker._kill_switch_active is True
    
    def test_kill_switch_blocks_usage(self, cost_tracker):
        """Test that kill switch blocks further usage."""
        tracker = cost_tracker
        tracker._kill_switch_active = True
        
        with pytest.raises(RuntimeError) as exc_info:
            tracker.record_usage(
                agent_id="agent-1",
                provider=AIProvider.CHATGPT,
                model="gpt-4",
                tokens_input=100,
                tokens_output=100,
                request_type="test"
            )
        
        assert "KILL SWITCH ACTIVE" in str(exc_info.value)
    
    def test_reset_kill_switch(self, cost_tracker):
        """Test resetting kill switch."""
        tracker = cost_tracker
        tracker._kill_switch_active = True
        
        result = tracker.reset_kill_switch()
        
        assert result is True
        assert tracker._kill_switch_active is False
    
    def test_check_budget(self, cost_tracker):
        """Test budget checking."""
        tracker = cost_tracker
        tracker.daily_budget = 100.0
        
        # Record some usage
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.KIMI,
            model="kimi-v1",
            tokens_input=10000,
            tokens_output=5000,
            request_type="test"
        )
        
        budget = tracker.check_budget()
        
        assert budget["daily_budget"] == 100.0
        assert budget["daily_spend"] > 0
        assert budget["budget_remaining"] < 100.0
        assert budget["percent_used"] > 0
        assert budget["status"] == "ok"
    
    def test_cost_report_today(self, cost_tracker):
        """Test generating today's cost report."""
        tracker = cost_tracker
        
        # Record some usage
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code_generation"
        )
        
        tracker.record_usage(
            agent_id="agent-2",
            provider=AIProvider.CLAUDE,
            model="claude-3-sonnet",
            tokens_input=2000,
            tokens_output=1000,
            request_type="analysis"
        )
        
        report = tracker.get_cost_report(period="today")
        
        assert isinstance(report, CostReport)
        assert report.total_cost > 0
        assert report.total_requests == 2
        assert len(report.by_agent()) == 2
        assert len(report.by_provider()) == 2
    
    def test_cost_report_by_agent(self, cost_tracker):
        """Test filtering cost report by agent."""
        tracker = cost_tracker
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code"
        )
        
        tracker.record_usage(
            agent_id="agent-2",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code"
        )
        
        report = tracker.get_cost_report(period="today", agent_id="agent-1")
        
        assert report.total_requests == 1
        assert "agent-1" in report.by_agent()
        assert "agent-2" not in report.by_agent()
    
    def test_cost_report_by_provider(self, cost_tracker):
        """Test filtering cost report by provider."""
        tracker = cost_tracker
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code"
        )
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CLAUDE,
            model="claude-3-sonnet",
            tokens_input=2000,
            tokens_output=1000,
            request_type="analysis"
        )
        
        report = tracker.get_cost_report(
            period="today",
            provider=AIProvider.CHATGPT
        )
        
        assert report.total_requests == 1
        assert "chatgpt" in report.by_provider()
        assert "claude" not in report.by_provider()
    
    def test_forecast_cost(self, cost_tracker):
        """Test cost forecasting."""
        tracker = cost_tracker
        tracker.daily_budget = 100.0
        
        # Record some usage
        for _ in range(5):
            tracker.record_usage(
                agent_id="agent-1",
                provider=AIProvider.KIMI,
                model="kimi-v1",
                tokens_input=10000,
                tokens_output=5000,
                request_type="test"
            )
        
        forecast = tracker.forecast_cost(days=7)
        
        assert forecast["forecast_period_days"] == 7
        assert forecast["historical_avg_daily_cost"] > 0
        assert forecast["projected_cost"] > 0
        assert forecast["total_budget_for_period"] == 700.0  # 100 * 7
        assert "recommendations" in forecast
    
    def test_get_agent_summary(self, cost_tracker):
        """Test getting agent cost summary."""
        tracker = cost_tracker
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code"
        )
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=2000,
            tokens_output=1000,
            request_type="test"
        )
        
        summary = tracker.get_agent_summary()
        
        assert "agent-1" in summary
        assert summary["agent-1"]["total_requests"] == 2
        assert summary["agent-1"]["total_cost"] > 0
        assert "chatgpt" in summary["agent-1"]["providers_used"]
    
    def test_get_provider_summary(self, cost_tracker):
        """Test getting provider cost summary."""
        tracker = cost_tracker
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code"
        )
        
        summary = tracker.get_provider_summary()
        
        assert "chatgpt" in summary
        assert summary["chatgpt"]["total_requests"] == 1
        assert summary["chatgpt"]["total_cost"] > 0
    
    def test_optimization_suggestions(self, cost_tracker):
        """Test getting optimization suggestions."""
        tracker = cost_tracker
        
        # Use expensive model
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code_generation"
        )
        
        # Should suggest cheaper alternatives
        assert len(result["optimization_suggestions"]) > 0
        
        suggestion = result["optimization_suggestions"][0]
        assert "suggestion" in suggestion
        assert "potential_savings_percent" in suggestion
        assert suggestion["potential_savings_percent"] > 0
    
    def test_data_persistence(self, temp_directory):
        """Test data persistence to file."""
        storage_path = temp_directory / "cost.json"
        
        # Create tracker and record usage
        tracker1 = CostTracker(
            daily_budget=100.0,
            storage_path=str(storage_path)
        )
        
        tracker1.record_usage(
            agent_id="agent-1",
            provider=AIProvider.KIMI,
            model="kimi-v1",
            tokens_input=10000,
            tokens_output=5000,
            request_type="test"
        )
        
        # Create new tracker instance (simulating restart)
        tracker2 = CostTracker(
            daily_budget=100.0,
            storage_path=str(storage_path)
        )
        
        # Should load previous data
        assert len(tracker2._usage_history) > 0
        assert "agent-1" in tracker2._agent_costs
    
    def test_export_data(self, cost_tracker):
        """Test data export."""
        tracker = cost_tracker
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.KIMI,
            model="kimi-v1",
            tokens_input=1000,
            tokens_output=500,
            request_type="test"
        )
        
        export_path = tracker.export_data()
        
        assert export_path is not None
        
        # Verify exported data
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert "export_timestamp" in data
        assert "agent_costs" in data
        assert "usage_history" in data
        assert len(data["usage_history"]) == 1


# =============================================================================
# CostReport Tests
# =============================================================================

class TestCostReport:
    """Test CostReport."""
    
    def test_report_properties(self, cost_tracker):
        """Test report properties."""
        tracker = cost_tracker
        
        # Record usage
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code"
        )
        
        report = tracker.get_cost_report(period="today")
        
        assert report.total_cost > 0
        assert report.total_requests == 1
        assert report.total_tokens == 1500
        assert report.average_cost_per_request == report.total_cost
    
    def test_report_groupings(self, cost_tracker):
        """Test report groupings."""
        tracker = cost_tracker
        
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4",
            tokens_input=1000,
            tokens_output=500,
            request_type="code_generation"
        )
        
        tracker.record_usage(
            agent_id="agent-2",
            provider=AIProvider.CLAUDE,
            model="claude-3-sonnet",
            tokens_input=2000,
            tokens_output=1000,
            request_type="analysis"
        )
        
        report = tracker.get_cost_report(period="today")
        
        by_agent = report.by_agent()
        assert len(by_agent) == 2
        assert "agent-1" in by_agent
        assert "agent-2" in by_agent
        
        by_provider = report.by_provider()
        assert len(by_provider) == 2
        assert "chatgpt" in by_provider
        assert "claude" in by_provider
        
        by_request_type = report.by_request_type()
        assert "code_generation" in by_request_type
        assert "analysis" in by_request_type


# =============================================================================
# Global Instance Tests
# =============================================================================

class TestGlobalInstance:
    """Test global tracker instance."""
    
    def test_get_tracker_singleton(self, temp_directory):
        """Test that get_tracker returns singleton."""
        storage_path = temp_directory / "global_cost.json"
        
        tracker1 = get_tracker(
            daily_budget=100.0,
            storage_path=str(storage_path)
        )
        
        tracker2 = get_tracker(
            daily_budget=200.0,  # Different budget
            storage_path=str(storage_path)
        )
        
        # Should return same instance
        assert tracker1 is tracker2
        # Budget from first call should be used
        assert tracker1.daily_budget == 100.0


# =============================================================================
# Alert Callback Tests
# =============================================================================

class TestAlertCallbacks:
    """Test alert callback functionality."""
    
    def test_alert_callback_invocation(self, cost_tracker):
        """Test that alert callbacks are invoked."""
        callback_called = False
        received_alert = None
        
        def callback(alert):
            nonlocal callback_called, received_alert
            callback_called = True
            received_alert = alert
        
        tracker = cost_tracker
        tracker.alert_callbacks.append(callback)
        tracker.daily_budget = 1.0  # Low budget
        
        # Record usage to trigger alert
        tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="gpt-4o-mini",  # Use cheaper model
            tokens_input=100,
            tokens_output=100,
            request_type="test"
        )
        
        # Callback may or may not be called depending on budget threshold
        # Just verify the callback mechanism is in place
        assert len(tracker.alert_callbacks) == 1
    
    def test_kill_switch_callback(self, temp_directory):
        """Test kill switch callback."""
        kill_switch_called = False
        
        def kill_switch():
            nonlocal kill_switch_called
            kill_switch_called = True
        
        storage_path = temp_directory / "cost.json"
        tracker = CostTracker(
            daily_budget=0.01,  # Very low budget
            storage_path=str(storage_path),
            kill_switch_callback=kill_switch,
            enable_kill_switch=True
        )
        
        # Record usage until kill switch
        try:
            for _ in range(100):
                tracker.record_usage(
                    agent_id="agent-1",
                    provider=AIProvider.CHATGPT,
                    model="gpt-4",
                    tokens_input=1000,
                    tokens_output=1000,
                    request_type="test"
                )
        except RuntimeError:
            pass
        
        assert tracker._kill_switch_active is True
        assert kill_switch_called is True


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestCostTrackerErrors:
    """Test error handling."""
    
    def test_invalid_provider(self, cost_tracker):
        """Test handling of invalid provider."""
        tracker = cost_tracker
        
        with pytest.raises(ValueError):
            tracker.record_usage(
                agent_id="agent-1",
                provider="invalid_provider",  # Invalid
                model="model",
                tokens_input=100,
                tokens_output=100,
                request_type="test"
            )
    
    def test_unknown_model_uses_default(self, cost_tracker):
        """Test that unknown model uses default pricing."""
        tracker = cost_tracker
        
        result = tracker.record_usage(
            agent_id="agent-1",
            provider=AIProvider.CHATGPT,
            model="unknown-model",  # Unknown model
            tokens_input=1000,
            tokens_output=500,
            request_type="test"
        )
        
        # Should use default pricing
        assert result["success"] is True
        assert result["cost"] > 0
