# iHhashi Reward Verification Agent

A comprehensive validation agent for iHhashi's reward calculations, payout logic, and referral systems. Ensures compliance with South African regulations and platform policies.

## Features

### Core Capabilities
- **Reward Calculation Validation** - Verify coin calculations, tier assignments, and referral bonuses
- **Payout Audit** - Validate payout transactions against schedule and thresholds
- **Referral Chain Verification** - Detect circular referrals, broken links, and self-referrals
- **Fraud Detection** - Identify suspicious patterns and potential abuse
- **Compliance Checking** - Ensure adherence to platform policies and regulations

### South Africa Specific
- Currency: ZAR (R)
- Coin value: 1 coin = R0.10
- Payout day: Every Sunday at 11:11 AM SAST
- Minimum payout: R100
- Support for SA banks (FNB, Capitec, Standard Bank, Nedbank, Absa, Investec)

## Quick Start

```python
from reward_verification_agent import RewardVerificationAgent, AuditReport

# Initialize the agent
agent = RewardVerificationAgent()

# Run a full audit
audit_data = {
    "payout_transactions": [...],
    "referral_chains": [...],
    "transactions": [...],
    "user_tiers": [...],
    "payout_schedule": {...}
}

report = agent.run_full_audit(audit_data)
print(f"Compliance Score: {report.overall_compliance_score}%")
```

## API Reference

### RewardVerificationAgent

#### `validate_reward_calculation(calculation_code, test_cases)`
Validates reward calculation logic against test cases.

**Parameters:**
- `calculation_code` (str): The reward calculation code to validate
- `test_cases` (list): List of test cases with inputs and expected outputs

**Returns:** Validation results with pass/fail status

#### `verify_payout_transaction(transaction_data)`
Verifies a single payout transaction for compliance.

**Parameters:**
- `transaction_data` (dict): Payout transaction details including:
  - `id`: Transaction ID
  - `amount`: Payout amount
  - `payout_time`: datetime object
  - `recipient_verified`: bool
  - `bank_code`: SA bank code
  - `user_average_payout`: Historical average

**Returns:** Verification results with checks, warnings, and errors

#### `audit_referral_chain(referral_data)`
Verifies integrity of referral chains.

**Parameters:**
- `referral_data` (dict): Referral chain with `chain_id` and `chain` list

**Returns:** Chain integrity status with fraud detection flags

#### `detect_reward_fraud(transactions)`
Detects fraudulent patterns in reward transactions.

**Parameters:**
- `transactions` (list): List of reward transactions

**Returns:** List of `FraudAlert` objects

#### `validate_tier_progression(user_data)`
Validates customer tier progression is correct.

**Parameters:**
- `user_data` (dict): User's referral count and tier assignment

**Returns:** Tier validation results with benefit verification

#### `check_payout_schedule(schedule_code)`
Verifies payout schedule configuration.

**Parameters:**
- `schedule_code` (str): Schedule configuration (JSON)

**Returns:** Schedule validation results

#### `verify_coin_redemption(redemption_code)`
Verifies coin redemption logic is correct.

**Parameters:**
- `redemption_code` (str): Redemption calculation code

**Returns:** Redemption validation with test case results

#### `run_full_audit(data)`
Runs a complete audit of all reward systems.

**Parameters:**
- `data` (dict): Complete system data including all components

**Returns:** `AuditReport` with comprehensive results

## Customer Tiers

| Tier | Referrals | Discount | Free Deliveries | Support |
|------|-----------|----------|-----------------|---------|
| Bronze | 1-5 | 5% | 0 | Standard 🥉 |
| Silver | 6-15 | 10% | 1/month | Priority 🥈 |
| Gold | 16-50 | 15% | 2/month | VIP 🥇 |
| Platinum | 51+ | 20% | Unlimited | Dedicated Manager 💎 |

## Coin Redemption

| Coins | Reward | Value |
|-------|--------|-------|
| 100 | Free Delivery | R0 |
| 150 | Discount | R15 |
| 300 | Discount | R30 |

**Coin Value:** 1 iHhashi Coin = R0.10

## Fraud Detection Rules

### Self-Referral Detection
- Detects users referring themselves
- Uses device fingerprint and IP matching
- **Severity:** CRITICAL

### Duplicate Account Detection
- Flags multiple accounts from same IP
- Threshold: 3+ accounts per IP
- **Severity:** HIGH

### Rapid-Fire Referrals
- Detects suspicious referral velocity
- Threshold: 5+ referrals within 60 minutes
- **Severity:** HIGH

### Suspicious Payout Amounts
- Flags payouts significantly above user average
- Threshold: 3x average payout
- **Severity:** MEDIUM

### Unusual Reward Patterns
- Detects sudden spikes in referral activity
- Compares daily averages against spikes
- **Severity:** MEDIUM

## Payout Schedule Requirements

- **Day:** Sunday
- **Time:** 11:11 AM
- **Timezone:** SAST (UTC+2)
- **Minimum Amount:** R100
- **Recipient:** Must be verified

## Audit Report Structure

```python
@dataclass
class AuditReport:
    overall_compliance_score: float  # 0-100%
    calculations_checked: int
    errors_found: List[VerificationError]
    fraud_alerts: List[FraudAlert]
    recommendations: List[str]
    compliance_status: str  # FULLY_COMPLIANT, COMPLIANT_WITH_WARNINGS, etc.
    audit_timestamp: datetime
    summary: Dict[str, Any]
```

### Compliance Status Levels

| Score | Status | Description |
|-------|--------|-------------|
| 95-100% | FULLY_COMPLIANT | No issues detected |
| 80-94% | COMPLIANT_WITH_WARNINGS | Minor issues present |
| 60-79% | PARTIALLY_COMPLIANT | Significant issues |
| 0-59% | NON_COMPLIANT | Critical failures |

## Examples

### Example 1: Validate Payout Transaction

```python
from datetime import datetime
from reward_verification_agent import RewardVerificationAgent

agent = RewardVerificationAgent()

transaction = {
    "id": "PAY-001",
    "amount": 250.00,
    "payout_time": datetime(2026, 3, 8, 11, 11),  # Sunday 11:11
    "recipient_verified": True,
    "bank_code": "FNB",
    "user_average_payout": 200.00
}

result = agent.verify_payout_transaction(transaction)
print(f"Status: {result['status']}")
print(f"Checks: {result['checks']}")
```

### Example 2: Detect Fraud

```python
transactions = [
    {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 0), "ip_address": "192.168.1.1"},
    {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 2), "ip_address": "192.168.1.1"},
    {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 5), "ip_address": "192.168.1.1"},
    {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 8), "ip_address": "192.168.1.1"},
    {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 10), "ip_address": "192.168.1.1"},
    {"user_id": "U001", "type": "referral", "timestamp": datetime(2026, 3, 1, 10, 12), "ip_address": "192.168.1.1"},
]

alerts = agent.detect_reward_fraud(transactions)
for alert in alerts:
    print(f"[{alert.severity.value}] {alert.rule_triggered}: {alert.description}")
```

### Example 3: Full System Audit

```python
audit_data = {
    "calculation_tests": {
        "code": "coin_calculation",
        "test_cases": [
            {"name": "test1", "inputs": {"referral_count": 5}, "expected_output": 250}
        ]
    },
    "payout_transactions": [...],
    "referral_chains": [...],
    "transactions": [...],
    "user_tiers": [
        {"user_id": "U001", "tier": "silver", "successful_referrals": 10}
    ],
    "payout_schedule": '{"day": "sunday", "time": "11:11", "timezone": "SAST"}'
}

report = agent.run_full_audit(audit_data)

print(f"Compliance Score: {report.overall_compliance_score}%")
print(f"Status: {report.compliance_status}")

for error in report.errors_found:
    print(f"Error: {error.component} - {error.description}")

for alert in report.fraud_alerts:
    print(f"Fraud Alert: {alert.rule_triggered} ({alert.severity.value})")

for rec in report.recommendations:
    print(f"Recommendation: {rec}")
```

## Running Tests

```bash
cd /home/teacherchris37/MasterBuilder7/skills/reward-verification-agent
python3 reward_verification_agent.py
```

The demo will run through all verification scenarios and produce a comprehensive audit report.

## Integration with iHhashi

This agent is designed to work with the iHhashi food delivery platform's reward system:

- Validates customer tier progression
- Verifies iHhashi Coin calculations
- Audits vendor referral bonuses (2 free days per referral)
- Ensures payout compliance (Sundays 11:11 AM SAST)
- Detects fraudulent referral activity

## License

Part of the iHhashi project - Food delivery platform for South Africa.
