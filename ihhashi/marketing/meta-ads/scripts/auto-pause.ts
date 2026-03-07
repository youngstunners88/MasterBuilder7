#!/usr/bin/env bun
/**
 * Auto-Pause Bleeders
 * 
 * Automatically pauses campaigns/adsets that are bleeding money:
 * - CPA > 2.5x target for 48+ hours
 * - Zero conversions after significant spend
 * 
 * Usage:
 *   bun auto-pause.ts           # Preview only (dry run)
 *   bun auto-pause.ts --execute # Actually pause
 */

const META_API_VERSION = "v21.0";
const META_BASE_URL = `https://graph.facebook.com/${META_API_VERSION}`;

function getConfig() {
  return {
    adAccountId: process.env.META_AD_ACCOUNT_ID || "",
    accessToken: process.env.META_ACCESS_TOKEN || "",
    targetCpa: parseFloat(process.env.META_TARGET_CPA || "5.00"),
  };
}

async function metaApi(
  endpoint: string,
  method: string = "GET",
  params: Record<string, string> = {},
  accessToken: string
) {
  const url = new URL(`${META_BASE_URL}${endpoint}`);
  
  if (method === "GET") {
    Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
    url.searchParams.set("access_token", accessToken);
    const response = await fetch(url.toString());
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Meta API error: ${response.status} - ${error}`);
    }
    return response.json();
  } else {
    url.searchParams.set("access_token", accessToken);
    const body = new URLSearchParams(params);
    const response = await fetch(url.toString(), {
      method,
      body,
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Meta API error: ${response.status} - ${error}`);
    }
    return response.json();
  }
}

interface Bleeder {
  id: string;
  name: string;
  level: "campaign" | "adset" | "ad";
  cpa: number;
  spend: number;
  conversions: number;
  reason: string;
}

async function findBleeders(): Promise<Bleeder[]> {
  const config = getConfig();
  console.log("🔍 Scanning for bleeding campaigns...\n");

  const bleeders: Bleeder[] = [];
  const cpaThreshold = config.targetCpa * 2.5;

  // Check campaigns
  const campaignData = await metaApi(
    `/${config.adAccountId}/insights`,
    "GET",
    {
      level: "campaign",
      date_preset: "last_2d",
      fields: "campaign_id,campaign_name,spend,actions,cost_per_action_type",
      filtering: '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
      limit: "100",
    },
    config.accessToken
  );

  for (const insight of (campaignData as any).data || []) {
    const spend = parseFloat(insight.spend);
    const conversions = insight.actions?.find(
      (a: any) => a.action_type === "purchase" || a.action_type === "omni_purchase"
    );
    const convCount = conversions ? parseInt(conversions.value) : 0;
    const cpa = convCount > 0 ? spend / convCount : Infinity;

    if (spend >= 20 && cpa > cpaThreshold) {
      bleeders.push({
        id: insight.campaign_id,
        name: insight.campaign_name || "Unknown",
        level: "campaign",
        cpa,
        spend,
        conversions: convCount,
        reason: convCount === 0 
          ? `Zero conversions after $${spend.toFixed(0)} spend`
          : `CPA $${cpa.toFixed(2)} > 2.5x target ($${cpaThreshold.toFixed(2)})`,
      });
    }
  }

  return bleeders;
}

async function pauseEntity(id: string, level: string, accessToken: string): Promise<boolean> {
  try {
    await metaApi(`/${id}`, "POST", { status: "PAUSED" }, accessToken);
    return true;
  } catch (error) {
    console.error(`Failed to pause ${level} ${id}:`, error);
    return false;
  }
}

async function run(dryRun: boolean = true) {
  const config = getConfig();
  const bleeders = await findBleeders();

  if (bleeders.length === 0) {
    console.log("✅ No bleeders found - all campaigns healthy!\n");
    return;
  }

  console.log("═══════════════════════════════════════════════════════");
  console.log("🩸 BLEEDERS DETECTED");
  console.log("═══════════════════════════════════════════════════════\n");

  bleeders.forEach((b, i) => {
    console.log(`${i + 1}. [${b.level.toUpperCase()}] ${b.name}`);
    console.log(`   CPA: $${b.cpa.toFixed(2)} | Spend: $${b.spend.toFixed(2)} | Conv: ${b.conversions}`);
    console.log(`   Reason: ${b.reason}\n`);
  });

  const totalWasted = bleeders.reduce((sum, b) => sum + b.spend, 0);
  console.log(`Total at risk: $${totalWasted.toFixed(2)}\n`);

  if (dryRun) {
    console.log("═══════════════════════════════════════════════════════");
    console.log("⚠️ DRY RUN MODE - No changes made");
    console.log("Run with --execute to actually pause these\n");
    return;
  }

  console.log("═══════════════════════════════════════════════════════");
  console.log("⏸️ PAUSING BLEEDERS...\n");

  let paused = 0;
  for (const b of bleeders) {
    const success = await pauseEntity(b.id, b.level, config.accessToken);
    if (success) {
      console.log(`✅ Paused: ${b.name}`);
      paused++;
    } else {
      console.log(`❌ Failed: ${b.name}`);
    }
  }

  console.log(`\n✅ Paused ${paused}/${bleeders.length} bleeders`);
  console.log("═══════════════════════════════════════════════════════\n");
}

// Run
const args = process.argv.slice(2);
const execute = args.includes("--execute");

run(!execute).catch((error) => {
  console.error("❌ Error:", error.message);
  process.exit(1);
});
