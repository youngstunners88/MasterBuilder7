#!/usr/bin/env bun
/**
 * Ad Fatigue Detector
 * 
 * Detects ads with high frequency (> 3.5) indicating audience fatigue
 * Frequency > 3.5 = audience is cooked, CTR about to drop
 * 
 * Usage:
 *   bun fatigue-detector.ts
 *   bun fatigue-detector.ts --threshold 4.0
 */

const META_API_VERSION = "v21.0";
const META_BASE_URL = `https://graph.facebook.com/${META_API_VERSION}`;

function getConfig() {
  const config = {
    adAccountId: process.env.META_AD_ACCOUNT_ID || "",
    accessToken: process.env.META_ACCESS_TOKEN || "",
  };

  if (!config.accessToken || !config.adAccountId) {
    console.error("❌ Missing Meta API credentials");
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

interface AdInsight {
  ad_id: string;
  ad_name?: string;
  campaign_name?: string;
  adset_name?: string;
  frequency: string;
  impressions: string;
  reach: string;
  spend: string;
  ctr: string;
  cpc: string;
}

interface FatigueAlert {
  adId: string;
  adName: string;
  campaignName: string;
  adsetName: string;
  frequency: number;
  impressions: number;
  reach: number;
  spend: number;
  ctr: number;
  severity: "warning" | "critical" | "severe";
}

async function detectFatigue(threshold: number = 3.5): Promise<FatigueAlert[]> {
  const config = getConfig();
  console.log(`🔍 Detecting ad fatigue (threshold: ${threshold})...\n`);

  // Get ad-level insights with frequency
  const data = await metaApi(
    `/${config.adAccountId}/insights`,
    {
      level: "ad",
      date_preset: "last_7d",
      fields: "ad_id,ad_name,campaign_name,adset_name,frequency,impressions,reach,spend,ctr,cpc",
      filtering: '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
      limit: "100",
    },
    config.accessToken
  );

  const insights = (data as any).data || [];
  const alerts: FatigueAlert[] = [];

  for (const insight of insights as AdInsight[]) {
    const frequency = parseFloat(insight.frequency || "0");
    
    if (frequency >= threshold) {
      const severity = frequency >= 5 ? "severe" : frequency >= 4 ? "critical" : "warning";
      
      alerts.push({
        adId: insight.ad_id,
        adName: insight.ad_name || "Unknown",
        campaignName: insight.campaign_name || "Unknown",
        adsetName: insight.adset_name || "Unknown",
        frequency,
        impressions: parseInt(insight.impressions),
        reach: parseInt(insight.reach),
        spend: parseFloat(insight.spend),
        ctr: parseFloat(insight.ctr) || 0,
        severity,
      });
    }
  }

  // Sort by frequency (highest first)
  alerts.sort((a, b) => b.frequency - a.frequency);

  return alerts;
}

function printAlerts(alerts: FatigueAlert[]) {
  if (alerts.length === 0) {
    console.log("✅ No fatigue detected - all ads healthy!\n");
    return;
  }

  console.log("═══════════════════════════════════════════════════════");
  console.log("😴 FATIGUE DETECTED");
  console.log("═══════════════════════════════════════════════════════\n");

  const severe = alerts.filter((a) => a.severity === "severe");
  const critical = alerts.filter((a) => a.severity === "critical");
  const warning = alerts.filter((a) => a.severity === "warning");

  if (severe.length > 0) {
    console.log("🔴 SEVERE (frequency >= 5.0) - ACTION NOW!");
    severe.forEach((a) => {
      console.log(`   ${a.adName}`);
      console.log(`   Campaign: ${a.campaignName} | AdSet: ${a.adsetName}`);
      console.log(`   Frequency: ${a.frequency.toFixed(2)} | CTR: ${a.ctr.toFixed(2)}%`);
      console.log(`   Spend: $${a.spend.toFixed(2)}\n`);
    });
  }

  if (critical.length > 0) {
    console.log("🟠 CRITICAL (frequency 4.0-5.0)");
    critical.forEach((a) => {
      console.log(`   ${a.adName}`);
      console.log(`   Campaign: ${a.campaignName} | Frequency: ${a.frequency.toFixed(2)}\n`);
    });
  }

  if (warning.length > 0) {
    console.log("🟡 WARNING (frequency 3.5-4.0)");
    warning.forEach((a) => {
      console.log(`   ${a.adName} | Frequency: ${a.frequency.toFixed(2)}`);
    });
  }

  console.log("\n═══════════════════════════════════════════════════════");
  console.log("💡 RECOMMENDATIONS");
  console.log("═══════════════════════════════════════════════════════");
  console.log("1. Refresh creative for ads with frequency > 4.0");
  console.log("2. Expand or duplicate audience for frequency > 5.0");
  console.log("3. Consider new hooks/angles for fatigued ads");
  console.log("═══════════════════════════════════════════════════════\n");
}

// Run
const args = process.argv.slice(2);
const thresholdIndex = args.indexOf("--threshold");
const threshold = thresholdIndex >= 0 ? parseFloat(args[thresholdIndex + 1]) : 3.5;

detectFatigue(threshold)
  .then(printAlerts)
  .catch((error) => {
    console.error("❌ Error:", error.message);
    process.exit(1);
  });
