# 🤖 iHhashi Agent System - Cost Analysis

## 📊 Executive Summary

| Item | Cost (Monthly) |
|------|----------------|
| **5 Production Agents** | **$280 - $520/month** |
| **Recommended: Separate Repo** | **Yes** |

---

## 💰 Detailed Cost Breakdown

### Agent 1: Auto Customer Support Bot 🤖

**Components:**
- `customer-support` agent
- `orchestrator` agent
- Telegram Bot API integration
- Supabase database queries

**Resource Usage:**
| Resource | Usage | Cost |
|----------|-------|------|
| Compute (always-on) | 2 vCPU, 4GB RAM | $40-60/mo |
| OpenAI/Groq API calls | ~10K requests/day | $50-80/mo |
| Supabase queries | ~50K/day | Included in main |
| Telegram Bot | Free | $0 |
| **Subtotal** | | **$90-140/mo** |

**Scaling Factors:**
- More support tickets = higher API costs
- Can reduce with caching: -$30/mo

---

### Agent 2: Competitor Price Monitor 📊

**Components:**
- `researcher` agent
- `analyst` agent  
- `ops` agent
- Web scraping (Puppeteer/Playwright)
- Data storage

**Resource Usage:**
| Resource | Usage | Cost |
|----------|-------|------|
| Compute (scheduled) | Run 4x/day, 30min each | $15-25/mo |
| Browser automation | ~20 scrapes/day | $10-20/mo |
| Data storage | ~500MB/month | $5/mo |
| API (if using scraper APIs) | - | $20-50/mo |
| **Subtotal** | | **$50-100/mo** |

**Notes:**
- Can run on cheaper spot instances: -$10/mo
- Use cached results to reduce scrapes: -$15/mo

---

### Agent 3: Multi-Lang Content Factory 🌍

**Components:**
- `writer` agent
- `translator` agent
- `social-media` agent
- Translation API (Google/DeepL)
- Social media APIs

**Resource Usage:**
| Resource | Usage | Cost |
|----------|-------|------|
| Compute (on-demand) | ~2hrs/day | $20-40/mo |
| Translation API | ~50K chars/day | $30-50/mo |
| Image generation (optional) | ~100 images/mo | $20-40/mo |
| Social media APIs | Free tiers | $0 |
| **Subtotal** | | **$70-130/mo** |

**Notes:**
- Use free translation tier: -$20/mo
- Reduce post frequency: -$15/mo

---

### Agent 4: Smart Restaurant Onboarding 🍽️

**Components:**
- `orchestrator` agent
- `coder` agent
- `doc-writer` agent
- Document generation
- Template rendering

**Resource Usage:**
| Resource | Usage | Cost |
|----------|-------|------|
| Compute (on-demand) | ~20 onboardings/day, 5min each | $30-50/mo |
| Document generation | PDF/API calls | $10-20/mo |
| Template storage | Minimal | $0 |
| **Subtotal** | | **$40-70/mo** |

**Notes:**
- Very efficient - scales with new vendors
- Can batch process: -$10/mo

---

### Agent 5: Fraud Detection System 🛡️

**Components:**
- `security-auditor` agent
- `analyst` agent
- `debugger` agent
- Real-time monitoring
- ML model inference (optional)

**Resource Usage:**
| Resource | Usage | Cost |
|----------|-------|------|
| Compute (always-on) | 1 vCPU, 2GB RAM | $30-50/mo |
| Database queries | High volume | Included |
| ML inference (if used) | ~10K predictions/day | $30-60/mo |
| Alerting (SMS/Email) | ~100 alerts/mo | $5-10/mo |
| **Subtotal** | | **$65-120/mo** |

**Notes:**
- Critical system - don't skimp here
- Rule-based detection cheaper: -$30/mo

---

## 📈 Total Monthly Costs

### Optimized Setup (Recommended)
| Agent | Cost |
|-------|------|
| Customer Support | $90 |
| Price Monitor | $50 |
| Content Factory | $70 |
| Restaurant Onboarding | $40 |
| Fraud Detection | $65 |
| **TOTAL** | **$315/mo** |

### Full-Featured Setup
| Agent | Cost |
|-------|------|
| Customer Support | $140 |
| Price Monitor | $100 |
| Content Factory | $130 |
| Restaurant Onboarding | $70 |
| Fraud Detection | $120 |
| **TOTAL** | **$560/mo** |

---

## 🏗️ Infrastructure Requirements

### Option A: All-in-One (iHhashi Repo)
**Cost:** Included in main app infrastructure
**Pros:**
- Simpler deployment
- Shared database
- Easier monitoring

**Cons:**
- Agents compete with main app resources
- Harder to scale independently
- Risk of affecting main app

**Best for:** MVP, early stage (< 100 vendors)

---

### Option B: Separate Agent Repo (Recommended)
**Additional Cost:** $50-100/mo for separate infrastructure
**Pros:**
- Independent scaling
- Isolated failures
- Clear separation of concerns
- Can use cheaper spot instances
- Easier to open-source/monetize later

**Cons:**
- More complex deployment
- Inter-service communication overhead
- Additional monitoring needed

**Best for:** Production, scale (> 100 vendors)

---

## 📁 Recommended Repository Structure

### Option B: Separate Repo (Recommended)

```
ihhashi-agents/
├── README.md
├── docker-compose.yml
├── .env.example
├── agents/
│   ├── customer-support/
│   │   ├── Dockerfile
│   │   ├── src/
│   │   └── requirements.txt
│   ├── price-monitor/
│   │   ├── Dockerfile
│   │   └── src/
│   ├── content-factory/
│   │   ├── Dockerfile
│   │   └── src/
│   ├── onboarding/
│   │   ├── Dockerfile
│   │   └── src/
│   └── fraud-detection/
│       ├── Dockerfile
│       └── src/
├── shared/
│   ├── database/
│   ├── models/
│   └── utils/
├── deployments/
│   ├── railway.yml
│   └── kubernetes/
└── docs/
    ├── ARCHITECTURE.md
    └── COST_OPTIMIZATION.md
```

### Why Separate Repo?

1. **Different Release Cycles**
   - Main app: Weekly releases
   - Agents: Daily/hourly updates

2. **Different Teams** (Future)
   - Main app: Core dev team
   - Agents: ML/Automation team

3. **Scaling Patterns**
   - Main app: Horizontal scaling
   - Agents: Vertical + spot instances

4. **Failure Domains**
   - Agent crash ≠ App crash

5. **Cost Optimization**
   - Agents can run on cheaper infra
   - Spot instances, batch processing

---

## 🎯 Recommendation: Hybrid Approach

### Phase 1 (Now - 6 months): Monorepo
- Keep agents in main iHhashi repo
- Share database and infrastructure
- Lower complexity, faster iteration

**Cost:** $315-560/mo (shared infra)

### Phase 2 (6-12 months): Separate Repo
- Extract agents to `ihhashi-agents`
- Microservices architecture
- Independent scaling

**Cost:** $365-660/mo (+$50-100 for separate infra)

---

## 💡 Cost Optimization Tips

### 1. Use Spot/Preemptible Instances
**Savings:** 60-70% on compute
**Risk:** Agents can be interrupted
**Good for:** Price monitor, content factory

### 2. Batch Processing
**Savings:** 30-40% on API costs
**How:** Queue jobs, process together
**Good for:** Onboarding, content generation

### 3. Caching
**Savings:** 20-30% on AI API calls
**How:** Cache common responses
**Good for:** Customer support, translations

### 4. Smart Scheduling
**Savings:** 50% on compute
**How:** Run during off-peak hours
**Good for:** Price monitor, reports

### 5. Free Tiers
**Savings:** $50-100/mo
- Google Translate API: 500K chars/mo free
- DeepL: 500K chars/mo free
- Telegram Bot: Free
- Social media APIs: Free tiers

---

## 📊 ROI Projection

### Costs vs Benefits

| Agent | Monthly Cost | Time Saved | Value |
|-------|--------------|------------|-------|
| Customer Support | $90 | 40 hrs/mo | R15,000 |
| Price Monitor | $50 | 10 hrs/mo | R5,000 |
| Content Factory | $70 | 20 hrs/mo | R8,000 |
| Onboarding | $40 | 15 hrs/mo | R6,000 |
| Fraud Detection | $65 | Risk mitigation | R20,000+ |
| **TOTAL** | **$315** | **85 hrs/mo** | **R54,000+** |

**ROI: ~18x** 🚀

---

## ✅ Final Recommendation

### Immediate Action (This Week)
1. ✅ **Keep agents in main repo for now**
2. ✅ **Implement Customer Support + Fraud Detection first**
3. ✅ **Use optimized cost structure ($155/mo)**

### 6-Month Plan
1. Monitor agent performance
2. Extract to separate repo when:
   - > 100 active vendors
   - Agent resource usage > 30% of main app
   - Need independent scaling

### GitHub Strategy
```
Now:        youngstunners88/ihhashi (monorepo)
6 months:   youngstunners88/ihhashi-agents (extracted)
```

---

*Analysis completed by Kimi + OpenFang Agents*  
*Date: 2026-03-06*
