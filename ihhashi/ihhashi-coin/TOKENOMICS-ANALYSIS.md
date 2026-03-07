# iHhashi Coin Tokenomics Analysis & Recommendation

## Executive Summary

This analysis proposes a **Stake-to-Earn + Fee-Share + Deflationary** model that aligns incentives across all ecosystem participants while preventing dumping and creating genuine scarcity.

**Core Thesis**: iHhashi Coin should not be a reward token—it should be an **ownership stake** in the iHhashi economy. Holders don't just get discounts; they earn from platform activity, similar to owning equity in the platform.

---

## Current Zora V4 Fee Structure

| Recipient | % of Total Fees (1%) | Duration |
|-----------|---------------------|----------|
| iHhashi (Platform Referrer) | 20% | Forever |
| Trade Referrer | 4% | Per trade |
| Creator | 50% | Forever |
| Protocol | 5% | Zora treasury |
| Doppler | 1% | Doppler treasury |
| LP Rewards | 20% | Permanently locked |

**Total addressable for redistribution**: The Creator's 50% + Trade Referrer's 4% = **54% of trading fees**

---

## 🎯 RECOMMENDED MODEL: "Hashi Sovereign"

### 1. FEE REDISTRIBUTION TO STAKEHOLDERS

**Redesign the 54% allocation as follows:**

| Recipient | % of Trading Fees | Mechanism |
|-----------|------------------|-----------|
| **Merchants (Staked)** | **18%** | Split proportionally by staked coins |
| **Drivers (Staked)** | **18%** | Split proportionally by staked coins |
| **Customers (Staked)** | **12%** | Split proportionally by staked coins |
| **Trade Referrer Bonus** | **4%** | To whoever referred the trade |
| **Creator Reserve** | **2%** | iHhashi treasury for operations |

**Total: 54%**

**Why these percentages?**

- **Merchants + Drivers = 36%**: They ARE the platform. Without restaurants and delivery, there's no business. Equal split (18% each) recognises their equal importance.
- **Customers = 12%**: They bring demand, but the value is capped to prevent pure speculation. The lower % encourages actual usage over speculation.
- **Trade Referrer = 4%**: Preserved from Zora's design—encourages viral growth.
- **Creator Reserve = 2%**: Minimal treasury fee for ongoing development.

---

### 2. STAKING MECHANISM: "Hashi Vault"

**The Problem with Pure Holding**: People claim to hold, then dump on pumps.

**The Solution: Time-Weighted Staking**

```
Staking Tiers (Minimum 30-day lock):
├── SILVER VAULT (30-89 days): 0.8x multiplier on fee share
├── GOLD VAULT (90-179 days): 1.0x multiplier
├── PLATINUM VAULT (180-364 days): 1.5x multiplier
└── DIAMOND VAULT (365+ days): 2.5x multiplier + governance rights
```

**How it works:**

1. Merchant stakes 10,000 HASHI for 180 days → Gets Platinum status
2. Platform earns R10,000 in trading fees that month
3. Merchant pool (18%) = R1,800
4. Merchant's share = (10,000 × 1.5) / Total Staked in Pool
5. **Claim weekly or compound automatically**

**Anti-Dump Protection:**

- Early unstake penalty: 5-15% burned (scales with lock duration)
- 7-day unbonding period for all unstakes
- Rewards only claimable after minimum 30-day stake

---

### 3. VESTING SCHEDULES

**For Different Stakeholders:**

| Stakeholder | Initial Allocation | Vesting Schedule | Cliff |
|-------------|-------------------|------------------|-------|
| **Merchants** | Based on GMV history | 6-month linear | 1 month |
| **Drivers** | Based on deliveries completed | 6-month linear | 1 month |
| **Early Customers** | Based on order history | 3-month linear | None |
| **Team/Founders** | 10% of supply | 24-month linear | 12 months |
| **Treasury** | 15% of supply | 48-month linear | 6 months |
| **Community Airdrop** | 5% of supply | Immediate (claim within 90 days) | None |
| **Liquidity Mining** | 20% of supply | Emitted over 4 years | None |

**Vesting Rationale:**

- **Merchants/Drivers**: Shorter vesting (6 months) because they have operational cash flow needs. They're running businesses, not speculating.
- **Customers**: No cliff, shorter vesting—they're the least sophisticated users and need immediate utility.
- **Team**: Long vesting (24 months) with 12-month cliff aligns team with long-term success.
- **Treasury**: Very long vesting (48 months) ensures funds available for years of development.

---

### 4. DEFLATIONARY MECHANISMS

**Four-Layer Deflation:**

#### Layer 1: Transaction Burn (0.5%)
- Every on-chain trade burns 0.5% of the transaction value
- Built into the smart contract
- Creates permanent scarcity with every trade

#### Layer 2: Redemption Burn
- When users redeem iHhashi Coins for discounts, 50% is burned
- Example: Redeem 300 coins for R30 discount → 150 burned, 150 returned to pool
- Creates deflation tied to actual utility

#### Layer 3: Platform Revenue Buyback & Burn
- iHhashi commits 10% of platform delivery fees to monthly buyback & burn
- Creates direct link between platform success and token value
- Transparent, on-chain burns visible to all

#### Layer 4: Unstake Penalty Burn
- Early unstake penalties (5-15%) are burned, not kept by platform
- Removes supply from impatient sellers
- Rewards long-term holders with increased scarcity

**Projected Annual Burn Rate:**

| Mechanism | Est. % of Supply Burned/Year |
|-----------|------------------------------|
| Transaction Burn | 1-2% |
| Redemption Burn | 0.5-1% |
| Buyback & Burn | 2-3% |
| Unstake Penalties | 0.5-1% |
| **Total** | **4-7% annually** |

---

### 5. GOLD HORSE STATUS SYSTEM

**Integrating with Existing Blue Horse:**

```
Status Hierarchy:
├── UNVERIFIED (New user)
├── VERIFIED (Basic KYC)
├── BLUE HORSE (Full verification, existing)
└── GOLD HORSE (100,000+ HASHI staked 90+ days)
    ├── Priority delivery assignment for drivers
    ├── Reduced platform fees (5% vs 15% for merchants)
    ├── Exclusive merchant promotions
    ├── Governance voting rights
    └── 2x referral rewards
```

**Why 100,000 HASHI for Gold Horse?**

- At launch price of ~$0.001/HASHI, that's ~$100 stake
- Achievable for serious participants but creates exclusivity
- Must be staked 90+ days → prevents flash purchases for status
- Can coexist with Blue Horse (verification) → Gold is about economic commitment

**Dual Status Display:**

- A user can be both Blue Horse (verified) AND Gold Horse (staked)
- Badge shows both: 🐎💙🥇
- Blue = trust, Gold = economic stake

---

### 6. ANTI-DUMP & LIQUIDITY MECHANISMS

#### Problem: How to prevent dumping while maintaining liquidity?

#### Solution: Balanced Approach

**A. Liquidity Incentives (Not Mercenary Mining)**

Instead of pure emissions, use **fee-switched liquidity rewards**:

```
Liquidity Providers earn:
├── 60% of trading fees from their pool
├── 0.5x voting escrow boost (not 1x, to prevent whales)
└── No additional token emissions
```

This creates **real yield** from real activity, not inflationary rewards.

**B. Circuit Breaker for Extreme Volatility**

```solidity
// Pseudo-code for smart contract
if (price_drop_24h > 30%) {
    pause_trading_for(4 hours);
    emit_warning_event();
}
```

- Prevents cascade liquidations
- Gives market time to stabilise
- Only triggers on extreme moves (30%+ daily drop)

**C. Treasury Backstop**

- Treasury holds 10% of supply for market operations
- Can deploy liquidity during extreme dumps
- Transparent on-chain operations
- Governance vote required for deployment >1% of treasury

**D. Graduated Sell Tax**

```
Sell Tax (applies only to sells, not buys):
├── Holding < 30 days: 5% tax (4% burned, 1% to stakers)
├── Holding 30-90 days: 3% tax
├── Holding 90-365 days: 1% tax
└── Holding 365+ days: 0% tax
```

- Disincentivises flipping
- Rewards long-term holders with zero tax
- Tax revenue goes to ecosystem (burn + stakers), not team

---

### 7. EARLY ADOPTERS VS NEW USERS BALANCE

**The Challenge:** Early adopters want outsized rewards, but new users need fair entry.

**The Solution: Decay Model with Minimum Floor**

#### Airdrop Allocation (5% of supply):

```
Snapshot-based airdrop:
├── 50% to historical users (orders, deliveries, GMV)
├── 30% to current Blue Horse users
└── 20% to referral program participants

Claim mechanics:
├── 100% claimable immediately
├── BUT: If claimed within first 30 days → 30% locked for 90 days
└── If claimed after 30 days → 100% unlocked
```

#### Ongoing Emissions Decay:

```
Year 1: 20% of emissions
Year 2: 15% of emissions (25% reduction)
Year 3: 11.25% of emissions (25% reduction)
Year 4: 8.44% of emissions (25% reduction)
...

Decay continues until emissions reach 1% floor (forever)
```

**Why this works:**

- Early adopters get first-mover advantage (more coins, cheaper prices)
- New users can always earn, just at slightly lower rates
- Floor (1%) ensures perpetual incentives for new participants
- 25% annual decay is aggressive enough to reward early, gentle enough for latecomers

#### Activity-Based Bonuses (Equal Opportunity):

```
New User Bonuses (not time-based):
├── First order: +50 HASHI
├── First 10 orders: +200 HASHI
├── First delivery completed (drivers): +100 HASHI
├── First R1000 GMV (merchants): +500 HASHI
└── Referral bonuses: Same as early adopters
```

These bonuses are **identical for early and new users**—rewards activity, not timing.

---

### 8. COMPLETE FEE FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HASHI COIN FEE FLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Trade Happens: 1% fee on Base/Uniswap]                            │
│                         │                                            │
│         ┌───────────────┼───────────────┐                           │
│         ▼               ▼               ▼                           │
│    ┌─────────┐    ┌──────────┐    ┌─────────┐                       │
│    │ Platform│    │ Protocol │    │ Creator │                       │
│    │  20%    │    │   6%     │    │  54%*   │                       │
│    │iHhashi  │    │Zora+Dopp │    │ Pool    │                       │
│    └─────────┘    └──────────┘    └────┬────┘                       │
│         │                              │                            │
│         │                              ▼                            │
│         │         ┌────────────────────────────────┐               │
│         │         │     STAKEHOLDER REDISTRIBUTION │               │
│         │         ├────────────────────────────────┤               │
│         │         │  Merchants Pool: 18%           │               │
│         │         │  Drivers Pool: 18%            │               │
│         │         │  Customers Pool: 12%          │               │
│         │         │  Trade Referrer: 4%           │               │
│         │         │  Treasury: 2%                 │               │
│         │         └────────────────────────────────┘               │
│         │                              │                            │
│         ▼                              ▼                            │
│    [Platform Ops]              [Staking Rewards]                    │
│    + Buyback                   + Governance                         │
│    + Burn                      + Status                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

*Creator 54% redistributed as shown above
```

---

### 9. IMPLEMENTATION ROADMAP

#### Phase 1: Foundation (Weeks 1-4)
- [ ] Deploy iHhashi Coin on Zora V4
- [ ] Set platform referrer to iHhashi treasury
- [ ] Deploy staking contract (Hashi Vault)
- [ ] Snapshot for airdrop eligibility

#### Phase 2: Distribution (Weeks 5-8)
- [ ] Claim window opens for airdrop
- [ ] Merchant allocation based on GMV
- [ ] Driver allocation based on deliveries
- [ ] Initial liquidity provision

#### Phase 3: Staking Live (Weeks 9-12)
- [ ] Hashi Vault goes live
- [ ] Fee distribution begins
- [ ] Gold Horse status active
- [ ] First weekly reward distribution

#### Phase 4: Governance (Month 4+)
- [ ] Diamond Vault holders get voting rights
- [ ] Treasury allocation votes
- [ ] Fee adjustment proposals
- [ ] Protocol upgrade votes

---

### 10. KEY METRICS TO TRACK

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Staking Rate | >60% of supply | Shows confidence, reduces sell pressure |
| Average Stake Duration | >90 days | Indicates long-term belief |
| Gold Horse Count | 500+ by year 1 | Shows committed stakeholders |
| Burn Rate | 4-7% annually | Creates scarcity |
| Fee Distribution | Weekly, automated | Builds trust through consistency |
| Merchant Participation | >40% of merchants staked | Aligns supply side |

---

### 11. RISKS & MITIGATIONS

| Risk | Mitigation |
|------|------------|
| **Whale dominance** | Vote escrow with diminishing returns (2.5x max, not unlimited) |
| **Regulatory issues** | Pure utility token with no profit promises; fee share is "rebate" not "dividend" |
| **Low liquidity** | Treasury reserves for market making; fee-switched LP incentives |
| **Mercenary capital** | Time-weighted staking; sell taxes; no pure emissions |
| **Smart contract bugs** | Audited contracts; timelock on governance; multisig treasury |
| **Market manipulation** | Circuit breakers; transparent on-chain data; max wallet limits initially |

---

### 12. SUMMARY: THE HASHI SOVEREIGN MODEL

**What makes iHhashi Coin PRECIOUS?**

1. **Real Fee Sharing**: Not just discounts—actual revenue from trading activity
2. **Time-Weighted Staking**: Diamond hands earn 2.5x more than paper hands
3. **Multi-Layer Deflation**: 4-7% annual burn rate creates permanent scarcity
4. **Status Integration**: Gold Horse = economic commitment, not just verification
5. **Fair Distribution**: Activity-based rewards; decay model for sustainability
6. **Anti-Dump Design**: Sell taxes, unstake penalties, circuit breakers
7. **Real Utility**: Redeem for discounts, stake for earnings, hold for status

**The Bottom Line:**

iHhashi Coin becomes valuable because:
- **Supply decreases** through burns (deflation)
- **Demand increases** through utility (discounts + fee share)
- **Velocity decreases** through staking (time-weighted locks)
- **Trust increases** through transparency (on-chain everything)

This is not a rewards points system pretending to be crypto. This is **genuine ownership** in the iHhashi economy.

---

## APPENDIX: Comparison with Other Models

| Model | Approach | Flaw | Hashi Solution |
|-------|----------|------|----------------|
| **Binance BNB** | Burn + utility | Centralised control | Decentralised staking governance |
| **GMX** | Fee share to stakers | No merchant/driver split | Three-pool distribution |
| **UNI** | Governance only | No fee switch (yet) | Fee sharing from day 1 |
| **Cronos** | Cashback rewards | Inflationary | Deflationary burn mechanisms |
| **Stepn** | Move-to-earn | Infinite emissions | Capped emissions with floor |

---

*Document Version: 1.0*
*Created: 2026-03-02*
*Author: Zo (AI Agent) for iHhashi*
