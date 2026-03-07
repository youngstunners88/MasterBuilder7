# iHhashi Meta Ads Automation

Autonomous Meta Ads management system for iHhashi delivery platform.

## What It Does

This system runs daily to:
1. **Health Check** - Answers 5 key questions about ad performance
2. **Fatigue Detection** - Catches ads before they die (frequency > 3.5)
3. **Auto-Pause** - Stops bleeders (CPA > 2.5x target for 48hrs)
4. **Budget Optimization** - Shifts spend to winning campaigns
5. **Copy Generation** - Writes new ad copy from top performers
6. **Morning Brief** - Sends Telegram summary for approval

## Quick Start

```bash
# Run full autonomous cycle
bun marketing/meta-ads/scripts/autonomous.ts --execute --telegram

# Run individual components
bun marketing/meta-ads/scripts/health-check.ts
bun marketing/meta-ads/scripts/fatigue-detector.ts
bun marketing/meta-ads/scripts/auto-pause.ts
bun marketing/meta-ads/scripts/budget-optimizer.ts
bun marketing/meta-ads/scripts/copy-generator.ts
bun marketing/meta-ads/scripts/morning-brief.ts
```

## Required Secrets

Set in Zo Settings > Advanced:
- `META_AD_ACCOUNT_ID` - Your Meta ad account ID
- `META_ACCESS_TOKEN` - Meta Marketing API token
- `META_PAGE_ID` - Facebook Page ID
- `META_INSTAGRAM_ACCOUNT_ID` - Instagram account ID (optional)
- `META_TARGET_CPA` - Target cost per acquisition (default: $5)

## How It Improves

This system integrates with GitHub Issues:

1. **Automatic Issue Creation** - When ads fail or opportunities are detected, issues are created
2. **Performance Logging** - All decisions logged for review
3. **Community Improvements** - Issues can be discussed and resolved
4. **Version Control** - All changes tracked in git

### Issue Labels

- `ads-health` - Health check findings
- `ads-fatigue` - Fatigue detection alerts
- `ads-budget` - Budget optimization suggestions
- `ads-copy` - Copy generation requests
- `ads-critical` - Requires immediate attention

## Files

```
marketing/meta-ads/
├── README.md              # This file
├── SKILL.md               # Skill definition for Zo
├── scripts/
│   ├── autonomous.ts      # Run all steps
│   ├── health-check.ts    # Daily health check
│   ├── fatigue-detector.ts # Detect dying ads
│   ├── auto-pause.ts      # Stop bleeders
│   ├── budget-optimizer.ts # Shift to winners
│   ├── copy-generator.ts  # Generate ad copy
│   ├── morning-brief.ts   # Telegram summary
│   ├── ad-upload.ts       # Upload new ads
│   └── github-issues.ts   # Create issues from findings
└── references/
    └── meta-api.md        # Meta API reference
```

## Scheduled Execution

To run every morning at 8 AM SAST, create a scheduled agent:

```bash
bun marketing/meta-ads/scripts/autonomous.ts --execute --telegram
```

With rrule: `FREQ=DAILY;BYHOUR=6;BYMINUTE=0` (UTC 6:00 = SAST 8:00)

## Safety Features

- All ads created in PAUSED state by default
- Auto-pause requires 48hrs of poor performance
- Budget shifts capped at 20% per day
- All actions logged with timestamps
- Telegram approval required for major changes

## Metrics Tracked

- Spend efficiency
- CPA vs target
- CTR trends
- Frequency (audience fatigue)
- Conversion rates
- ROAS (Return on Ad Spend)
