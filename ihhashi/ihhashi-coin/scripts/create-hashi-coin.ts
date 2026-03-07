/**
 * iHhashi Coin - Zora Coins Protocol Integration
 * 
 * Creates iHhashi Coin on Zora with referral rewards integration.
 * 
 * REFERRAL REWARDS (Zora V4 - 1% total fee):
 * - Platform Referrer (iHhashi): 20% of total fees FOREVER
 * - Trade Referrer (user who referred): 4% per trade
 * - Creator: 50% of total fees
 * - Protocol: 5%
 * - Doppler: 1%
 * - LP Rewards: 20%
 * 
 * Usage:
 *   bun scripts/create-hashi-coin.ts --private-key <KEY>
 *   bun scripts/create-hashi-coin.ts --help
 */

import {
  createCoin,
  createCoinCall,
  CreateConstants,
  createMetadataBuilder,
  createZoraUploaderForCreator,
  setApiKey,
} from "@zoralabs/coins-sdk";
import {
  createWalletClient,
  createPublicClient,
  http,
  Address,
  Hex,
} from "viem";
import { base } from "viem/chains";

// ============================================================================
// CONFIGURATION
// ============================================================================

const HASHI_COIN_CONFIG = {
  name: "iHhashi Coin",
  symbol: "HASHI",
  description: "iHhashi Food Delivery Rewards - Tradeable loyalty tokens for South Africa's favourite delivery platform. Earn through referrals, redeem for discounts and free delivery.",
  
  // iHhashi treasury - receives 20% of ALL trading fees forever
  platformReferrer: (process.env.IHHASHI_TREASURY || "0x0000000000000000000000000000000000000000") as Address,
  
  // Creator wallet - receives 50% of trading fees
  creator: (process.env.IHHASHI_CREATOR || "0x0000000000000000000000000000000000000000") as Address,
  
  // Zora API key (get from https://zora.co/settings/developer)
  zoraApiKey: process.env.ZORA_API_KEY || "",
  
  // Base RPC URL
  rpcUrl: process.env.BASE_RPC_URL || "https://mainnet.base.org",
  
  // Chain ID (Base mainnet)
  chainId: 8453,
};

// ============================================================================
// METADATA
// ============================================================================

interface HashiCoinMetadata {
  name: string;
  description: string;
  image: string;
  external_url: string;
  properties: {
    category: string;
    platform: string;
    rewards: {
      referral_bonus: string;
      redemption_options: string[];
    };
  };
}

const HASHI_COIN_METADATA: HashiCoinMetadata = {
  name: "iHhashi Coin",
  description: "iHhashi Food Delivery Rewards - Tradeable loyalty tokens for South Africa's favourite delivery platform. Earn through referrals, redeem for discounts and free delivery.",
  image: "ipfs://bafybeihashi-coin-logo", // Will be uploaded
  external_url: "https://ihhashi.com",
  properties: {
    category: "Loyalty Token",
    platform: "iHhashi",
    rewards: {
      referral_bonus: "50 iHhashi Coins per referral",
      redemption_options: [
        "100 coins = Free delivery",
        "150 coins = R15 discount",
        "300 coins = R30 discount"
      ]
    }
  }
};

// ============================================================================
// CREATE HASHI COIN
// ============================================================================

async function createHashiCoin(privateKey: Hex) {
  console.log("🚀 Creating iHhashi Coin on Zora...\n");
  
  // Set API key if available
  if (HASHI_COIN_CONFIG.zoraApiKey) {
    setApiKey(HASHI_COIN_CONFIG.zoraApiKey);
  }
  
  // Setup clients
  const publicClient = createPublicClient({
    chain: base,
    transport: http(HASHI_COIN_CONFIG.rpcUrl),
  });
  
  const walletClient = createWalletClient({
    account: privateKey,
    chain: base,
    transport: http(HASHI_COIN_CONFIG.rpcUrl),
  });
  
  const creatorAddress = walletClient.account!.address;
  console.log(`📝 Creator address: ${creatorAddress}`);
  console.log(`💰 Platform referrer (iHhashi): ${HASHI_COIN_CONFIG.platformReferrer}`);
  console.log(`🔗 Chain: Base Mainnet (${HASHI_COIN_CONFIG.chainId})\n`);
  
  // Build metadata
  console.log("📦 Building metadata...");
  const { createMetadataParameters } = await createMetadataBuilder()
    .withName(HASHI_COIN_CONFIG.name)
    .withSymbol(HASHI_COIN_CONFIG.symbol)
    .withDescription(HASHI_COIN_CONFIG.description)
    // Note: In production, upload actual image file
    .upload(createZoraUploaderForCreator(creatorAddress));
  
  // Create coin args
  const args = {
    creator: creatorAddress,
    name: HASHI_COIN_CONFIG.name,
    symbol: HASHI_COIN_CONFIG.symbol,
    metadata: createMetadataParameters,
    
    // Pair with ZORA token for liquidity
    currency: CreateConstants.ContentCoinCurrencies.ZORA,
    
    // Base mainnet
    chainId: HASHI_COIN_CONFIG.chainId,
    
    // LOW starting market cap (suitable for new tokens)
    startingMarketCap: CreateConstants.StartingMarketCaps.LOW,
    
    // iHhashi receives 20% of ALL trading fees FOREVER
    platformReferrerAddress: HASHI_COIN_CONFIG.platformReferrer,
    
    // Payout recipient (can be updated later)
    payoutRecipientOverride: HASHI_COIN_CONFIG.creator || creatorAddress,
  };
  
  console.log("⏳ Submitting transaction...\n");
  
  try {
    const result = await createCoin({
      call: args,
      walletClient,
      publicClient,
    });
    
    console.log("✅ iHhashi Coin created successfully!\n");
    console.log("=" .repeat(60));
    console.log("HASHI COIN DEPLOYMENT");
    console.log("=" .repeat(60));
    console.log(`📍 Coin Address: ${result.address}`);
    console.log(`🔗 Transaction: ${result.hash}`);
    console.log(`📊 Pool Address: ${result.deployment?.poolAddress || 'N/A'}`);
    console.log(`🌐 View on Zora: https://zora.co/collect/base:${result.address}`);
    console.log("=" .repeat(60));
    console.log("\n💰 REFERRAL REWARDS STRUCTURE:");
    console.log(`   Platform Referrer (iHhashi): 20% of fees FOREVER`);
    console.log(`   Trade Referrers: 4% per trade`);
    console.log(`   Creator: 50% of fees`);
    console.log("=" .repeat(60));
    
    return result;
  } catch (error: any) {
    console.error("❌ Failed to create iHhashi Coin:", error.message);
    throw error;
  }
}

// ============================================================================
// GET CREATE CALL (for WAGMI/frontend integration)
// ============================================================================

async function getHashiCoinCreateCall(creatorAddress: Address) {
  console.log("🔨 Building iHhashi Coin create call...\n");
  
  // Set API key if available
  if (HASHI_COIN_CONFIG.zoraApiKey) {
    setApiKey(HASHI_COIN_CONFIG.zoraApiKey);
  }
  
  // Build metadata
  const { createMetadataParameters } = await createMetadataBuilder()
    .withName(HASHI_COIN_CONFIG.name)
    .withSymbol(HASHI_COIN_CONFIG.symbol)
    .withDescription(HASHI_COIN_CONFIG.description)
    .upload(createZoraUploaderForCreator(creatorAddress));
  
  const args = {
    creator: creatorAddress,
    name: HASHI_COIN_CONFIG.name,
    symbol: HASHI_COIN_CONFIG.symbol,
    metadata: createMetadataParameters,
    currency: CreateConstants.ContentCoinCurrencies.ZORA,
    chainId: HASHI_COIN_CONFIG.chainId,
    startingMarketCap: CreateConstants.StartingMarketCaps.LOW,
    platformReferrerAddress: HASHI_COIN_CONFIG.platformReferrer,
  };
  
  const { calls, predictedCoinAddress } = await createCoinCall(args);
  
  console.log(`📍 Predicted coin address: ${predictedCoinAddress}`);
  console.log(`📝 Calls to execute: ${calls.length}`);
  
  return { calls, predictedCoinAddress, args };
}

// ============================================================================
// CLI
// ============================================================================

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
iHhashi Coin - Zora Coins Protocol Integration

USAGE:
  bun scripts/create-hashi-coin.ts [OPTIONS]

OPTIONS:
  --private-key <KEY>    Private key to sign transaction (required for creation)
  --get-call             Get create call data (for frontend/WAGMI integration)
  --creator <ADDRESS>    Creator address (for --get-call mode)
  --help, -h             Show this help message

ENVIRONMENT VARIABLES:
  ZORA_API_KEY          Zora API key (get from https://zora.co/settings/developer)
  IHHASHI_TREASURY      iHhashi treasury address (receives 20% platform referral fees)
  IHHASHI_CREATOR       Creator payout address (receives 50% creator fees)
  BASE_RPC_URL          Base RPC URL (default: https://mainnet.base.org)

EXAMPLES:
  # Create iHhashi Coin
  bun scripts/create-hashi-coin.ts --private-key 0x...

  # Get create call for frontend
  bun scripts/create-hashi-coin.ts --get-call --creator 0x...

REFERRAL REWARDS (Zora V4):
  - Platform Referrer: 20% of total fees FOREVER
  - Trade Referrer: 4% per trade
  - Creator: 50% of total fees
`);
    process.exit(0);
  }
  
  if (args.includes("--get-call")) {
    const creatorIndex = args.indexOf("--creator");
    if (creatorIndex === -1) {
      console.error("❌ --creator address required for --get-call mode");
      process.exit(1);
    }
    const creatorAddress = args[creatorIndex + 1] as Address;
    await getHashiCoinCreateCall(creatorAddress);
    return;
  }
  
  const privateKeyIndex = args.indexOf("--private-key");
  if (privateKeyIndex === -1) {
    console.error("❌ --private-key required for coin creation");
    console.error("Run with --help for usage information");
    process.exit(1);
  }
  
  const privateKey = args[privateKeyIndex + 1] as Hex;
  await createHashiCoin(privateKey);
}

main().catch(console.error);
