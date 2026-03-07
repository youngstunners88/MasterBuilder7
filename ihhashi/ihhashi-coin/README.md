# iHhashi Coin - Zora Coins Protocol Integration

On-chain iHhashi Coins for iHhashi food delivery platform. Built on Zora's V4 Coins Protocol with built-in referral rewards.

## Overview

iHhashi Coin brings iHhashi's loyalty rewards on-chain, making them tradeable and giving them real market value. Every trade generates passive income for iHhashi through Zora's referral system.

## Referral Rewards (Zora V4)

When iHhashi Coin is created on Zora, the fee structure (1% total fee on all trades) is distributed as follows:

| Recipient | % of Total Fees | Notes |
|-----------|-----------------|-------|
| **iHhashi (Platform Referrer)** | **20%** | Forever - set once at creation |
| **Trade Referrer** | **4%** | Per trade - whoever referred the buyer |
| Creator | 50% | Goes to payout recipient |
| Protocol | 5% | Zora treasury |
| Doppler | 1% | Doppler treasury |
| LP Rewards | 20% | Permanently locked in liquidity |

### Key Benefits

1. **Passive Income Forever**: iHhashi earns 20% of ALL trading fees for the lifetime of the coin
2. **Trade Referrals**: Users who refer others to buy iHhashi Coin earn 4% of that trade
3. **On-Chain Transparency**: All rewards distributed automatically on-chain
4. **Tradeable Loyalty**: Customers can buy, sell, or hold their iHhashi Coins

## Integration with iHhashi Referral System

### Existing Web2 Referrals (v0.4.0)

```
Customer Referrals:
├── Referrer: 50 iHhashi Coins
├── New Customer: 25 iHhashi Coins (welcome bonus)
└── Tiers: Bronze → Silver → Gold → Platinum

Vendor Referrals:
├── +2 FREE DAYS per vendor referral
└── Maximum: 90 extra days
```

### New On-Chain Integration (v0.5.0)

```
On-Chain iHhashi Coins:
├── Platform Referrer (iHhashi): 20% of all trading fees
├── Trade Referrers: 4% per trade
├── Customers can:
│   ├── Buy iHhashi Coins on Zora
│   ├── Sell iHhashi Coins (real market value!)
│   ├── Hold for potential appreciation
│   └── Redeem for discounts (burn mechanism)
└── Redemption:
    ├── 100 coins = Free delivery
    ├── 150 coins = R15 discount
    └── 300 coins = R30 discount
```

## Setup

### 1. Get Zora API Key

1. Go to https://zora.co
2. Create account / login
3. Navigate to https://zora.co/settings/developer
4. Create an API key

### 2. Set Environment Variables

Add to Zo Secrets (Settings > Advanced):

```env
ZORA_API_KEY=your-zora-api-key
IHHASHI_TREASURY=0xYourTreasuryAddress
IHHASHI_CREATOR=0xYourCreatorAddress
BASE_RPC_URL=https://mainnet.base.org
```

### 3. Deploy iHhashi Coin

```bash
cd /home/workspace/iHhashi/hashi-coin
bun scripts/create-hashi-coin.ts --private-key 0x...
```

## Usage

### Create iHhashi Coin

```bash
# Full creation (signs and submits transaction)
bun scripts/create-hashi-coin.ts --private-key 0xYourPrivateKey

# Get call data for frontend integration
bun scripts/create-hashi-coin.ts --get-call --creator 0xCreatorAddress
```

### Frontend Integration (React/WAGMI)

```tsx
import { createCoinCall, CreateConstants } from "@zoralabs/coins-sdk";
import { useSendTransaction } from "wagmi";
import { base } from "viem/chains";

function CreateHashiCoinButton() {
  const { sendTransaction } = useSendTransaction();
  
  const handleCreate = async () => {
    const { calls, predictedCoinAddress } = await createCoinCall({
      creator: "0xUserAddress",
      name: "iHhashi Coin",
      symbol: "HASHI",
      metadata: { type: "RAW_URI", uri: "ipfs://..." },
      currency: CreateConstants.ContentCoinCurrencies.ZORA,
      chainId: base.id,
      startingMarketCap: CreateConstants.StartingMarketCaps.LOW,
      platformReferrerAddress: "0xIHHASHI_TREASURY",
    });
    
    sendTransaction({
      to: calls[0].to,
      data: calls[0].data,
      value: calls[0].value,
    });
  };
  
  return <button onClick={handleCreate}>Create iHhashi Coin</button>;
}
```

## Architecture

```
iHhashi Platform
├── Web2 Rewards (MongoDB)
│   ├── CustomerRewardAccount
│   ├── CoinTransaction
│   └── Referral
│
├── Web3 Rewards (Zora)
│   ├── iHhashi Coin (ERC20)
│   ├── Platform Referrer: iHhashi Treasury
│   └── Trade Referrers: Per-trade
│
└── Bridge Layer
    ├── Mint on-chain (Web2 → Web3)
    ├── Burn for redemption (Web3 → Web2)
    └── Sync balances
```

## API Endpoints

### New Endpoints (v0.5.0)

```
POST /api/v1/hashicoin/mint
  - Convert Web2 iHhashi Coins to on-chain
  - Body: { amount: number, wallet_address: string }
  
POST /api/v1/hashicoin/redeem
  - Burn on-chain iHhashi Coins for discount
  - Body: { amount: number, order_id: string }
  
GET /api/v1/hashicoin/balance/:wallet
  - Get on-chain iHhashi Coin balance
  - Returns: { balance: string, value_zar: number }
  
GET /api/v1/hashicoin/rewards
  - Get iHhashi platform referrer earnings
  - Returns: { total_earned: string, pending: string }
```

## Contract Addresses

After deployment, update these:

```env
HASHI_COIN_ADDRESS=0x...  # Deployed coin address
HASHI_COIN_POOL=0x...     # Uniswap V4 pool address
```

## Security

- Platform referrer address is **immutable** once set
- Only coin owner can update payout recipient
- All rewards distributed automatically by smart contract
- No manual claiming required

## Resources

- [Zora Coins SDK Docs](https://docs.zora.co/coins/sdk)
- [Coin Rewards](https://docs.zora.co/coins/contracts/rewards)
- [Earning Referral Rewards](https://docs.zora.co/coins/contracts/earning-referral-rewards)
- [Zora Developer Settings](https://zora.co/settings/developer)

## License

MIT
