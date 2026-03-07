#!/usr/bin/env bun
/**
 * Meta Ads Health Check
 * 
 * Answers the 5 questions every morning:
 * 1. Am I on track?
 * 2. What's running?
 * 3. Who's winning?
 * 4. Who's bleeding?
 * 5. Any fatigue?
 * 
 * Usage:
 *   bun health-check.ts
 *   bun health-check.ts --json
 */

const META_API_VERSION = "v21.0";
const META_BASE_URL = `https://graph.facebook.com/${META_API_VERSION}`;

interface EnvConfig {
  appId: string;
  appSecret: string;
  adAccountId: string;
  accessToken: string;
  targetCpa: number;
}

function getConfig(): EnvConfig {
  const config = {
    appId: process.env.META_APP_ID || "",
    appSecret: process.env.META_APP_SECRET || "",
    adAccountId: process.env.META_AD_ACCOUNT_ID || "",
    accessToken: process.env.META_ACCESS_TOKEN || "",
    targetCpa: parseFloat(process.env.META_TARGET_CPA || "5.00"),
  };

  if (!config.accessToken || !config.adAccountId) {
    console.error("❌ Missing Meta API credentials");
    console.error("Set these environment variables:");
    console.error("  META_AD_ACCOUNT_ID");
    console.error("  META_ACCESS_TOKEN");
    process.exit(1);
  }

  return config;
}

async function metaApi(endpoint: string, params: Record<string, string>, accessToken: string) {
  const url = new URL(`${META_BASE_URL}${endpoint}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
  url.searchParams.set("access_token", accessToken);

  const response = await fetch(url.toString());
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Meta API error: ${response.status} - ${error}`);
  }
  return response.json();
}

interface Campaign {
  id: string;
  name: string;
  status: string;
  objective: string;
  daily_budget?: string;
  lifetime_budget?: string;
}

interface CampaignInsights {
  campaign_id: string;
  campaign_name?: string;
  spend: string;
  impressions: string;
  clicks: string;
  actions: Array<{ action_type: string; value: string }>;
  cost_per_action_type: Array<{ action_type: string; value: string }>;
  cpc: string;
  cpm: string;
  ctr: string;
  frequency?: string;
}

interface HealthReport {
  timestamp: string;
  summary: {
    totalSpend: number;
    totalImpressions: number;
    totalClicks: number;
    totalConversions: number;
    avgCpa: number;
    avgCtr: number;
    onTrack: boolean;
  };
  running: Campaign[];
  winners: Array<{ id: string; name: string; cpa: number; spend: number; conversions: number }>;
  bleeders: Array<{ id: string; name: string; cpa: number; spend: number; conversions: number }>;
  fatigue: Array<{ id: string; name: string; frequency: number }>;
}

async function getActiveCampaigns(adAccountId: string, accessToken: string): Promise<Campaign[]> {
  const data = await metaApi(
    `/${adAccountId}/campaigns`,
    {
      fields: "id,name,status,objective,daily_budget,lifetime_budget",
      filtering: '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
      limit: "50",
    },
    accessToken
  );
  return (data as any).data || [];
}

async function getCampaignInsights(
  adAccountId: string,
  accessToken: string,
  dateRange: string = "last_7d"
): Promise<CampaignInsights[]> {
  const data = await metaApi(
    `/${adAccountId}/insights`,
    {
      level: "campaign",
      date_preset: dateRange,
      fields: "campaign_id,campaign_name,spend,impressions,clicks,actions,cost_per_action_type,cpc,cpm,ctr,frequency",
      limit: "100",
    },
    accessToken
  );
  return (data as any).data || [];
}

function extractConversions(insights: CampaignInsights): number {
  const purchaseAction = insights.actions?.find(
    (a) => a.action_type === "purchase" || a.action_type === "omni_purchase"
  );
  return purchaseAction ? parseInt(purchaseAction.value) : 0;
}

function calculateCpa(insights: CampaignInsights): number {
  const conversions = extractConversions(insights);
  if (conversions === 0) return Infinity;
  return parseFloat(insights.spend) / conversions;
}

async function runHealthCheck(): Promise<HealthReport> {
  const config = getConfig();
  console.log("🔍 Running Meta Ads Health Check...\n");

  // Get active campaigns
  const campaigns = await getActiveCampaigns(config.adAccountId, config.accessToken);
  console.log(`📊 Found ${campaigns.length} active campaigns\n`);

  // Get insights
  const insights = await getCampaignInsights(config.adAccountId, config.accessToken);

  // Build campaign map
  const campaignMap = new Map<string, Campaign>();
  campaigns.forEach((c) => campaignMap.set(c.id, c));

  // Analyze
  let totalSpend = 0;
  let totalImpressions = 0;
  let totalClicks = 0;
  let totalConversions = 0;

  const winners: HealthReport["winners"] = [];
  const bleeders: HealthReport["bleeders"] = [];
  const fatigue: HealthReport["fatigue"] = [];

  for (const insight of insights) {
    const spend = parseFloat(insight.spend);
    const impressions = parseInt(insight.impressions);
    const clicks = parseInt(insight.clicks);
    const conversions = extractConversions(insight);
    const cpa = calculateCpa(insight);
    const ctr = parseFloat(insight.ctr) || 0;
    const frequency = parseFloat(insight.frequency || "0");

    totalSpend += spend;
    totalImpressions += impressions;
    totalClicks += clicks;
    totalConversions += conversions;

    const campaignName = insight.campaign_name || campaignMap.get(insight.campaign_id)?.name || "Unknown";

    // Check for fatigue (frequency > 3.5)
    if (frequency > 3.5) {
      fatigue.push({ id: insight.campaign_id, name: campaignName, frequency });
    }

    // Categorize by CPA
    if (conversions > 0) {
      if (cpa <= config.targetCpa * 1.2) {
        winners.push({ id: insight.campaign_id, name: campaignName, cpa, spend, conversions });
      } else if (cpa > config.targetCpa * 2.5) {
        bleeders.push({ id: insight.campaign_id, name: campaignName, cpa, spend, conversions });
      }
    }
  }

  // Sort
  winners.sort((a, b) => a.cpa - b.cpa);
  bleeders.sort((a, b) => b.cpa - a.cpa);
  fatigue.sort((a, b) => b.frequency - a.frequency);

  const avgCpa = totalConversions > 0 ? totalSpend / totalConversions : Infinity;
  const avgCtr = totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0;
  const onTrack = avgCpa <= config.targetCpa * 1.5;

  const report: HealthReport = {
    timestamp: new Date().toISOString(),
    summary: {
      totalSpend,
      totalImpressions,
      totalClicks,
      totalConversions,
      avgCpa,
      avgCtr,
      onTrack,
    },
    running: campaigns,
    winners: winners.slice(0, 5),
    bleeders: bleeders.slice(0, 5),
    fatigue: fatigue.slice(0, 5),
  };

  // Print report
  console.log("═══════════════════════════════════════════════════════");
  console.log("📈 SUMMARY");
  console.log("═══════════════════════════════════════════════════════");
  console.log(`Spend:        $${totalSpend.toFixed(2)}`);
  console.log(`Impressions:  ${totalImpressions.toLocaleString()}`);
  console.log(`Clicks:       ${totalClicks.toLocaleString()}`);
  console.log(`Conversions:  ${totalConversions}`);
  console.log(`Avg CPA:      $${avgCpa.toFixed(2)} (target: $${config.targetCpa})`);
  console.log(`Avg CTR:      ${avgCtr.toFixed(2)}%`);
  console.log(`Status:       ${onTrack ? "✅ ON TRACK" : "⚠️ OVER TARGET"}`);

  console.log("\n═══════════════════════════════════════════════════════");
  console.log("🏆 TOP WINNERS (CPA <= 1.2x target)");
  console.log("═══════════════════════════════════════════════════════");
  if (winners.length === 0) {
    console.log("No winners found");
  } else {
    winners.slice(0, 5).forEach((w, i) => {
      console.log(`${i + 1}. ${w.name}`);
      console.log(`   CPA: $${w.cpa.toFixed(2)} | Spend: $${w.spend.toFixed(2)} | Conv: ${w.conversions}`);
    });
  }

  console.log("\n═══════════════════════════════════════════════════════");
  console.log("🩸 BLEEDERS (CPA > 2.5x target)");
  console.log("═══════════════════════════════════════════════════════");
  if (bleeders.length === 0) {
    console.log("No bleeders found ✅");
  } else {
    bleeders.slice(0, 5).forEach((b, i) => {
      console.log(`${i + 1}. ${b.name}`);
      console.log(`   CPA: $${b.cpa.toFixed(2)} | Spend: $${b.spend.toFixed(2)} | Conv: ${b.conversions}`);
    });
  }

  console.log("\n═══════════════════════════════════════════════════════");
  console.log("😴 FATIGUE ALERT (Frequency > 3.5)");
  console.log("═══════════════════════════════════════════════════════");
  if (fatigue.length === 0) {
    console.log("No fatigue detected ✅");
  } else {
    fatigue.slice(0, 5).forEach((f, i) => {
      console.log(`${i + 1}. ${f.name}`);
      console.log(`   Frequency: ${f.frequency.toFixed(2)}`);
    });
  }

  console.log("\n═══════════════════════════════════════════════════════");

  return report;
}

// Run
const args = process.argv.slice(2);
const jsonOutput = args.includes("--json");

runHealthCheck()
  .then((report) => {
    if (jsonOutput) {
      console.log(JSON.stringify(report, null, 2));
    }
  })
  .catch((error) => {
    console.error("❌ Error:", error.message);
    process.exit(1);
  });
