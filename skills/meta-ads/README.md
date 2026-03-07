# 📱 Meta-Ads Automation

> Autonomous Meta Ads management for iHhashi

## Overview

Maximize customer acquisition efficiency through autonomous ad management for the iHhashi delivery platform.

## Daily Workflow

1. **Health Check** - Assess overall account health
2. **Fatigue Detection** - Find ads with audience fatigue (frequency > 3.5)
3. **Auto-Pause** - Stop campaigns bleeding money (CPA > 2.5x target for 48hrs)
4. **Budget Optimization** - Shift spend to top performers
5. **Copy Generation** - Create new variations from winners
6. **Morning Brief** - Send Telegram summary

## Key Metrics

| Metric | Threshold |
|--------|-----------|
| Target CPA | $5 (configurable) |
| Fatigue threshold | Frequency > 3.5 |
| Auto-pause threshold | CPA > 2.5x target for 48hrs |
| Budget shift cap | 20% per day |

## Safety Rules

1. Never delete campaigns - only pause
2. New ads always start paused
3. Require Telegram approval for budget shifts > $50/day
4. Log all actions with timestamps
5. Create GitHub issues for anomalies

## Issue Integration

| Detection | Label |
|-----------|-------|
| Critical issues | `ads-critical` |
| Fatigue warnings | `ads-fatigue` |
| Budget opportunities | `ads-budget` |
| Copy ideas | `ads-copy` |

## Commands

### Full Autonomous Cycle

```bash
bun skills/meta-ads/scripts/autonomous.ts --execute --telegram
```

### Individual Scripts

```bash
# Health check
bun skills/meta-ads/scripts/health-check.ts

# Fatigue detection
bun skills/meta-ads/scripts/fatigue-detector.ts

# Auto-pause bleeders
bun skills/meta-ads/scripts/auto-pause.ts

# Budget optimization
bun skills/meta-ads/scripts/budget-optimizer.ts

# Copy generation
bun skills/meta-ads/scripts/copy-generator.ts

# Morning brief
bun skills/meta-ads/scripts/morning-brief.ts
```

## Context

iHhashi is a delivery platform for:
- Groceries
- Food
- Fruits & vegetables
- Dairy products
- Personal courier services

**Target audience:** South Africa

## Required Secrets

| Secret | Description |
|--------|-------------|
| `META_AD_ACCOUNT_ID` | Meta ad account ID |
| `META_ACCESS_TOKEN` | Marketing API token |
| `META_PAGE_ID` | Facebook Page ID |
| `META_INSTAGRAM_ACCOUNT_ID` | Instagram account (optional) |
| `META_TARGET_CPA` | Target CPA (default: $5) |
| `GITHUB_TOKEN` | For issue creation |
| `TELEGRAM_BOT_TOKEN` | For notifications |
