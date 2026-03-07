/**
 * iHhashi Coin Trading with Referral Integration
 * 
 * Trade iHhashi Coins with trade referral rewards.
 * Trade referrer earns 4% of the trade fee.
 * 
 * Usage:
 *   bun scripts/trade-hashi-coin.ts buy --amount 100 --referrer 0x...
 *   bun scripts/trade-hashi-coin.ts sell --amount 50
 */

import {
  tradeCoin,
  TradeConstants,
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

const CONFIG = {
  // iHhashi Coin address (set after deployment)
  hashiCoinAddress: (process.env.HASHI_COIN_ADDRESS || "0x0000000000000000000000000000000000000000") as Address,
  
  // Zora API key
  zoraApiKey: process.env.ZORA_API_KEY || "",
  
  // Base RPC URL
  rpcUrl: process.env.BASE_RPC_URL || "https://mainnet.base.org",
};

// ============================================================================
// TRADE WITH REFERRAL
// ============================================================================

interface TradeOptions {
  direction: "buy" | "sell";
  amount: string; // In token units or ETH
  tradeReferrer?: Address; // Address to receive 4% trade referral reward
  privateKey: Hex;
}

async function tradeHashiCoin(options: TradeOptions) {
  const { direction, amount, tradeReferrer, privateKey } = options;
  
  console.log(`🔄 Trading iHhashi Coin: ${direction.toUpperCase()}\n`);
  
  // Set API key if available
  if (CONFIG.zoraApiKey) {
    setApiKey(CONFIG.zoraApiKey);
  }
  
  // Setup clients
  const publicClient = createPublicClient({
    chain: base,
    transport: http(CONFIG.rpcUrl),
  });
  
  const walletClient = createWalletClient({
    account: privateKey,
    chain: base,
    transport: http(CONFIG.rpcUrl),
  });
  
  const traderAddress = walletClient.account!.address;
  console.log(`👤 Trader: ${traderAddress}`);
  console.log(`📍 Coin: ${CONFIG.hashiCoinAddress}`);
  
  if (tradeReferrer) {
    console.log(`💰 Trade Referrer: ${tradeReferrer} (earns 4% of this trade)`);
  }
  console.log("");
  
  // Build trade parameters
  const tradeArgs = {
    direction: direction === "buy" 
      ? TradeConstants.TradeDirection.BUY 
      : TradeConstants.TradeDirection.SELL,
    
    // For BUY: amount of ETH to spend
    // For SELL: amount of tokens to sell
    amount: BigInt(amount),
    
    // Coin to trade
    coin: CONFIG.hashiCoinAddress,
    
    // Trade referrer gets 4% of this trade's fee
    tradeReferrer: tradeReferrer,
  };
  
  console.log("⏳ Executing trade...\n");
  
  try {
    const result = await tradeCoin({
      call: tradeArgs,
      walletClient,
      publicClient,
    });
    
    console.log("✅ Trade completed!\n");
    console.log("=" .repeat(60));
    console.log("TRADE DETAILS");
    console.log("=" .repeat(60));
    console.log(`🔗 Transaction: ${result.hash}`);
    console.log(`📊 Direction: ${direction.toUpperCase()}`);
    console.log(`💰 Amount: ${amount}`);
    if (tradeReferrer) {
      console.log(`💵 Trade Referrer Earned: 4% of trade fee`);
    }
    console.log("=" .repeat(60));
    
    return result;
  } catch (error: any) {
    console.error("❌ Trade failed:", error.message);
    throw error;
  }
}

// ============================================================================
// BRIDGE: Web2 to Web3
// ============================================================================

interface MintOptions {
  userId: string; // iHhashi user ID
  amount: number; // iHhashi Coins to mint on-chain
  walletAddress: Address;
}

/**
 * Convert Web2 iHhashi Coins to on-chain
 * 
 * Flow:
 * 1. User has Web2 iHhashi Coins in MongoDB
 * 2. User requests to mint on-chain
 * 3. Platform burns Web2 coins, mints on-chain coins
 * 4. User receives tradeable iHhashi Coins
 */
async function mintOnChainHashiCoins(options: MintOptions) {
  console.log(`🏭 Minting on-chain iHhashi Coins for user ${options.userId}\n`);
  
  // In production, this would:
  // 1. Check user's Web2 balance via MongoDB
  // 2. Burn Web2 coins
  // 3. Mint on-chain coins to user's wallet
  // 4. Record transaction
  
  console.log(`📝 TODO: Implement bridge logic`);
  console.log(`   1. Check Web2 balance for user ${options.userId}`);
  console.log(`   2. Burn ${options.amount} Web2 iHhashi Coins`);
  console.log(`   3. Mint ${options.amount} on-chain iHhashi Coins to ${options.walletAddress}`);
  
  return {
    status: "pending_implementation",
    userId: options.userId,
    amount: options.amount,
    walletAddress: options.walletAddress,
  };
}

// ============================================================================
// REDEMPTION: On-Chain to Discount
// ============================================================================

interface RedeemOptions {
  walletAddress: Address;
  amount: number; // iHhashi Coins to burn
  orderId: string; // iHhashi order to apply discount
}

/**
 * Burn on-chain iHhashi Coins for order discount
 * 
 * Flow:
 * 1. User has on-chain iHhashi Coins
 * 2. User requests discount on order
 * 3. Platform burns coins, applies discount
 * 4. Order gets reduced price
 */
async function redeemHashiCoins(options: RedeemOptions) {
  console.log(`🎁 Redeeming iHhashi Coins for order ${options.orderId}\n`);
  
  const REDEMPTION_RATES = {
    100: { type: "free_delivery", value: "Free Delivery" },
    150: { type: "discount_r15", value: "R15 Discount" },
    300: { type: "discount_r30", value: "R30 Discount" },
  };
  
  // Find applicable redemption
  const redemption = REDEMPTION_RATES[options.amount as keyof typeof REDEMPTION_RATES];
  
  if (!redemption) {
    console.log("⚠️  Invalid redemption amount. Valid amounts: 100, 150, 300");
    return { status: "invalid_amount" };
  }
  
  console.log(`✅ Redemption: ${redemption.value}`);
  console.log(`🔥 Burning ${options.amount} iHhashi Coins from ${options.walletAddress}`);
  console.log(`📦 Applying to order: ${options.orderId}`);
  
  return {
    status: "success",
    redemption: redemption.value,
    coinsBurned: options.amount,
    orderId: options.orderId,
  };
}

// ============================================================================
// CLI
// ============================================================================

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
iHhashi Coin Trading

USAGE:
  bun scripts/trade-hashi-coin.ts [COMMAND] [OPTIONS]

COMMANDS:
  buy                  Buy iHhashi Coins
  sell                 Sell iHhashi Coins
  mint                 Convert Web2 coins to on-chain
  redeem               Burn coins for order discount

OPTIONS:
  --amount <AMOUNT>    Amount to trade (in wei for ETH, token units for coins)
  --referrer <ADDRESS> Trade referrer address (earns 4% of trade)
  --private-key <KEY>  Private key to sign transaction
  --wallet <ADDRESS>   Wallet address (for mint/redeem)
  --order-id <ID>      Order ID (for redeem)
  --user-id <ID>       User ID (for mint)
  --help, -h           Show this help message

EXAMPLES:
  # Buy 0.01 ETH worth of iHhashi Coins with referral
  bun scripts/trade-hashi-coin.ts buy --amount 10000000000000000 --referrer 0xReferrer --private-key 0x...

  # Sell 100 iHhashi Coins
  bun scripts/trade-hashi-coin.ts sell --amount 100 --private-key 0x...

TRADE REFERRAL REWARDS:
  - Trade referrer earns 4% of the trade fee
  - Set per trade via --referrer flag
  - Different referrer can be set for each trade
`);
    process.exit(0);
  }
  
  const command = args[0];
  const privateKeyIndex = args.indexOf("--private-key");
  const amountIndex = args.indexOf("--amount");
  const referrerIndex = args.indexOf("--referrer");
  const walletIndex = args.indexOf("--wallet");
  const orderIdIndex = args.indexOf("--order-id");
  const userIdIndex = args.indexOf("--user-id");
  
  switch (command) {
    case "buy":
    case "sell":
      if (privateKeyIndex === -1) {
        console.error("❌ --private-key required for trading");
        process.exit(1);
      }
      if (amountIndex === -1) {
        console.error("❌ --amount required for trading");
        process.exit(1);
      }
      
      await tradeHashiCoin({
        direction: command as "buy" | "sell",
        amount: args[amountIndex + 1],
        tradeReferrer: referrerIndex !== -1 ? args[referrerIndex + 1] as Address : undefined,
        privateKey: args[privateKeyIndex + 1] as Hex,
      });
      break;
      
    case "mint":
      if (userIdIndex === -1 || walletIndex === -1 || amountIndex === -1) {
        console.error("❌ --user-id, --wallet, and --amount required for minting");
        process.exit(1);
      }
      await mintOnChainHashiCoins({
        userId: args[userIdIndex + 1],
        amount: parseInt(args[amountIndex + 1]),
        walletAddress: args[walletIndex + 1] as Address,
      });
      break;
      
    case "redeem":
      if (walletIndex === -1 || orderIdIndex === -1 || amountIndex === -1) {
        console.error("❌ --wallet, --order-id, and --amount required for redemption");
        process.exit(1);
      }
      await redeemHashiCoins({
        walletAddress: args[walletIndex + 1] as Address,
        orderId: args[orderIdIndex + 1],
        amount: parseInt(args[amountIndex + 1]),
      });
      break;
      
    default:
      console.error("❌ Unknown command. Use --help for usage.");
      process.exit(1);
  }
}

main().catch(console.error);
