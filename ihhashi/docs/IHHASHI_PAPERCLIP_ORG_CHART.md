# iHhashi Paperclip Org Chart

## Overview

This document defines the AI agent organization structure for running iHhashi as a semi-autonomous business using Paperclip orchestration.

---

## Company: iHhashi (Pty) Ltd

**Mission**: Build the #1 food delivery platform in South Africa, starting with Johannesburg, reaching R10M monthly GMV by end of 2026.

---

## Org Chart

```
                    ┌─────────────────┐
                    │   BOARD (You)   │
                    │   kofi.zo       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      CEO        │
                    │  "Mzansi"       │
                    │  Strategic      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│     CTO       │   │   COO         │   │   CFO         │
│ "TechLead"    │   │ "Operations"  │   │ "Finance"     │
│ Engineering   │   │ Logistics     │   │ Money         │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
   ┌────┴────┐         ┌────┴────┐              │
   │         │         │         │              │
┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐         ┌──▼──┐
│ Dev │  │ QA  │  │Sup- │  │Cust-│         │ Acc │
│Team │  │Team │  │port │  │omer │         │ount │
│     │  │     │  │Team │  │Care │         │ing  │
└─────┘  └─────┘  └─────┘  └─────┘         └─────┘
```

---

## Employee Roster

### Executive Team

| ID | Name | Role | Budget (R/month) | Heartbeat | Skills |
|----|------|------|------------------|-----------|--------|
| `ceo-mzansi` | Mzansi | CEO | R5,000 | Daily 9:00 SAST | Strategy, partnerships, investor relations |
| `cto-techlead` | TechLead | CTO | R4,000 | Daily 8:00 SAST | Architecture, code review, security |
| `coo-operations` | Operations | COO | R3,500 | Daily 7:00 SAST | Vendor onboarding, logistics, fleet management |
| `cfo-finance` | Finance | CFO | R3,000 | Weekly (Mon) | Payouts, accounting, financial reports |

### Engineering Team

| ID | Name | Role | Budget (R/month) | Heartbeat | Skills |
|----|------|------|------------------|-----------|--------|
| `dev-backend` | BackendBot | Backend Developer | R2,500 | Daily 9:00 SAST | FastAPI, MongoDB, Redis, payments |
| `dev-frontend` | FrontendBot | Frontend Developer | R2,500 | Daily 9:00 SAST | React, Tailwind, mobile, PWA |
| `dev-mobile` | MobileBot | Mobile Developer | R2,000 | Daily 10:00 SAST | React Native, APK builds, Play Store |
| `qa-engineer` | QABot | QA Engineer | R1,500 | Daily 6:00 SAST | Testing, CI/CD, security scans |

### Operations Team

| ID | Name | Role | Budget (R/month) | Heartbeat | Skills |
|----|------|------|------------------|-----------|--------|
| `support-agent` | SupportBot | Customer Support | R1,500 | Daily 7:00-22:00 | Zendesk, WhatsApp, complaints, refunds |
| `vendor-success` | VendorBot | Vendor Success | R1,500 | Daily 9:00 | Onboarding, menu optimization, analytics |
| `fleet-manager` | FleetBot | Fleet Coordinator | R1,000 | Daily 6:00 | Rider dispatch, route optimization, earnings |

### Finance Team

| ID | Name | Role | Budget (R/month) | Heartbeat | Skills |
|----|------|------|------------------|-----------|--------|
| `accountant` | AccountantBot | Accountant | R1,000 | Weekly (Sun 11:11) | Paystack transfers, payouts, reconciliation |
| `analyst` | AnalystBot | Business Analyst | R1,000 | Weekly (Mon) | GMV reports, churn analysis, unit economics |

### Special Agents

| ID | Name | Role | Budget (R/month) | Heartbeat | Skills |
|----|------|------|------------------|-----------|--------|
| `nduna-intel` | NdunaBrain | AI Concierge | R2,000 | Real-time | Nduna chatbot, NLP, Zulu/Sotho/Xhosa support |
| `marketing-bot` | MarketingBot | Growth Hacker | R2,000 | Daily 10:00 | Social media, campaigns, referral tracking |
| `compliance-officer` | ComplianceBot | Compliance | R500 | Weekly | FICA, POPIA, vendor verification |

---

## Total Monthly Budget: R30,000

---

## Goal Hierarchy

### Level 1: Company Goal
```
Goal: "Build #1 food delivery platform in South Africa"
KPI: R10M monthly GMV by Dec 2026
```

### Level 2: Department Goals

**CTO Goals:**
- 99.9% API uptime
- <200ms average response time
- Zero security breaches
- Mobile app 4.5+ star rating

**COO Goals:**
- 500+ active vendors
- 1000+ registered delivery partners
- <30 min average delivery time
- 95% order fulfillment rate

**CFO Goals:**
- Weekly payouts processed on time (Sunday 11:11)
- <2% payment failure rate
- Monthly financial reports by 5th of each month

### Level 3: Individual Goals

Each agent has specific tasks that roll up to department goals:

```
dev-backend:
  - Fix API bugs within 24 hours
  - Deploy new features weekly
  - Maintain test coverage >80%

support-agent:
  - Respond to tickets within 15 minutes
  - Resolve 90% of issues in first contact
  - Escalate only critical issues
```

---

## Governance Rules

### Approval Gates
1. **Hiring new agents**: Board approval required
2. **Budget changes >R500**: CEO approval required
3. **Code changes to payments**: CTO approval required
4. **Vendor payouts >R10,000**: CFO approval required
5. **Database schema changes**: CTO + QA approval required

### Auto-Pause Conditions
- Agent exceeds budget by 20%
- Agent fails heartbeat 3 consecutive times
- Critical error detected (payment failure, data breach)

### Escalation Paths
```
Support issue → support-agent → coo-operations → ceo-mzansi
Bug report → qa-engineer → dev-team → cto-techlead → ceo-mzansi
Payment issue → accountant → cfo-finance → ceo-mzansi
```

---

## Integration with Existing Systems

### Nduna Chatbot → NdunaBrain Agent
The existing Nduna chatbot becomes the "nduna-intel" agent with:
- Real-time customer support
- Multi-language support (English, Zulu, Sotho, Xhosa, Afrikaans, Tswana)
- Order tracking and status updates
- Vendor recommendations

### Marketing OpenClaw → MarketingBot Agent
The Marketing OpenClaw instance becomes the marketing-bot:
- Automated social media posts
- Referral campaign management
- Performance analytics

### Route Optimization → FleetBot Agent
The route_optimizer service becomes fleet-bot:
- Automatic dispatch optimization
- Real-time delivery tracking
- Earnings calculations

---

## Paperclip Configuration

```yaml
# Company configuration for iHhashi
company:
  id: ihhashi-sa
  name: "iHhashi (Pty) Ltd"
  timezone: "Africa/Johannesburg"
  currency: "ZAR"
  
agents:
  - id: ceo-mzansi
    name: "Mzansi"
    role: "CEO"
    runtime: "openclaw"
    model: "claude-sonnet-4"
    budget_monthly: 5000
    heartbeat: "0 9 * * *"
    
  - id: cto-techlead
    name: "TechLead"
    role: "CTO"
    runtime: "openclaw"
    model: "claude-sonnet-4"
    budget_monthly: 4000
    heartbeat: "0 8 * * *"
    
  # ... more agents
```

---

## Getting Started

1. **Install Paperclip**:
   ```bash
   cd /home/workspace/Paperclip
   pnpm install
   pnpm dev
   ```

2. **Create iHhashi company**:
   ```bash
   curl -X POST http://localhost:3100/api/companies \
     -H "Content-Type: application/json" \
     -d '{"name": "iHhashi (Pty) Ltd", "slug": "ihhashi-sa"}'
   ```

3. **Add agents** via the Paperclip UI at `http://localhost:3100`

4. **Connect runtimes**:
   - OpenClaw agents: Configure with OpenClaw gateway
   - Claude Code agents: Set up API keys
   - Custom agents: Use HTTP heartbeat endpoint

---

## Next Steps

1. Set up Paperclip trial instance
2. Configure iHhashi company and goals
3. Hire executive team agents
4. Set up heartbeat schedules
5. Monitor from mobile dashboard
