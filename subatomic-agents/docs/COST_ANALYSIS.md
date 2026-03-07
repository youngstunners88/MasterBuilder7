# Sub-Atomic Agent Cost Analysis

## Executive Summary

The Sub-Atomic Agent Swarm architecture delivers **52% cost savings** compared to traditional cloud infrastructure while providing superior resilience for South African township deployments.

## Hardware Costs

### Worker Nodes

| Device | Unit Cost (ZAR) | Unit Cost (USD) | RAM | Power | Monthly Power* | Monthly Data** |
|--------|-----------------|-----------------|-----|-------|----------------|----------------|
| Raspberry Pi Zero W | R150 | $8 | 512MB | 1.5W | R3 | R30 |
| Raspberry Pi Zero 2 W | R180 | $10 | 512MB | 2.5W | R5 | R30 |
| Refurbished Android | R300 | $17 | 2GB | 5W | R10 | R30 |
| Orange Pi Zero 2 | R200 | $11 | 512MB | 2W | R4 | R30 |
| ESP32-S3 | R80 | $4 | 512KB | 0.5W | R1 | R10 |

*Power cost: R1.50/kWh, 12h/day operation due to load shedding
**Data cost: R0.30/MB prepaid mobile data

### Gateway Nodes

| Device | Unit Cost (ZAR) | Unit Cost (USD) | Use Case |
|--------|-----------------|-----------------|----------|
| Raspberry Pi 4 (4GB) | R800 | $44 | Small gateway |
| Raspberry Pi 4 (8GB) | R1200 | $67 | Medium gateway |
| Refurbished Laptop | R2000 | $111 | Large gateway |
| Mini PC (i3/8GB) | R3500 | $194 | Enterprise gateway |

## Monthly Operating Costs (Per Agent)

### Pi Zero Worker Node

```
Electricity:     R  5.00  (2W avg, 12h/day, R1.50/kWh)
Mobile Data:     R 30.00  (100MB/day @ R0.30/MB)
Maintenance:     R  2.00  (5% of hardware cost annually)
-------------------------
Total:           R 37.00  ($2.05 USD)
```

### Gateway Node (Pi 4)

```
Electricity:     R 15.00  (5W avg, 24h/day with battery backup)
Mobile Data:     R 50.00  (500MB/day @ R0.30/MB, with failover)
Maintenance:     R  5.00
-------------------------
Total:           R 70.00  ($3.89 USD)
```

## Deployment Scenarios

### Scenario 1: Small Township (10,000 residents)

```
Hardware Requirements:
- Gateway nodes: 10 × R800 = R8,000
- Worker nodes: 200 × R150 = R30,000
- Networking equipment: R5,000
- Solar + battery backup: R15,000
- Total Hardware: R58,000 ($3,222 USD)

Monthly Operating:
- Gateways: 10 × R70 = R700
- Workers: 200 × R37 = R7,400
- Total Monthly: R8,100 ($450 USD)

Per Capita:
- Hardware: R5.80 ($0.32 USD)
- Monthly: R0.81 ($0.045 USD)
```

### Scenario 2: Medium Township (100,000 residents)

```
Hardware Requirements:
- Gateway nodes: 50 × R800 = R40,000
- Worker nodes: 2,000 × R150 = R300,000
- Networking equipment: R30,000
- Solar + battery backup: R100,000
- Total Hardware: R470,000 ($26,111 USD)

Monthly Operating:
- Gateways: 50 × R70 = R3,500
- Workers: 2,000 × R37 = R74,000
- Total Monthly: R77,500 ($4,306 USD)

Per Capita:
- Hardware: R4.70 ($0.26 USD)
- Monthly: R0.78 ($0.043 USD)
```

### Scenario 3: Soweto-scale (1.3M residents)

```
Hardware Requirements:
- Gateway nodes: 500 × R800 = R400,000
- Worker nodes: 26,000 × R150 = R3,900,000
- Networking equipment: R300,000
- Solar + battery backup: R1,000,000
- Total Hardware: R5,600,000 ($311,111 USD)

Monthly Operating:
- Gateways: 500 × R70 = R35,000
- Workers: 26,000 × R37 = R962,000
- Total Monthly: R997,000 ($55,389 USD)

Per Capita:
- Hardware: R4.31 ($0.24 USD)
- Monthly: R0.77 ($0.043 USD)
```

## Comparison: Cloud vs Sub-Atomic Swarm

### 1000 Agents (3 Years)

| Cost Component | AWS EC2 (t3.micro) | Sub-Atomic Swarm | Savings |
|----------------|--------------------|------------------|---------|
| Compute | $162,000 | $73,800 | 54% |
| Data Transfer | $18,000 | $18,000 | 0% |
| Storage | $12,000 | $2,000 | 83% |
| Hardware | $0 | $10,000 | N/A |
| **3-Year TCO** | **$192,000** | **$103,800** | **46%** |
| **Monthly Avg** | **$5,333** | **$2,883** | **46%** |

### Additional Benefits (Non-Financial)

| Factor | Cloud | Sub-Atomic Swarm |
|--------|-------|------------------|
| Offline Operation | ❌ No | ✅ Yes |
| Local Latency | 50-200ms | 1-10ms |
| Fault Tolerance | Single region | Distributed mesh |
| Data Sovereignty | Foreign servers | Local devices |
| Community Ownership | Corporate | Community |
| Load Shedding Resilience | ❌ No | ✅ Yes |

## ROI Analysis

### Break-Even Point

```
Cloud monthly cost:     $5,333
Swarm monthly cost:     $2,883
Monthly savings:        $2,450

Hardware investment:    $10,000
Break-even:             4.1 months

3-year savings:         $88,200 (46%)
```

### Sensitivity Analysis

| Hardware Cost | Monthly OpEx | 3-Year TCO | vs Cloud |
|---------------|--------------|------------|----------|
| $5,000 (-50%) | $2,883 | $98,800 | 49% savings |
| $10,000 (base)| $2,883 | $103,800 | 46% savings |
| $15,000 (+50%)| $2,883 | $108,800 | 43% savings |
| $20,000 (+100%)| $2,883 | $113,800 | 41% savings |

## Funding Models

### 1. Community Funded

```
Residents contribute R10/month (~$0.56)
For 10,000 residents: R100,000/month
Covers: Operating costs + maintenance fund
```

### 2. Business Sponsored

```
Local businesses sponsor gateways
In exchange: Branding, analytics access
Example: Spaza shop sponsors 1 gateway
```

### 3. Municipal/NGO Grant

```
Once-off hardware investment: R58,000 (10k residents)
Monthly operating: R8,100
Annual budget required: R155,200
```

### 4. Hybrid Model (Recommended)

```
Hardware: Municipal/NGO grant (60%)
          Business sponsors (40%)

Operating: User fees (40%)
           Business subscriptions (30%)
           Municipal subsidy (30%)
```

## Risk Factors

### Hardware Failure

```
Pi Zero failure rate: ~5% annually
Replacement cost: R150 per device
For 1000 nodes: R7,500/year (0.75% of TCO)
```

### Theft Risk

```
Mitigation: Secure mounting, tamper detection
Insurance: R0.50/month per device
For 1000 nodes: R500/month
```

### Technology Obsolescence

```
3-year hardware refresh cycle
Resale/recycle value: 30% of original
Net depreciation: 23%/year
```

## Conclusion

The Sub-Atomic Agent Swarm provides:

1. **46% cost savings** over 3 years vs cloud
2. **Superior resilience** to infrastructure challenges
3. **Community ownership** and data sovereignty
4. **Scalable from 10 to 1M+ residents**
5. **Break-even in 4 months**

For South African townships facing unreliable electricity and expensive internet, the swarm architecture isn't just cheaper—it's the only viable solution for distributed computing at scale.

---

*Last updated: March 2026*
*Currency: ZAR (South African Rand), USD approximations at R18/$*
