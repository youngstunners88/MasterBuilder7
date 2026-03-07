#!/usr/bin/env bun
/**
 * Ad Copy Generator
 * 
 * Analyzes top performing ads and generates new copy variations:
 * - Extracts winning hooks, angles, CTAs
 * - Generates variations based on YOUR top performers
 * - Models copy on what already converts
 * 
 * Usage:
 *   bun copy-generator.ts
 *   bun copy-generator.ts --count 5
 *   bun copy-generator.ts --campaign "Campaign Name"
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

async function metaApi(endpoint: string, params: Record<string, string>, accessToken: string) {
  const url = new URL(`${META_BASE_URL}${endpoint}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
  url.searchParams.set("access_token", accessToken);
  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Meta API error: ${response.status}`);
  return response.json();
}

interface TopAd {
  id: string;
  name: string;
  body: string;
  headline: string;
  linkDescription: string;
  callToAction: string;
  cpa: number;
  ctr: number;
  conversions: number;
}

interface GeneratedCopy {
  hook: string;
  body: string;
  headline: string;
  cta: string;
  basedOn: string;
}

async function getTopPerformingAds(limit: number = 5): Promise<TopAd[]> {
  const config = getConfig();
  console.log("🔍 Finding top performing ads...\n");

  // Get ad-level insights
  const insightsData = await metaApi(
    `/${config.adAccountId}/insights`,
    {
      level: "ad",
      date_preset: "last_14d",
      fields: "ad_id,ad_name,spend,actions,ctr,cost_per_action_type",
      limit: "50",
    },
    config.accessToken
  );

  const insights = (insightsData as any).data || [];
  
  // Sort by conversions and CPA
  const withConversions = insights.map((i: any) => {
    const conversions = i.actions?.find(
      (a: any) => a.action_type === "purchase" || a.action_type === "omni_purchase"
    );
    return {
      ad_id: i.ad_id,
      spend: parseFloat(i.spend || 0),
      ctr: parseFloat(i.ctr || 0),
      conversions: conversions ? parseInt(conversions.value) : 0,
      cpa: conversions ? parseFloat(i.spend) / parseInt(conversions.value) : Infinity,
    };
  });

  // Filter to ads with conversions and sort by CPA
  const topAds = withConversions
    .filter((a: any) => a.conversions > 0)
    .sort((a: any, b: any) => a.cpa - b.cpa)
    .slice(0, limit);

  // Get creative details for each
  const ads: TopAd[] = [];
  for (const ad of topAds) {
    try {
      const creativeData = await metaApi(
        `/${ad.ad_id}`,
        {
          fields: "creative{id,body,link_deep_link_url,call_to_action_type,name}",
        },
        config.accessToken
      );

      const creative = (creativeData as any).creative || {};
      
      ads.push({
        id: ad.ad_id,
        name: (creativeData as any).name || "Unknown",
        body: creative.body || "",
        headline: creative.name || "",
        linkDescription: "",
        callToAction: creative.call_to_action_type || "LEARN_MORE",
        cpa: ad.cpa,
        ctr: ad.ctr,
        conversions: ad.conversions,
      });
    } catch (error) {
      // Skip if can't get creative
    }
  }

  return ads;
}

function analyzePatterns(ads: TopAd[]): {
  hooks: string[];
  angles: string[];
  ctas: string[];
} {
  const hooks: string[] = [];
  const angles: string[] = [];
  const ctas: string[] = [];

  for (const ad of ads) {
    if (ad.body) {
      // Extract first sentence as potential hook
      const sentences = ad.body.split(/[.!?]+/).filter((s) => s.trim());
      if (sentences.length > 0) {
        hooks.push(sentences[0].trim());
      }
      
      // Store full body as angle
      angles.push(ad.body);
    }
    
    if (ad.callToAction) {
      ctas.push(ad.callToAction);
    }
  }

  return { hooks, angles, ctas };
}

function generateVariations(
  patterns: { hooks: string[]; angles: string[]; ctas: string[] },
  topAds: TopAd[],
  count: number = 3
): GeneratedCopy[] {
  const variations: GeneratedCopy[] = [];

  // Template patterns for variation
  const hookTemplates = [
    "Tired of {problem}?",
    "What if {benefit}?",
    "Discover the secret to {benefit}",
    "Stop wasting time on {problem}",
    "Here's how to {benefit}",
    "The {audience} hack you've been waiting for",
  ];

  const bodyTemplates = [
    "After trying everything, I finally found {solution}. {detail} No more {problem}.",
    "Most people don't know this, but {insight}. That's why {solution} works so well.",
    "I was skeptical at first. But {result} changed my mind completely.",
    "Here's what nobody tells you about {topic}: {insight}.",
  ];

  // Generate variations based on top performers
  for (let i = 0; i < count; i++) {
    const baseAd = topAds[i % topAds.length];
    const hookIdx = i % hookTemplates.length;
    const bodyIdx = i % bodyTemplates.length;

    variations.push({
      hook: patterns.hooks[i % patterns.hooks.length] || hookTemplates[hookIdx].replace("{benefit}", "getting results"),
      body: patterns.angles[i % patterns.angles.length] || bodyTemplates[bodyIdx].replace("{solution}", "this approach"),
      headline: `Variation ${i + 1} - Based on ${baseAd.name}`,
      cta: patterns.ctas[i % patterns.ctas.length] || "LEARN_MORE",
      basedOn: baseAd.name,
    });
  }

  return variations;
}

async function run(count: number = 3) {
  const topAds = await getTopPerformingAds();

  if (topAds.length === 0) {
    console.log("No ads with conversions found. Run some ads first!\n");
    return;
  }

  console.log("═══════════════════════════════════════════════════════");
  console.log("🏆 TOP PERFORMING ADS");
  console.log("═══════════════════════════════════════════════════════\n");

  topAds.forEach((ad, i) => {
    console.log(`${i + 1}. ${ad.name}`);
    console.log(`   CPA: $${ad.cpa.toFixed(2)} | CTR: ${ad.ctr.toFixed(2)}% | Conv: ${ad.conversions}`);
    if (ad.body) {
      console.log(`   Body: "${ad.body.substring(0, 100)}${ad.body.length > 100 ? "..." : ""}"`);
    }
    console.log();
  });

  // Analyze patterns
  const patterns = analyzePatterns(topAds);
  const variations = generateVariations(patterns, topAds, count);

  console.log("═══════════════════════════════════════════════════════");
  console.log("✨ GENERATED COPY VARIATIONS");
  console.log("═══════════════════════════════════════════════════════\n");

  variations.forEach((v, i) => {
    console.log(`--- Variation ${i + 1} (Based on: ${v.basedOn}) ---`);
    console.log(`HOOK: ${v.hook}`);
    console.log(`BODY: ${v.body}`);
    console.log(`HEADLINE: ${v.headline}`);
    console.log(`CTA: ${v.cta}\n`);
  });

  console.log("═══════════════════════════════════════════════════════");
  console.log("💡 TIP: Review these variations and customize before uploading.");
  console.log("═══════════════════════════════════════════════════════\n");
}

// Run
const args = process.argv.slice(2);
const countIndex = args.indexOf("--count");
const count = countIndex >= 0 ? parseInt(args[countIndex + 1]) : 3;

run(count).catch((error) => {
  console.error("❌ Error:", error.message);
  process.exit(1);
});
