# iHhashi Coin - Launch Checklist

## Pre-Launch

### 1. Set Up Wallets
- [ ] Create iHhashi Treasury wallet (receives 20% platform referral forever)
- [ ] Fund wallet with ETH for gas on Base
- [ ] Store private key securely (Zo Secrets)

### 2. Get Zora API Key
- [ ] Go to https://zora.co/settings/developer
- [ ] Create API key
- [ ] Add to Zo Secrets as `ZORA_API_KEY`

### 3. Set Environment Variables
Add to Zo Secrets (Settings > Advanced):
```
ZORA_API_KEY=your-key
IHHASHI_TREASURY=0xTreasuryAddress
IHHASHI_CREATOR=0xCreatorAddress
BASE_RPC_URL=https://mainnet.base.org
```

## Deploy iHhashi Coin

```bash
cd /home/workspace/iHhashi/hashi-coin
bun scripts/create-hashi-coin.ts --private-key 0x...
```

## Post-Launch

### 1. Record Contract Addresses
After deployment, save these:
- Coin Address: `0x...`
- Pool Address: `0x...`
- Transaction Hash: `0x...`

### 2. Update Environment
```env
HASHI_COIN_ADDRESS=0xDeployedCoinAddress
HASHI_COIN_POOL=0xPoolAddress
```

### 3. Verify on Zora
- View at: https://zora.co/collect/base:[COIN_ADDRESS]
- Check trading is active

### 4. Integrate with iHhashi Backend
- Add API endpoints for mint/burn/redeem
- Update referral system to support trade referrers

## Referral Rewards Summary

| Type | Who Earns | Amount | Duration |
|------|-----------|--------|----------|
| Platform Referral | iHhashi | 20% of all fees | Forever |
| Trade Referral | Referring user | 4% of trade | Per trade |
| Creator | Payout recipient | 50% of all fees | Forever |

## Revenue Projection

Assuming $10,000 monthly trading volume:
- Total fees (1%): $100/month
- iHhashi earns (20%): $20/month
- Trade referrers earn (4%): $4 per referred trade

Assuming $100,000 monthly trading volume:
- Total fees (1%): $1,000/month
- iHhashi earns (20%): $200/month
- Trade referrers earn (4%): $40 per referred trade

## Next Steps

1. Deploy iHhashi Coin
2. Add liquidity (optional - initial liquidity provided by Zora)
3. Build frontend integration
4. Launch marketing campaign
5. Monitor trading volume and rewards
