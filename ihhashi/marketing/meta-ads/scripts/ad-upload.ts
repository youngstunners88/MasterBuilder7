#!/usr/bin/env bun
/**
 * Ad Upload
 * 
 * Uploads new ads directly to Meta Ads Manager:
 * - Creates ad creative
 * - Creates ad
 * - No manual download/upload needed
 * 
 * Usage:
 *   bun ad-upload.ts --creative '{"name":"New Ad","body":"..."}'
 *   bun ad-upload.ts --file ./new-ad.json
 */

const META_API_VERSION = "v21.0";
const META_BASE_URL = `https://graph.facebook.com/${META_API_VERSION}`;

function getConfig() {
  return {
    adAccountId: process.env.META_AD_ACCOUNT_ID || "",
    accessToken: process.env.META_ACCESS_TOKEN || "",
    pageId: process.env.META_PAGE_ID || "",
    instagramAccountId: process.env.META_INSTAGRAM_ACCOUNT_ID || "",
  };
}

async function metaApi(
  endpoint: string,
  method: string = "POST",
  body: Record<string, any> = {},
  accessToken: string
) {
  const url = new URL(`${META_BASE_URL}${endpoint}`);
  url.searchParams.set("access_token", accessToken);

  const response = await fetch(url.toString(), {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(`Meta API error: ${JSON.stringify(data)}`);
  }

  return data;
}

interface AdCreative {
  name: string;
  body?: string;
  headline?: string;
  linkDescription?: string;
  callToAction?: string;
  destinationUrl?: string;
  imageUrl?: string;
  videoId?: string;
  pageId?: string;
  instagramAccountId?: string;
}

interface AdSpec {
  campaignId: string;
  adsetId: string;
  creative: AdCreative;
  status?: "ACTIVE" | "PAUSED";
}

async function createAdCreative(creative: AdCreative, config: ReturnType<typeof getConfig>): Promise<string> {
  console.log(`🎨 Creating ad creative: ${creative.name}...`);

  const creativeSpec: Record<string, any> = {
    name: creative.name,
    object_story_spec: {
      page_id: creative.pageId || config.pageId,
      link_data: {
        message: creative.body || "",
        link: creative.destinationUrl || "",
        name: creative.headline || "",
        description: creative.linkDescription || "",
        call_to_action: {
          type: creative.callToAction || "LEARN_MORE",
        },
      },
    },
  };

  // Add Instagram if configured
  if (creative.instagramAccountId || config.instagramAccountId) {
    creativeSpec.object_story_spec.instagram_actor_id = 
      creative.instagramAccountId || config.instagramAccountId;
  }

  // Add image if provided
  if (creative.imageUrl) {
    creativeSpec.object_story_spec.link_data.image_hash = creative.imageUrl;
  }

  const result = await metaApi(
    `/${config.adAccountId}/adcreatives`,
    "POST",
    creativeSpec,
    config.accessToken
  );

  console.log(`✅ Creative created: ${(result as any).id}\n`);
  return (result as any).id;
}

async function createAd(
  adsetId: string,
  creativeId: string,
  name: string,
  status: string,
  config: ReturnType<typeof getConfig>
): Promise<string> {
  console.log(`📢 Creating ad: ${name}...`);

  const result = await metaApi(
    `/${config.adAccountId}/ads`,
    "POST",
    {
      name,
      adset_id: adsetId,
      creative: { creative_id: creativeId },
      status: status || "PAUSED",
    },
    config.accessToken
  );

  console.log(`✅ Ad created: ${(result as any).id}\n`);
  return (result as any).id;
}

async function uploadAd(spec: AdSpec): Promise<{ creativeId: string; adId: string }> {
  const config = getConfig();

  if (!config.adAccountId || !config.accessToken) {
    throw new Error("Missing Meta API credentials. Set META_AD_ACCOUNT_ID and META_ACCESS_TOKEN.");
  }

  console.log("═══════════════════════════════════════════════════════");
  console.log("📤 UPLOADING AD TO META");
  console.log("═══════════════════════════════════════════════════════\n");

  // Create creative
  const creativeId = await createAdCreative(spec.creative, config);

  // Create ad
  const adId = await createAd(
    spec.adsetId,
    creativeId,
    spec.creative.name,
    spec.status || "PAUSED",
    config
  );

  console.log("═══════════════════════════════════════════════════════");
  console.log("✅ UPLOAD COMPLETE");
  console.log("═══════════════════════════════════════════════════════\n");
  console.log(`Creative ID: ${creativeId}`);
  console.log(`Ad ID: ${adId}`);
  console.log(`Status: ${spec.status || "PAUSED"}`);
  console.log(`\nView in Ads Manager: https://adsmanager.facebook.com/ads_manager/manage_campaigns\n`);

  return { creativeId, adId };
}

// CLI handling
async function run() {
  const args = process.argv.slice(2);

  // Example usage
  if (args.length === 0) {
    console.log("Usage:");
    console.log("  bun ad-upload.ts --file ./ad-spec.json");
    console.log("  bun ad-upload.ts --adset 123456789 --name 'New Ad' --body 'Ad copy here'\n");
    
    console.log("Example ad-spec.json:");
    console.log(JSON.stringify({
      campaignId: "act_123_campaign_456",
      adsetId: "123456789",
      creative: {
        name: "Test Ad",
        body: "This is the ad body text",
        headline: "Click Here!",
        callToAction: "LEARN_MORE",
        destinationUrl: "https://example.com",
      },
      status: "PAUSED",
    }, null, 2));
    return;
  }

  // Parse --file argument
  const fileIndex = args.indexOf("--file");
  if (fileIndex >= 0) {
    const filePath = args[fileIndex + 1];
    const { default: spec } = await import(filePath, { assert: { type: "json" } });
    await uploadAd(spec);
    return;
  }

  // Parse individual arguments
  const adsetIndex = args.indexOf("--adset");
  const nameIndex = args.indexOf("--name");
  const bodyIndex = args.indexOf("--body");

  if (adsetIndex >= 0 && nameIndex >= 0) {
    const spec: AdSpec = {
      campaignId: "",
      adsetId: args[adsetIndex + 1],
      creative: {
        name: args[nameIndex + 1],
        body: bodyIndex >= 0 ? args[bodyIndex + 1] : "",
      },
      status: "PAUSED",
    };
    await uploadAd(spec);
  }
}

run().catch((error) => {
  console.error("❌ Error:", error.message);
  process.exit(1);
});
