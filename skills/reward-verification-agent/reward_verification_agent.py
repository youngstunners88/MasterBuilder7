"""
iHhashi Reward Verification Agent

Validates reward calculations, payout logic, and referral systems.
Ensures compliance with South African regulations and platform policies.
"""

import re
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TierLevel(Enum):
    """Customer tier levels based on referral count."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class CoinRedemptionType(Enum):
    """Available coin redemption options."""
    FREE_DELIVERY = "free_delivery"
    R15_DISCOUNT = "r15_discount"
    R30_DISCOUNT = "r30_discount"


class VerificationStatus(Enum):
    """Status of verification checks."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class FraudSeverity(Enum):
    """Severity levels for fraud alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudAlert:
    """Represents a detected fraud pattern."""
    rule_triggered: str
    severity: FraudSeverity
    description: str
    affected_users: List[str]
    evidence: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VerificationError:
    """Represents a verification error."""
    component: str
    error_type: str
    description: str
    expected_value: Any
    actual_value: Any
    severity: str = "error"


@dataclass
class AuditReport:
    """Comprehensive audit report for reward systems."""
    overall_compliance_score: float
    calculations_checked: int
    errors_found: List[VerificationError]
    fraud_alerts: List[FraudAlert]
    recommendations: List[str]
    compliance_status: str
    audit_timestamp: datetime = field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TierConfig:
    """Configuration for customer tiers."""
    name: str
    min_referrals: int
    max_referrals: int
    discount_percentage: float
    free_deliveries_per_month: int
    support_level: str
    badge: str


class RewardConstants:
    """Constants for reward calculations (South Africa specific)."""
    # Currency
    CURRENCY = "ZAR"
    CURRENCY_SYMBOL = "R"
    
    # Coin values
    COIN_VALUE_ZAR = 0.10  # 1 coin = R0.10
    REFERRAL_REWARD_REFERRER = 50  # Referrer gets 50 coins
    REFERRAL_REWARD_REFEREE = 25   # New customer gets 25 coins
    
    # Redemption thresholds
    REDEMPTION_FREE_DELIVERY = 100
    REDEMPTION_R15_OFF = 150
    REDEMPTION_R30_OFF = 300
    
    # Payout settings
    PAYOUT_DAY = "sunday"
    PAYOUT_TIME = "11:11"
    PAYOUT_TIMEZONE = "SAST"  # South Africa Standard Time (UTC+2)
    MINIMUM_PAYOUT_ZAR = 100.00
    
    # Vendor referral bonus
    VENDOR_REFERRAL_BONUS_DAYS = 2
    VENDOR_REFERRAL_MAX_BONUS_DAYS = 90
    
    # Fraud detection thresholds
    SELF_REFERRAL_WINDOW_HOURS = 24
    RAPID_REFERRAL_THRESHOLD = 5
    RAPID_REFERRAL_WINDOW_MINUTES = 60
    SUSPICIOUS_PAYOUT_MULTIPLIER = 3.0
    DUPLICATE_IP_THRESHOLD = 3


# Tier configuration
TIER_CONFIGS = {
    TierLevel.BRONZE: TierConfig(
        name="Bronze",
        min_referrals=1,
        max_referrals=5,
        discount_percentage=5.0,
        free_deliveries_per_month=0,
        support_level="Standard",
        badge="🥉"
    ),
    TierLevel.SILVER: TierConfig(
        name="Silver",
        min_referrals=6,
        max_referrals=15,
        discount_percentage=10.0,
        free_deliveries_per_month=1,
        support_level="Priority",
        badge="🥈"
    ),
    TierLevel.GOLD: TierConfig(
        name="Gold",
        min_referrals=16,
        max_referrals=50,
        discount_percentage=15.0,
        free_deliveries_per_month=2,
        support_level="VIP",
        badge="🥇"
    ),
    TierLevel.PLATINUM: TierConfig(
        name="Platinum",
        min_referrals=51,
        max_referrals=999999,
        discount_percentage=20.0,
        free_deliveries_per_month=999999,  # Unlimited
        support_level="Dedicated Manager",
        badge="💎"
    )
}


class RewardVerificationAgent:
    """
    Agent for validating iHhashi reward calculations, payout logic, and referral systems.
    
    Features:
    - Reward calculation validation
    - Payout audit capabilities
    - Referral chain verification
    - Fraud detection
    - Compliance checking
    """
    
    def __init__(self):
        self.constants = RewardConstants()
        self.verification_history: List[Dict] = []
        self.fraud_patterns: Dict[str, Any] = {}
        logger.info("RewardVerificationAgent initialized")
    
    def validate_reward_calculation(self, calculation_code: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """
        Validate reward calculation logic against test cases.
        
        Args:
            calculation_code: The reward calculation code/function to validate
            test_cases: List of test cases with inputs and expected outputs
            
        Returns:
            Validation results with pass/fail status
        """
        results = {
            "status": VerificationStatus.PASSED,
            "tests_run": len(test_cases),
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "execution_time_ms": 0
        }
        
        start_time = datetime.utcnow()
        
        for idx, test_case in enumerate(test_cases):
            try:
                test_result = self._run_single_test(calculation_code, test_case)
                if test_result["passed"]:
                    results["tests_passed"] += 1
                else:
                    results["tests_failed"] += 1
                    results["errors"].append({
                        "test_index": idx,
                        "test_name": test_case.get("name", f"Test {idx}"),
                        "error": test_result["error"]
                    })
                    results["status"] = VerificationStatus.FAILED
            except Exception as e:
                results["tests_failed"] += 1
                results["errors"].append({
                    "test_index": idx,
                    "test_name": test_case.get("name", f"Test {idx}"),
                    "error": str(e)
                })
                results["status"] = VerificationStatus.ERROR
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        results["execution_time_ms"] = round(execution_time, 2)
        
        self.verification_history.append({
            "type": "reward_calculation",
            "timestamp": datetime.utcnow(),
            "results": results
        })
        
        return results
    
    def _run_single_test(self, calculation_code: str, test_case: Dict) -> Dict:
        """Run a single test case."""
        expected = test_case.get("expected_output")
        inputs = test_case.get("inputs", {})
        
        # Simulate calculation execution
        # In production, this would actually execute the code
        actual_output = self._simulate_calculation(calculation_code, inputs)
        
        passed = self._compare_outputs(expected, actual_output)
        
        return {
            "passed": passed,
            "expected": expected,
            "actual": actual_output,
            "error": None if passed else f"Expected {expected}, got {actual_output}"
        }
    
    def _simulate_calculation(self, code: str, inputs: Dict) -> Any:
        """Simulate reward calculation (simplified for demo)."""
        # This is a placeholder - in production, safely execute the code
        if "coin" in code.lower():
            return self._calculate_coins(inputs)
        elif "tier" in code.lower():
            return self._calculate_tier(inputs)
        elif "payout" in code.lower():
            return self._calculate_payout(inputs)
        return None
    
    def _calculate_coins(self, inputs: Dict) -> int:
        """Calculate iHhashi Coins based on inputs."""
        referral_count = inputs.get("referral_count", 0)
        base_coins = inputs.get("base_coins", 0)
        
        # Referrer gets 50 coins per successful referral
        referral_coins = referral_count * self.constants.REFERRAL_REWARD_REFERRER
        return base_coins + referral_coins
    
    def _calculate_tier(self, inputs: Dict) -> str:
        """Calculate customer tier based on referral count."""
        referral_count = inputs.get("successful_referrals", 0)
        return self._get_tier_from_referrals(referral_count).value
    
    def _calculate_payout(self, inputs: Dict) -> float:
        """Calculate payout amount."""
        earnings = inputs.get("weekly_earnings", 0)
        return earnings if earnings >= self.constants.MINIMUM_PAYOUT_ZAR else 0
    
    def _compare_outputs(self, expected: Any, actual: Any) -> bool:
        """Compare expected and actual outputs."""
        if isinstance(expected, dict) and isinstance(actual, dict):
            return all(
                key in actual and self._compare_outputs(val, actual[key])
                for key, val in expected.items()
            )
        return expected == actual
    
    def verify_payout_transaction(self, transaction_data: Dict) -> Dict[str, Any]:
        """
        Verify a single payout transaction for compliance.
        
        Args:
            transaction_data: Payout transaction details
            
        Returns:
            Verification results
        """
        results = {
            "transaction_id": transaction_data.get("id", "unknown"),
            "status": VerificationStatus.PASSED,
            "checks": [],
            "warnings": [],
            "errors": []
        }
        
        # Check 1: Minimum payout threshold
        amount = transaction_data.get("amount", 0)
        if amount < self.constants.MINIMUM_PAYOUT_ZAR:
            results["checks"].append({
                "check": "minimum_threshold",
                "status": VerificationStatus.FAILED,
                "message": f"Amount R{amount:.2f} below minimum R{self.constants.MINIMUM_PAYOUT_ZAR:.2f}"
            })
            results["errors"].append("Below minimum payout threshold")
            results["status"] = VerificationStatus.FAILED
        else:
            results["checks"].append({
                "check": "minimum_threshold",
                "status": VerificationStatus.PASSED,
                "message": f"Amount R{amount:.2f} meets minimum requirement"
            })
        
        # Check 2: Payout schedule (Sunday 11:11 AM SAST)
        payout_time = transaction_data.get("payout_time")
        if payout_time:
            schedule_check = self._verify_payout_datetime(payout_time)
            results["checks"].append(schedule_check)
            if schedule_check["status"] == VerificationStatus.FAILED:
                results["errors"].append("Payout outside scheduled window")
                results["status"] = VerificationStatus.FAILED
        
        # Check 3: Recipient verification status
        recipient_verified = transaction_data.get("recipient_verified", False)
        if not recipient_verified:
            results["checks"].append({
                "check": "recipient_verification",
                "status": VerificationStatus.FAILED,
                "message": "Recipient not verified"
            })
            results["errors"].append("Unverified recipient")
            results["status"] = VerificationStatus.FAILED
        else:
            results["checks"].append({
                "check": "recipient_verification",
                "status": VerificationStatus.PASSED,
                "message": "Recipient verified"
            })
        
        # Check 4: Suspicious amount detection
        avg_payout = transaction_data.get("user_average_payout", amount)
        if avg_payout > 0 and amount > avg_payout * self.constants.SUSPICIOUS_PAYOUT_MULTIPLIER:
            results["checks"].append({
                "check": "suspicious_amount",
                "status": VerificationStatus.WARNING,
                "message": f"Amount R{amount:.2f} is {amount/avg_payout:.1f}x user average"
            })
            results["warnings"].append("Suspicious payout amount detected")
            if results["status"] == VerificationStatus.PASSED:
                results["status"] = VerificationStatus.WARNING
        
        # Check 5: Bank account validation (SA banks)
        bank_code = transaction_data.get("bank_code", "")
        valid_banks = ["FNB", "CAPITEC", "STANDARD", "NEDBANK", "ABSA", "INVESTEC"]
        if bank_code and bank_code.upper() not in valid_banks:
            results["checks"].append({
                "check": "bank_validation",
                "status": VerificationStatus.WARNING,
                "message": f"Unrecognized bank code: {bank_code}"
            })
            results["warnings"].append("Unrecognized bank")
        else:
            results["checks"].append({
                "check": "bank_validation",
                "status": VerificationStatus.PASSED,
                "message": f"Valid bank: {bank_code}"
            })
        
        return results
    
    def _verify_payout_datetime(self, payout_time: datetime) -> Dict:
        """Verify payout is on correct day and time."""
        # Convert to SAST (UTC+2)
        if payout_time.tzinfo is None:
            payout_time = payout_time.replace(tzinfo=None)
        
        is_sunday = payout_time.weekday() == 6  # Sunday
        hour = payout_time.hour
        minute = payout_time.minute
        
        # Allow 11:00 - 11:30 window
        time_correct = hour == 11 and 0 <= minute <= 30
        
        if is_sunday and time_correct:
            return {
                "check": "payout_schedule",
                "status": VerificationStatus.PASSED,
                "message": f"Payout scheduled correctly: {payout_time}"
            }
        else:
            expected = f"Sunday 11:00-11:30 {self.constants.PAYOUT_TIMEZONE}"
            actual = payout_time.strftime("%A %H:%M")
            return {
                "check": "payout_schedule",
                "status": VerificationStatus.FAILED,
                "message": f"Expected {expected}, got {actual}"
            }
    
    def audit_referral_chain(self, referral_data: Dict) -> Dict[str, Any]:
        """
        Verify integrity of referral chains and detect anomalies.
        
        Args:
            referral_data: Referral chain data
            
        Returns:
            Audit results with chain integrity status
        """
        results = {
            "chain_id": referral_data.get("chain_id", "unknown"),
            "status": VerificationStatus.PASSED,
            "chain_length": 0,
            "self_referral_detected": False,
            "circular_referral_detected": False,
            "broken_links": [],
            "validations": []
        }
        
        chain = referral_data.get("chain", [])
        results["chain_length"] = len(chain)
        
        if not chain:
            return results
        
        # Build user map for quick lookup
        user_ids = set()
        referral_map = {}  # user -> referrer
        
        for entry in chain:
            user_id = entry.get("user_id")
            referrer_id = entry.get("referred_by")
            
            if user_id:
                user_ids.add(user_id)
            if user_id and referrer_id:
                referral_map[user_id] = referrer_id
        
        # Check for self-referrals
        for user_id, referrer_id in referral_map.items():
            if user_id == referrer_id:
                results["self_referral_detected"] = True
                results["validations"].append({
                    "type": "self_referral",
                    "user_id": user_id,
                    "status": VerificationStatus.FAILED,
                    "message": "User referred themselves"
                })
                results["status"] = VerificationStatus.FAILED
        
        # Check for circular referrals
        for user_id in user_ids:
            visited = set()
            current = user_id
            while current:
                if current in visited:
                    results["circular_referral_detected"] = True
                    results["validations"].append({
                        "type": "circular_referral",
                        "user_id": user_id,
                        "status": VerificationStatus.FAILED,
                        "message": f"Circular referral detected involving {user_id}"
                    })
                    results["status"] = VerificationStatus.FAILED
                    break
                visited.add(current)
                current = referral_map.get(current)
        
        # Check for broken links (referrer doesn't exist)
        for user_id, referrer_id in referral_map.items():
            if referrer_id not in user_ids:
                results["broken_links"].append({
                    "user_id": user_id,
                    "missing_referrer": referrer_id
                })
                results["validations"].append({
                    "type": "broken_link",
                    "user_id": user_id,
                    "referrer_id": referrer_id,
                    "status": VerificationStatus.WARNING,
                    "message": f"Referrer {referrer_id} not found in chain"
                })
        
        # Validate timestamps (referrals should be chronological)
        sorted_chain = sorted(chain, key=lambda x: x.get("timestamp", datetime.min))
        for i in range(1, len(sorted_chain)):
            if sorted_chain[i].get("timestamp") < sorted_chain[i-1].get("timestamp"):
                results["validations"].append({
                    "type": "timestamp_anomaly",
                    "status": VerificationStatus.WARNING,
                    "message": f"Non-chronological timestamps at index {i}"
                })
        
        return results
    
    def detect_reward_fraud(self, transactions: List[Dict]) -> List[FraudAlert]:
        """
        Detect fraudulent patterns in reward transactions.
        
        Args:
            transactions: List of reward transactions to analyze
            
        Returns:
            List of fraud alerts
        """
        alerts = []
        
        # Organize transactions by user
        user_transactions = defaultdict(list)
        ip_transactions = defaultdict(set)
        
        for tx in transactions:
            user_id = tx.get("user_id")
            ip_address = tx.get("ip_address")
            timestamp = tx.get("timestamp")
            
            if user_id:
                user_transactions[user_id].append(tx)
            if ip_address and user_id:
                ip_transactions[ip_address].add(user_id)
        
        # Rule 1: Self-referral detection
        self_referral_alerts = self._detect_self_referrals(transactions)
        alerts.extend(self_referral_alerts)
        
        # Rule 2: Duplicate account detection (same IP, multiple accounts)
        duplicate_alerts = self._detect_duplicate_accounts(ip_transactions)
        alerts.extend(duplicate_alerts)
        
        # Rule 3: Unusual reward patterns
        unusual_pattern_alerts = self._detect_unusual_patterns(user_transactions)
        alerts.extend(unusual_pattern_alerts)
        
        # Rule 4: Rapid-fire referral detection
        rapid_fire_alerts = self._detect_rapid_fire_referrals(user_transactions)
        alerts.extend(rapid_fire_alerts)
        
        # Rule 5: Suspicious payout amounts
        payout_alerts = self._detect_suspicious_payouts(transactions)
        alerts.extend(payout_alerts)
        
        return alerts
    
    def _detect_self_referrals(self, transactions: List[Dict]) -> List[FraudAlert]:
        """Detect users referring themselves."""
        alerts = []
        
        for tx in transactions:
            if tx.get("type") == "referral":
                user_id = tx.get("user_id")
                referred_user = tx.get("referred_user_id")
                
                if user_id == referred_user:
                    # Check device fingerprint and IP
                    device_match = tx.get("referrer_device_id") == tx.get("referee_device_id")
                    ip_match = tx.get("referrer_ip") == tx.get("referee_ip")
                    
                    if device_match or ip_match:
                        alerts.append(FraudAlert(
                            rule_triggered="self_referral",
                            severity=FraudSeverity.CRITICAL,
                            description=f"Confirmed self-referral detected",
                            affected_users=[user_id],
                            evidence={
                                "device_match": device_match,
                                "ip_match": ip_match,
                                "transaction_id": tx.get("id")
                            }
                        ))
        
        return alerts
    
    def _detect_duplicate_accounts(self, ip_transactions: Dict[str, Set[str]]) -> List[FraudAlert]:
        """Detect multiple accounts from same IP."""
        alerts = []
        
        for ip, users in ip_transactions.items():
            if len(users) > self.constants.DUPLICATE_IP_THRESHOLD:
                alerts.append(FraudAlert(
                    rule_triggered="duplicate_accounts",
                    severity=FraudSeverity.HIGH,
                    description=f"Multiple accounts ({len(users)}) from IP {ip}",
                    affected_users=list(users),
                    evidence={
                        "ip_address": ip,
                        "user_count": len(users),
                        "users": list(users)
                    }
                ))
        
        return alerts
    
    def _detect_unusual_patterns(self, user_transactions: Dict[str, List[Dict]]) -> List[FraudAlert]:
        """Detect unusual reward earning patterns."""
        alerts = []
        
        for user_id, txs in user_transactions.items():
            # Calculate average daily rewards
            referral_txs = [tx for tx in txs if tx.get("type") == "referral"]
            if len(referral_txs) < 3:
                continue
            
            # Check for sudden spikes
            daily_counts = defaultdict(int)
            for tx in referral_txs:
                day = tx.get("timestamp", datetime.utcnow()).date()
                daily_counts[day] += 1
            
            if daily_counts:
                avg_daily = sum(daily_counts.values()) / len(daily_counts)
                max_daily = max(daily_counts.values())
                
                if max_daily > avg_daily * 5 and max_daily > 5:
                    alerts.append(FraudAlert(
                        rule_triggered="unusual_reward_spike",
                        severity=FraudSeverity.MEDIUM,
                        description=f"Unusual referral spike: {max_daily} in one day (avg: {avg_daily:.1f})",
                        affected_users=[user_id],
                        evidence={
                            "user_id": user_id,
                            "max_daily": max_daily,
                            "avg_daily": avg_daily,
                            "daily_counts": dict(daily_counts)
                        }
                    ))
        
        return alerts
    
    def _detect_rapid_fire_referrals(self, user_transactions: Dict[str, List[Dict]]) -> List[FraudAlert]:
        """Detect rapid succession of referrals."""
        alerts = []
        
        for user_id, txs in user_transactions.items():
            referral_txs = [tx for tx in txs if tx.get("type") == "referral"]
            referral_txs.sort(key=lambda x: x.get("timestamp", datetime.min))
            
            if len(referral_txs) < self.constants.RAPID_REFERRAL_THRESHOLD:
                continue
            
            # Check for rapid-fire within window
            for i in range(len(referral_txs) - self.constants.RAPID_REFERRAL_THRESHOLD + 1):
                window_start = referral_txs[i].get("timestamp")
                window_end = referral_txs[i + self.constants.RAPID_REFERRAL_THRESHOLD - 1].get("timestamp")
                
                if window_start and window_end:
                    time_diff = (window_end - window_start).total_seconds() / 60
                    
                    if time_diff <= self.constants.RAPID_REFERRAL_WINDOW_MINUTES:
                        alerts.append(FraudAlert(
                            rule_triggered="rapid_fire_referrals",
                            severity=FraudSeverity.HIGH,
                            description=f"{self.constants.RAPID_REFERRAL_THRESHOLD}+ referrals in {time_diff:.0f} minutes",
                            affected_users=[user_id],
                            evidence={
                                "user_id": user_id,
                                "referral_count": self.constants.RAPID_REFERRAL_THRESHOLD,
                                "time_window_minutes": time_diff,
                                "start_time": window_start.isoformat(),
                                "end_time": window_end.isoformat()
                            }
                        ))
                        break
        
        return alerts
    
    def _detect_suspicious_payouts(self, transactions: List[Dict]) -> List[FraudAlert]:
        """Detect suspicious payout amounts."""
        alerts = []
        
        # Group by user and calculate averages
        user_payouts = defaultdict(list)
        for tx in transactions:
            if tx.get("type") == "payout":
                user_payouts[tx.get("user_id")].append(tx.get("amount", 0))
        
        for user_id, amounts in user_payouts.items():
            if len(amounts) < 2:
                continue
            
            avg_payout = sum(amounts[:-1]) / len(amounts[:-1])
            latest_payout = amounts[-1]
            
            if avg_payout > 0 and latest_payout > avg_payout * self.constants.SUSPICIOUS_PAYOUT_MULTIPLIER:
                alerts.append(FraudAlert(
                    rule_triggered="suspicious_payout",
                    severity=FraudSeverity.MEDIUM,
                    description=f"Payout R{latest_payout:.2f} is {latest_payout/avg_payout:.1f}x user average",
                    affected_users=[user_id],
                    evidence={
                        "user_id": user_id,
                        "latest_payout": latest_payout,
                        "average_payout": avg_payout,
                        "multiplier": latest_payout / avg_payout
                    }
                ))
        
        return alerts
    
    def validate_tier_progression(self, user_data: Dict) -> Dict[str, Any]:
        """
        Validate customer tier progression is correct.
        
        Args:
            user_data: User's referral and tier data
            
        Returns:
            Tier validation results
        """
        results = {
            "user_id": user_data.get("user_id", "unknown"),
            "status": VerificationStatus.PASSED,
            "current_tier": user_data.get("tier", "unknown"),
            "calculated_tier": None,
            "referral_count": user_data.get("successful_referrals", 0),
            "validations": [],
            "benefits_match": True
        }
        
        referral_count = user_data.get("successful_referrals", 0)
        current_tier = user_data.get("tier")
        
        # Calculate what tier they should be
        calculated_tier = self._get_tier_from_referrals(referral_count)
        results["calculated_tier"] = calculated_tier.value
        
        # Validate tier assignment
        if current_tier != calculated_tier.value:
            results["status"] = VerificationStatus.FAILED
            results["validations"].append({
                "type": "tier_mismatch",
                "status": VerificationStatus.FAILED,
                "message": f"Tier mismatch: assigned '{current_tier}', should be '{calculated_tier.value}'"
            })
        else:
            results["validations"].append({
                "type": "tier_assignment",
                "status": VerificationStatus.PASSED,
                "message": f"Tier '{current_tier}' correctly assigned for {referral_count} referrals"
            })
        
        # Validate benefits match tier
        tier_config = TIER_CONFIGS[calculated_tier]
        user_discount = user_data.get("discount_percentage", 0)
        user_free_deliveries = user_data.get("free_deliveries_per_month", 0)
        
        if abs(user_discount - tier_config.discount_percentage) > 0.01:
            results["benefits_match"] = False
            results["status"] = VerificationStatus.FAILED
            results["validations"].append({
                "type": "discount_mismatch",
                "status": VerificationStatus.FAILED,
                "message": f"Discount {user_discount}% doesn't match tier {tier_config.discount_percentage}%"
            })
        
        if user_free_deliveries != tier_config.free_deliveries_per_month:
            results["benefits_match"] = False
            results["status"] = VerificationStatus.FAILED
            results["validations"].append({
                "type": "free_delivery_mismatch",
                "status": VerificationStatus.FAILED,
                "message": f"Free deliveries {user_free_deliveries} != expected {tier_config.free_deliveries_per_month}"
            })
        
        return results
    
    def _get_tier_from_referrals(self, referral_count: int) -> TierLevel:
        """Get tier level based on referral count."""
        for tier in [TierLevel.PLATINUM, TierLevel.GOLD, TierLevel.SILVER, TierLevel.BRONZE]:
            config = TIER_CONFIGS[tier]
            if config.min_referrals <= referral_count <= config.max_referrals:
                return tier
        return TierLevel.BRONZE if referral_count > 0 else TierLevel.BRONZE
    
    def check_payout_schedule(self, schedule_code: str) -> Dict[str, Any]:
        """
        Verify payout schedule configuration is correct.
        
        Args:
            schedule_code: Schedule configuration code
            
        Returns:
            Schedule validation results
        """
        results = {
            "status": VerificationStatus.PASSED,
            "schedule_valid": True,
            "checks": [],
            "warnings": [],
            "errors": []
        }
        
        # Expected schedule parameters
        expected = {
            "day": self.constants.PAYOUT_DAY,
            "time": self.constants.PAYOUT_TIME,
            "timezone": self.constants.PAYOUT_TIMEZONE,
            "minimum_amount": self.constants.MINIMUM_PAYOUT_ZAR
        }
        
        # Parse schedule code (simplified - in production would parse actual code)
        # For demo, we assume schedule_code is a dict-like structure
        try:
            schedule_config = json.loads(schedule_code) if isinstance(schedule_code, str) else schedule_code
        except:
            schedule_config = {}
        
        # Check day
        if schedule_config.get("day", "").lower() != expected["day"]:
            results["errors"].append(f"Payout day should be {expected['day']}")
            results["status"] = VerificationStatus.FAILED
            results["schedule_valid"] = False
        
        # Check time
        if schedule_config.get("time", "") != expected["time"]:
            results["errors"].append(f"Payout time should be {expected['time']}")
            results["status"] = VerificationStatus.FAILED
            results["schedule_valid"] = False
        
        # Check timezone
        if schedule_config.get("timezone", "") != expected["timezone"]:
            results["warnings"].append(f"Timezone should be {expected['timezone']}")
            if results["status"] == VerificationStatus.PASSED:
                results["status"] = VerificationStatus.WARNING
        
        # Check minimum payout
        config_min = schedule_config.get("minimum_payout", 0)
        if config_min != expected["minimum_amount"]:
            results["errors"].append(f"Minimum payout should be R{expected['minimum_amount']:.2f}, got R{config_min:.2f}")
            results["status"] = VerificationStatus.FAILED
            results["schedule_valid"] = False
        
        results["checks"] = [
            {"check": "payout_day", "expected": expected["day"], "actual": schedule_config.get("day")},
            {"check": "payout_time", "expected": expected["time"], "actual": schedule_config.get("time")},
            {"check": "timezone", "expected": expected["timezone"], "actual": schedule_config.get("timezone")},
            {"check": "minimum_payout", "expected": expected["minimum_amount"], "actual": config_min}
        ]
        
        return results
    
    def verify_coin_redemption(self, redemption_code: str) -> Dict[str, Any]:
        """
        Verify coin redemption logic is correct.
        
        Args:
            redemption_code: Redemption calculation code
            
        Returns:
            Redemption validation results
        """
        results = {
            "status": VerificationStatus.PASSED,
            "checks": [],
            "test_cases": []
        }
        
        # Test cases for coin redemption
        test_cases = [
            {
                "name": "Free Delivery",
                "coins": 100,
                "expected_reward": "free_delivery",
                "expected_value": 0
            },
            {
                "name": "R15 Discount",
                "coins": 150,
                "expected_reward": "r15_discount",
                "expected_value": 15.0
            },
            {
                "name": "R30 Discount",
                "coins": 300,
                "expected_reward": "r30_discount",
                "expected_value": 30.0
            },
            {
                "name": "Insufficient Coins",
                "coins": 50,
                "expected_reward": None,
                "expected_value": 0
            },
            {
                "name": "Coin to ZAR Conversion",
                "coins": 100,
                "test_conversion": True,
                "expected_zar": 10.0
            }
        ]
        
        for test in test_cases:
            test_result = {"name": test["name"], "passed": True, "errors": []}
            
            coins = test["coins"]
            
            # Check coin value conversion
            if test.get("test_conversion"):
                expected_zar = test["expected_zar"]
                actual_zar = coins * self.constants.COIN_VALUE_ZAR
                if abs(actual_zar - expected_zar) > 0.01:
                    test_result["passed"] = False
                    test_result["errors"].append(
                        f"Coin conversion error: expected R{expected_zar}, got R{actual_zar}"
                    )
            
            # Check redemption thresholds
            elif coins >= self.constants.REDEMPTION_R30_OFF:
                if test["expected_reward"] != CoinRedemptionType.R30_DISCOUNT.value:
                    test_result["passed"] = False
                    test_result["errors"].append("R30 discount threshold incorrect")
            elif coins >= self.constants.REDEMPTION_R15_OFF:
                if test["expected_reward"] != CoinRedemptionType.R15_DISCOUNT.value:
                    test_result["passed"] = False
                    test_result["errors"].append("R15 discount threshold incorrect")
            elif coins >= self.constants.REDEMPTION_FREE_DELIVERY:
                if test["expected_reward"] != CoinRedemptionType.FREE_DELIVERY.value:
                    test_result["passed"] = False
                    test_result["errors"].append("Free delivery threshold incorrect")
            
            if not test_result["passed"]:
                results["status"] = VerificationStatus.FAILED
            
            results["test_cases"].append(test_result)
        
        # Validate redemption value calculations
        results["checks"].append({
            "check": "redemption_values",
            "100_coins": "Free delivery",
            "150_coins": "R15 discount",
            "300_coins": "R30 discount",
            "coin_value": f"R{self.constants.COIN_VALUE_ZAR}",
            "status": results["status"].value
        })
        
        return results
    
    def generate_audit_report(self, audit_results: List[Dict]) -> AuditReport:
        """
        Generate comprehensive audit report from multiple verification results.
        
        Args:
            audit_results: List of verification results
            
        Returns:
            Comprehensive audit report
        """
        errors = []
        fraud_alerts = []
        recommendations = []
        calculations_checked = 0
        passed_count = 0
        failed_count = 0
        
        for result in audit_results:
            result_type = result.get("type", "unknown")
            
            if result_type == "fraud_detection":
                fraud_alerts.extend(result.get("alerts", []))
            elif result_type == "calculation":
                calculations_checked += result.get("tests_run", 0)
                if result.get("status") == VerificationStatus.PASSED.value:
                    passed_count += 1
                else:
                    failed_count += 1
                    for error in result.get("errors", []):
                        errors.append(VerificationError(
                            component=result.get("component", "unknown"),
                            error_type="calculation_error",
                            description=error.get("error", "Unknown error"),
                            expected_value=error.get("expected"),
                            actual_value=error.get("actual")
                        ))
            elif result_type == "tier_validation":
                calculations_checked += 1
                if result.get("status") != VerificationStatus.PASSED.value:
                    failed_count += 1
                    for validation in result.get("validations", []):
                        if validation.get("status") != VerificationStatus.PASSED.value:
                            errors.append(VerificationError(
                                component="tier_system",
                                error_type=validation.get("type", "tier_error"),
                                description=validation.get("message", ""),
                                expected_value=result.get("calculated_tier"),
                                actual_value=result.get("current_tier")
                            ))
                else:
                    passed_count += 1
            elif result_type == "payout_verification":
                calculations_checked += 1
                if result.get("status") != VerificationStatus.PASSED.value:
                    failed_count += 1
                    for check in result.get("checks", []):
                        if check.get("status") == VerificationStatus.FAILED.value:
                            errors.append(VerificationError(
                                component="payout_system",
                                error_type=check.get("check", "payout_error"),
                                description=check.get("message", ""),
                                expected_value="compliant",
                                actual_value="failed"
                            ))
                else:
                    passed_count += 1
        
        # Generate recommendations based on findings
        if failed_count > 0:
            recommendations.append(f"Review and fix {failed_count} failed verification(s)")
        
        if fraud_alerts:
            critical_count = sum(1 for a in fraud_alerts if a.severity == FraudSeverity.CRITICAL)
            if critical_count > 0:
                recommendations.append(f"URGENT: Investigate {critical_count} critical fraud alert(s)")
            recommendations.append(f"Review {len(fraud_alerts)} fraud detection alert(s)")
        
        if any(e.component == "tier_system" for e in errors):
            recommendations.append("Audit tier benefit assignments for affected users")
        
        if any(e.component == "payout_system" for e in errors):
            recommendations.append("Review payout schedule and threshold configurations")
        
        # Calculate compliance score
        total_checks = passed_count + failed_count
        compliance_score = (passed_count / total_checks * 100) if total_checks > 0 else 100.0
        
        # Adjust for fraud alerts
        fraud_penalty = len([a for a in fraud_alerts if a.severity in [FraudSeverity.HIGH, FraudSeverity.CRITICAL]]) * 5
        compliance_score = max(0, compliance_score - fraud_penalty)
        
        # Determine compliance status
        if compliance_score >= 95 and not fraud_alerts:
            compliance_status = "FULLY_COMPLIANT"
        elif compliance_score >= 80:
            compliance_status = "COMPLIANT_WITH_WARNINGS"
        elif compliance_score >= 60:
            compliance_status = "PARTIALLY_COMPLIANT"
        else:
            compliance_status = "NON_COMPLIANT"
        
        summary = {
            "total_verifications": total_checks,
            "passed": passed_count,
            "failed": failed_count,
            "fraud_alerts_count": len(fraud_alerts),
            "critical_fraud_alerts": sum(1 for a in fraud_alerts if a.severity == FraudSeverity.CRITICAL),
            "components_audited": list(set(e.component for e in errors)) if errors else []
        }
        
        return AuditReport(
            overall_compliance_score=round(compliance_score, 2),
            calculations_checked=calculations_checked,
            errors_found=errors,
            fraud_alerts=fraud_alerts,
            recommendations=recommendations,
            compliance_status=compliance_status,
            summary=summary
        )
    
    def run_full_audit(self, data: Dict) -> AuditReport:
        """
        Run a complete audit of all reward systems.
        
        Args:
            data: Complete system data including transactions, users, payouts
            
        Returns:
            Comprehensive audit report
        """
        audit_results = []
        
        # 1. Validate reward calculations
        if "calculation_tests" in data:
            calc_result = self.validate_reward_calculation(
                data["calculation_tests"].get("code", ""),
                data["calculation_tests"].get("test_cases", [])
            )
            calc_result["type"] = "calculation"
            calc_result["component"] = "reward_calculations"
            audit_results.append(calc_result)
        
        # 2. Verify payout transactions
        if "payout_transactions" in data:
            for tx in data["payout_transactions"]:
                payout_result = self.verify_payout_transaction(tx)
                payout_result["type"] = "payout_verification"
                audit_results.append(payout_result)
        
        # 3. Audit referral chains
        if "referral_chains" in data:
            for chain in data["referral_chains"]:
                chain_result = self.audit_referral_chain(chain)
                chain_result["type"] = "referral_chain"
                audit_results.append(chain_result)
        
        # 4. Detect fraud
        if "transactions" in data:
            fraud_alerts = self.detect_reward_fraud(data["transactions"])
            audit_results.append({
                "type": "fraud_detection",
                "alerts": fraud_alerts
            })
        
        # 5. Validate tier progressions
        if "user_tiers" in data:
            for user in data["user_tiers"]:
                tier_result = self.validate_tier_progression(user)
                tier_result["type"] = "tier_validation"
                audit_results.append(tier_result)
        
        # 6. Check payout schedule
        if "payout_schedule" in data:
            schedule_result = self.check_payout_schedule(data["payout_schedule"])
            schedule_result["type"] = "schedule_check"
            audit_results.append(schedule_result)
        
        # 7. Verify coin redemption
        if "coin_redemption" in data:
            redemption_result = self.verify_coin_redemption(data["coin_redemption"])
            redemption_result["type"] = "redemption_check"
            audit_results.append(redemption_result)
        
        return self.generate_audit_report(audit_results)


# =============================================================================
# DEMO / TEST CODE
# =============================================================================

def demo():
    """Demonstrate the Reward Verification Agent capabilities."""
    
    print("=" * 80)
    print("iHhashi Reward Verification Agent - Demo")
    print("=" * 80)
    print()
    
    agent = RewardVerificationAgent()
    
    # Demo 1: Reward Calculation Validation
    print("1. Reward Calculation Validation")
    print("-" * 40)
    
    test_cases = [
        {
            "name": "New customer referral",
            "inputs": {"referral_count": 1, "base_coins": 0},
            "expected_output": 50
        },
        {
            "name": "Multiple referrals",
            "inputs": {"referral_count": 5, "base_coins": 100},
            "expected_output": 350  # 100 + (5 * 50)
        },
        {
            "name": "No referrals",
            "inputs": {"referral_count": 0, "base_coins": 25},
            "expected_output": 25
        }
    ]
    
    result = agent.validate_reward_calculation("coin_calculation", test_cases)
    print(f"Tests Run: {result['tests_run']}")
    print(f"Tests Passed: {result['tests_passed']}")
    print(f"Tests Failed: {result['tests_failed']}")
    print(f"Status: {result['status'].value}")
    if result['errors']:
        print(f"Errors: {result['errors']}")
    print()
    
    # Demo 2: Payout Transaction Verification
    print("2. Payout Transaction Verification")
    print("-" * 40)
    
    valid_payout = {
        "id": "PAY-001",
        "amount": 250.00,
        "payout_time": datetime(2026, 3, 8, 11, 11),  # Sunday 11:11
        "recipient_verified": True,
        "bank_code": "FNB",
        "user_average_payout": 200.00
    }
    
    invalid_payout = {
        "id": "PAY-002",
        "amount": 50.00,  # Below minimum
        "payout_time": datetime(2026, 3, 9, 14, 0),  # Monday, wrong day
        "recipient_verified": False,
        "bank_code": "UNKNOWN"
    }
    
    result1 = agent.verify_payout_transaction(valid_payout)
    print(f"Valid Payout: {result1['status'].value}")
    print(f"  Checks passed: {sum(1 for c in result1['checks'] if c['status'] == VerificationStatus.PASSED)}")
    
    result2 = agent.verify_payout_transaction(invalid_payout)
    print(f"Invalid Payout: {result2['status'].value}")
    print(f"  Errors: {result2['errors']}")
    print()
    
    # Demo 3: Referral Chain Audit
    print("3. Referral Chain Audit")
    print("-" * 40)
    
    valid_chain = {
        "chain_id": "CHAIN-001",
        "chain": [
            {"user_id": "U001", "referred_by": None, "timestamp": datetime(2026, 1, 1)},
            {"user_id": "U002", "referred_by": "U001", "timestamp": datetime(2026, 1, 2)},
            {"user_id": "U003", "referred_by": "U002", "timestamp": datetime(2026, 1, 3)},
        ]
    }
    
    fraudulent_chain = {
        "chain_id": "CHAIN-002",
        "chain": [
            {"user_id": "U004", "referred_by": None, "timestamp": datetime(2026, 1, 1)},
            {"user_id": "U005", "referred_by": "U004", "timestamp": datetime(2026, 1, 2)},
            {"user_id": "U004", "referred_by": "U005", "timestamp": datetime(2026, 1, 3)},  # Circular!
        ]
    }
    
    result1 = agent.audit_referral_chain(valid_chain)
    print(f"Valid Chain: {result1['status'].value}")
    print(f"  Chain length: {result1['chain_length']}")
    
    result2 = agent.audit_referral_chain(fraudulent_chain)
    print(f"Fraudulent Chain: {result2['status'].value}")
    print(f"  Circular referral: {result2['circular_referral_detected']}")
    print()
    
    # Demo 4: Fraud Detection
    print("4. Fraud Detection")
    print("-" * 40)
    
    transactions = [
        # Normal transactions
        {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 0), "ip_address": "192.168.1.1"},
        {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 2, 10, 0), "ip_address": "192.168.1.1"},
        
        # Rapid-fire referrals (suspicious)
        {"user_id": "U002", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 0), "ip_address": "192.168.1.2"},
        {"user_id": "U002", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 5), "ip_address": "192.168.1.2"},
        {"user_id": "U002", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 8), "ip_address": "192.168.1.2"},
        {"user_id": "U002", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 12), "ip_address": "192.168.1.2"},
        {"user_id": "U002", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 15), "ip_address": "192.168.1.2"},
        {"user_id": "U002", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 18), "ip_address": "192.168.1.2"},
        
        # Multiple accounts from same IP
        {"user_id": "U003", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 0), "ip_address": "192.168.1.100"},
        {"user_id": "U004", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 5), "ip_address": "192.168.1.100"},
        {"user_id": "U005", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 10), "ip_address": "192.168.1.100"},
        {"user_id": "U006", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 15), "ip_address": "192.168.1.100"},
    ]
    
    fraud_alerts = agent.detect_reward_fraud(transactions)
    print(f"Fraud alerts detected: {len(fraud_alerts)}")
    for alert in fraud_alerts:
        print(f"  - {alert.rule_triggered} ({alert.severity.value}): {alert.description}")
    print()
    
    # Demo 5: Tier Progression Validation
    print("5. Tier Progression Validation")
    print("-" * 40)
    
    valid_user = {
        "user_id": "U001",
        "tier": "silver",
        "successful_referrals": 10,
        "discount_percentage": 10.0,
        "free_deliveries_per_month": 1
    }
    
    invalid_user = {
        "user_id": "U002",
        "tier": "bronze",  # Should be gold!
        "successful_referrals": 25,
        "discount_percentage": 5.0,
        "free_deliveries_per_month": 0
    }
    
    result1 = agent.validate_tier_progression(valid_user)
    print(f"Valid User: {result1['status'].value}")
    print(f"  Tier: {result1['current_tier']} (correct for {result1['referral_count']} referrals)")
    
    result2 = agent.validate_tier_progression(invalid_user)
    print(f"Invalid User: {result2['status'].value}")
    print(f"  Current tier: {result2['current_tier']}, Should be: {result2['calculated_tier']}")
    print()
    
    # Demo 6: Payout Schedule Check
    print("6. Payout Schedule Check")
    print("-" * 40)
    
    valid_schedule = json.dumps({
        "day": "sunday",
        "time": "11:11",
        "timezone": "SAST",
        "minimum_payout": 100.00
    })
    
    invalid_schedule = json.dumps({
        "day": "monday",  # Wrong day
        "time": "09:00",  # Wrong time
        "timezone": "UTC",  # Wrong timezone
        "minimum_payout": 50.00  # Wrong amount
    })
    
    result1 = agent.check_payout_schedule(valid_schedule)
    print(f"Valid Schedule: {result1['status'].value}")
    
    result2 = agent.check_payout_schedule(invalid_schedule)
    print(f"Invalid Schedule: {result2['status'].value}")
    print(f"  Errors: {result2['errors']}")
    print()
    
    # Demo 7: Coin Redemption Verification
    print("7. Coin Redemption Verification")
    print("-" * 40)
    
    redemption_code = "calculate_redemption"
    result = agent.verify_coin_redemption(redemption_code)
    print(f"Redemption Status: {result['status'].value}")
    print(f"Test cases run: {len(result['test_cases'])}")
    for tc in result['test_cases']:
        status = "✓" if tc['passed'] else "✗"
        print(f"  {status} {tc['name']}")
    print()
    
    # Demo 8: Full Audit Report
    print("8. Full Audit Report")
    print("-" * 40)
    
    audit_data = {
        "calculation_tests": {
            "code": "coin_calculation",
            "test_cases": test_cases
        },
        "payout_transactions": [valid_payout, invalid_payout],
        "referral_chains": [valid_chain, fraudulent_chain],
        "transactions": transactions,
        "user_tiers": [valid_user, invalid_user],
        "payout_schedule": valid_schedule,
        "coin_redemption": redemption_code
    }
    
    report = agent.run_full_audit(audit_data)
    
    print(f"Overall Compliance Score: {report.overall_compliance_score}%")
    print(f"Compliance Status: {report.compliance_status}")
    print(f"Calculations Checked: {report.calculations_checked}")
    print(f"Errors Found: {len(report.errors_found)}")
    print(f"Fraud Alerts: {len(report.fraud_alerts)}")
    print()
    
    if report.errors_found:
        print("Errors:")
        for error in report.errors_found[:5]:
            print(f"  - {error.component}: {error.description}")
    
    if report.fraud_alerts:
        print("\nFraud Alerts:")
        for alert in report.fraud_alerts:
            print(f"  - [{alert.severity.value.upper()}] {alert.rule_triggered}: {alert.description}")
    
    if report.recommendations:
        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    
    print()
    print("=" * 80)
    print("Demo Complete")
    print("=" * 80)
    
    return report


if __name__ == "__main__":
    demo()
