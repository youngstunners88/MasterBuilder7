# Gold Horse Status System - Technical Design

## Executive Summary

This document outlines the technical implementation for integrating **Gold Horse status** (100K+ iHhashi Coin holders) with the existing **Blue Horse verification system**, leveraging Zora V4's on-chain capabilities while building custom incentive mechanisms.

---

## 1. Status System Architecture

### 1.1 Blue Horse vs Gold Horse: Different Dimensions

```
┌─────────────────────────────────────────────────────────────────┐
│                    IHHASHI STATUS MATRIX                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   BLUE HORSE (Trust)          GOLD HORSE (Commitment)           │
│   ══════════════════          ═══════════════════════           │
│                                                                 │
│   • Identity verified          • 100K+ HASHI held               │
│   • Business verified          • Stake-weighted rewards         │
│   • Good standing              • Governance rights              │
│   • Platform trust             • Economic commitment            │
│                                                                 │
│   EARNED THROUGH:              EARNED THROUGH:                  │
│   • KYC verification           • Buying & holding               │
│   • Document submission        • Staking (multipliers)          │
│   • Track record               • Long-term commitment           │
│                                                                 │
│   BENEFITS:                    BENEFITS:                        │
│   • Priority listing           • Fee share from trades          │
│   • Higher search rank         • Exclusive discounts            │
│   • Trust badge                • Governance voting              │
│   • Faster support             • Premium features               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Combined Status Tiers

| Blue Horse | Gold Horse | Combined Status | Benefits |
|------------|------------|-----------------|----------|
| ❌ No | ❌ No | **Standard User** | Basic access |
| ✅ Yes | ❌ No | **Trusted User** | Priority support, verified badge |
| ❌ No | ✅ Yes | **Investor** | Fee share, discounts (no trust badge) |
| ✅ Yes | ✅ Yes | **Elite Partner** | ALL benefits + governance + highest fee share |

**Key Insight**: The statuses are **orthogonal** - you can have either, both, or neither. This allows:
- New users to buy Gold Horse without verification (but limited trust)
- Verified users (Blue Horse) to earn Gold Horse for maximum benefits
- Flexibility for different user types

---

## 2. Technical Implementation

### 2.1 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IHHASHI PLATFORM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │   Mobile    │     │    Web      │     │   Admin     │                  │
│   │    App      │     │   Portal    │     │  Dashboard  │                  │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                  │
│          │                   │                   │                          │
│          └───────────────────┼───────────────────┘                          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        API GATEWAY (FastAPI)                         │  │
│   │  • Authentication (Supabase)                                        │  │
│   │  • Rate limiting                                                    │  │
│   │  • Status resolution                                                │  │
│   └────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                        │
│          ┌─────────────────────────┼─────────────────────────┐             │
│          │                         │                         │             │
│          ▼                         ▼                         ▼             │
│   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐        │
│   │  MongoDB    │          │   Redis     │          │ Blockchain  │        │
│   │  (Web2)     │          │   (Cache)   │          │  Indexer    │        │
│   │             │          │             │          │             │        │
│   │ • Users     │          │ • Status    │          │ • Balances  │        │
│   │ • Blue Horse│          │ • Sessions  │          │ • Stakes    │        │
│   │ • Orders    │          │ • Events    │          │ • Events    │        │
│   └─────────────┘          └─────────────┘          └──────┬──────┘        │
│                                                            │              │
│                                                            ▼              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        BASE NETWORK (L2)                             │  │
│   │                                                                      │  │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │  │
│   │  │  HASHI COIN  │    │ HASHI VAULT  │    │   STATUS     │          │  │
│   │  │  (ERC20)     │───▶│  (Staking)   │───▶│  ORACLE      │          │  │
│   │  │              │    │              │    │              │          │  │
│   │  │ Zora V4 Pool │    │ Time-weighted│    │ Emits status │          │  │
│   │  │              │    │ Multipliers  │    │ changes      │          │  │
│   │  └──────────────┘    └──────────────┘    └──────────────┘          │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Smart Contract Architecture

#### 2.2.1 Hashi Vault Contract (Staking)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title HashiVault
 * @notice Time-weighted staking for iHhashi Coin with Gold Horse status tracking
 */
contract HashiVault is ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;
    
    // Constants
    uint256 public constant MIN_STAKE_DURATION = 30 days;
    uint256 public constant GOLD_HORSE_THRESHOLD = 100_000 * 1e18; // 100K tokens
    uint256 public constant UNBONDING_PERIOD = 7 days;
    
    // Multipliers (scaled by 100)
    uint256 public constant SILVER_MULTIPLIER = 80;   // 0.8x
    uint256 public constant GOLD_MULTIPLIER = 100;    // 1.0x
    uint256 public constant PLATINUM_MULTIPLIER = 150; // 1.5x
    uint256 public constant DIAMOND_MULTIPLIER = 250;  // 2.5x
    
    // Structs
    struct Stake {
        uint256 amount;
        uint256 startTime;
        uint256 lockDuration;
        uint256 lastClaimTime;
        bool unbonding;
        uint256 unbondingStartTime;
    }
    
    struct UserStatus {
        bool isGoldHorse;
        uint256 effectiveBalance; // amount * multiplier
        uint256 tier; // 0=none, 1=silver, 2=gold, 3=platinum, 4=diamond
    }
    
    // State
    IERC20 public immutable hashiToken;
    
    mapping(address => Stake) public stakes;
    mapping(address => UserStatus) public userStatuses;
    
    address[] public goldHorseHolders;
    mapping(address => uint256) public goldHorseIndex; // For O(1) removal
    
    uint256 public totalStaked;
    uint256 public totalEffectiveBalance; // Sum of all effective balances
    
    // Events
    event Staked(address indexed user, uint256 amount, uint256 lockDuration);
    event UnstakeInitiated(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event GoldHorseStatusChanged(address indexed user, bool isGoldHorse);
    event RewardsClaimed(address indexed user, uint256 amount);
    
    constructor(address _hashiToken) Ownable(msg.sender) {
        hashiToken = IERC20(_hashiToken);
    }
    
    /**
     * @notice Stake HASHI tokens with a lock duration
     * @param amount Amount to stake
     * @param lockDuration Lock duration in seconds (30-365 days)
     */
    function stake(uint256 amount, uint256 lockDuration) external nonReentrant {
        require(amount > 0, "Amount must be > 0");
        require(lockDuration >= MIN_STAKE_DURATION, "Lock too short");
        require(lockDuration <= 365 days, "Lock too long");
        require(stakes[msg.sender].amount == 0, "Already staked");
        
        hashiToken.safeTransferFrom(msg.sender, address(this), amount);
        
        uint256 tier = _calculateTier(lockDuration);
        uint256 multiplier = _getMultiplier(tier);
        uint256 effectiveBalance = (amount * multiplier) / 100;
        
        stakes[msg.sender] = Stake({
            amount: amount,
            startTime: block.timestamp,
            lockDuration: lockDuration,
            lastClaimTime: block.timestamp,
            unbonding: false,
            unbondingStartTime: 0
        });
        
        totalStaked += amount;
        totalEffectiveBalance += effectiveBalance;
        
        _updateGoldHorseStatus(msg.sender, amount, effectiveBalance);
        
        emit Staked(msg.sender, amount, lockDuration);
    }
    
    /**
     * @notice Initiate unstake (starts unbonding period)
     */
    function initiateUnstake() external nonReentrant {
        Stake storage userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake");
        require(!userStake.unbonding, "Already unbonding");
        
        // Check if lock period is over
        bool lockExpired = block.timestamp >= userStake.startTime + userStake.lockDuration;
        
        userStake.unbonding = true;
        userStake.unbondingStartTime = block.timestamp;
        
        emit UnstakeInitiated(msg.sender, userStake.amount);
    }
    
    /**
     * @notice Complete unstake after unbonding period
     */
    function completeUnstake() external nonReentrant {
        Stake storage userStake = stakes[msg.sender];
        require(userStake.unbonding, "Not unbonding");
        require(block.timestamp >= userStake.unbondingStartTime + UNBONDING_PERIOD, "Unbonding not complete");
        
        uint256 amount = userStake.amount;
        uint256 tier = _calculateTier(userStake.lockDuration);
        uint256 multiplier = _getMultiplier(tier);
        uint256 effectiveBalance = (amount * multiplier) / 100;
        
        // Apply early unstake penalty if lock not expired
        uint256 penalty = 0;
        if (block.timestamp < userStake.startTime + userStake.lockDuration) {
            penalty = _calculatePenalty(userStake.lockDuration, block.timestamp - userStake.startTime);
            // Penalty is burned (sent to dead address or actually burned)
            if (penalty > 0) {
                hashiToken.safeTransfer(address(0x000000000000000000000000000000000000dEaD), (amount * penalty) / 100);
                amount -= (amount * penalty) / 100;
            }
        }
        
        totalStaked -= userStake.amount;
        totalEffectiveBalance -= effectiveBalance;
        
        delete stakes[msg.sender];
        _removeGoldHorseStatus(msg.sender);
        
        hashiToken.safeTransfer(msg.sender, amount);
        
        emit Unstaked(msg.sender, amount);
    }
    
    /**
     * @notice Check and update Gold Horse status
     * @param user Address to check
     */
    function checkGoldHorseStatus(address user) public view returns (bool) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return false;
        
        uint256 tier = _calculateTier(userStake.lockDuration);
        uint256 multiplier = _getMultiplier(tier);
        uint256 effectiveBalance = (userStake.amount * multiplier) / 100;
        
        return effectiveBalance >= GOLD_HORSE_THRESHOLD;
    }
    
    /**
     * @notice Get user's effective balance for reward calculations
     */
    function getEffectiveBalance(address user) external view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 tier = _calculateTier(userStake.lockDuration);
        uint256 multiplier = _getMultiplier(tier);
        return (userStake.amount * multiplier) / 100;
    }
    
    /**
     * @notice Get all Gold Horse holders
     */
    function getGoldHorseHolders() external view returns (address[] memory) {
        return goldHorseHolders;
    }
    
    // Internal functions
    function _calculateTier(uint256 lockDuration) internal pure returns (uint256) {
        if (lockDuration >= 365 days) return 4; // Diamond
        if (lockDuration >= 180 days) return 3; // Platinum
        if (lockDuration >= 90 days) return 2;  // Gold
        return 1; // Silver
    }
    
    function _getMultiplier(uint256 tier) internal pure returns (uint256) {
        if (tier == 4) return DIAMOND_MULTIPLIER;
        if (tier == 3) return PLATINUM_MULTIPLIER;
        if (tier == 2) return GOLD_MULTIPLIER;
        return SILVER_MULTIPLIER;
    }
    
    function _calculatePenalty(uint256 lockDuration, uint256 timeStaked) internal pure returns (uint256) {
        // Penalty decreases over time: 15% -> 5%
        uint256 progress = (timeStaked * 100) / lockDuration;
        if (progress >= 80) return 5;
        if (progress >= 50) return 10;
        return 15;
    }
    
    function _updateGoldHorseStatus(address user, uint256 amount, uint256 effectiveBalance) internal {
        bool shouldBeGoldHorse = effectiveBalance >= GOLD_HORSE_THRESHOLD;
        bool wasGoldHorse = userStatuses[user].isGoldHorse;
        
        if (shouldBeGoldHorse && !wasGoldHorse) {
            // Add to Gold Horse list
            goldHorseHolders.push(user);
            goldHorseIndex[user] = goldHorseHolders.length - 1;
            
            userStatuses[user] = UserStatus({
                isGoldHorse: true,
                effectiveBalance: effectiveBalance,
                tier: _calculateTier(stakes[user].lockDuration)
            });
            
            emit GoldHorseStatusChanged(user, true);
        } else if (!shouldBeGoldHorse && wasGoldHorse) {
            _removeGoldHorseStatus(user);
        } else if (wasGoldHorse) {
            // Update effective balance
            userStatuses[user].effectiveBalance = effectiveBalance;
            userStatuses[user].tier = _calculateTier(stakes[user].lockDuration);
        }
    }
    
    function _removeGoldHorseStatus(address user) internal {
        if (userStatuses[user].isGoldHorse) {
            uint256 index = goldHorseIndex[user];
            uint256 lastIndex = goldHorseHolders.length - 1;
            
            // Swap and pop
            if (index != lastIndex) {
                address lastHolder = goldHorseHolders[lastIndex];
                goldHorseHolders[index] = lastHolder;
                goldHorseIndex[lastHolder] = index;
            }
            
            goldHorseHolders.pop();
            delete goldHorseIndex[user];
            
            emit GoldHorseStatusChanged(user, false);
        }
        
        delete userStatuses[user];
    }
}
```

#### 2.2.2 Status Oracle Contract

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title HashiStatusOracle
 * @notice Emits status changes for off-chain indexing
 */
contract HashiStatusOracle is Ownable {
    // Reference to the vault
    address public vault;
    
    // Price feed for HASHI/USD (can be Chainlink or custom)
    AggregatorV3Interface public priceFeed;
    
    // Status thresholds in USD terms (optional alternative)
    uint256 public goldHorseUSDThreshold = 1000 * 1e8; // $1000 worth
    
    // Events for indexer
    event StatusUpdate(
        address indexed user,
        bool isGoldHorse,
        uint256 balance,
        uint256 effectiveBalance,
        uint256 tier,
        uint256 timestamp
    );
    
    event PriceThresholdCrossed(
        address indexed user,
        bool above,
        uint256 balance,
        uint256 price
    );
    
    constructor(address _vault, address _priceFeed) Ownable(msg.sender) {
        vault = _vault;
        priceFeed = AggregatorV3Interface(_priceFeed);
    }
    
    /**
     * @notice Called by vault when status changes
     */
    function emitStatusUpdate(
        address user,
        bool isGoldHorse,
        uint256 balance,
        uint256 effectiveBalance,
        uint256 tier
    ) external {
        require(msg.sender == vault, "Only vault");
        
        emit StatusUpdate(
            user,
            isGoldHorse,
            balance,
            effectiveBalance,
            tier,
            block.timestamp
        );
    }
    
    /**
     * @notice Check if user qualifies based on USD value (alternative)
     */
    function checkUSDQualification(address user, uint256 balance) external view returns (bool) {
        (, int256 price, , , ) = priceFeed.latestRoundData();
        uint256 usdValue = (balance * uint256(price)) / 1e18;
        return usdValue >= goldHorseUSDThreshold;
    }
}
```

---

## 3. Wallet Connection & Balance Tracking

### 3.1 Frontend Integration (React Native / Web)

```typescript
// lib/web3/wallet-connection.ts
import { createConfig, http } from 'wagmi';
import { base } from 'viem/chains';
import { injected, walletConnect, coinbaseWallet } from 'wagmi/connectors';

export const config = createConfig({
  chains: [base],
  connectors: [
    injected(),
    walletConnect({ projectId: 'YOUR_PROJECT_ID' }),
    coinbaseWallet({ appName: 'iHhashi' }),
  ],
  transports: {
    [base.id]: http('https://mainnet.base.org'),
  },
});
```

### 3.2 Balance Checking Service

```typescript
// services/gold-horse-service.ts
import { readContract } from 'viem/actions';
import { config } from '@/lib/web3/wallet-connection';

const HASHI_VAULT_ADDRESS = '0x...';
const HASHI_TOKEN_ADDRESS = '0x...';

// ABIs
const vaultABI = [
  {
    name: 'stakes',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'user', type: 'address' }],
    outputs: [
      { name: 'amount', type: 'uint256' },
      { name: 'startTime', type: 'uint256' },
      { name: 'lockDuration', type: 'uint256' },
      { name: 'lastClaimTime', type: 'uint256' },
      { name: 'unbonding', type: 'bool' },
      { name: 'unbondingStartTime', type: 'uint256' },
    ],
  },
  {
    name: 'getEffectiveBalance',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'user', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'userStatuses',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'user', type: 'address' }],
    outputs: [
      { name: 'isGoldHorse', type: 'bool' },
      { name: 'effectiveBalance', type: 'uint256' },
      { name: 'tier', type: 'uint256' },
    ],
  },
] as const;

const erc20ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

export interface GoldHorseStatus {
  isGoldHorse: boolean;
  walletBalance: bigint;
  stakedBalance: bigint;
  effectiveBalance: bigint;
  tier: number;
  tierName: string;
  progressToGoldHorse: number; // 0-100
  statusType: 'none' | 'investor' | 'trusted' | 'elite';
}

export class GoldHorseService {
  private client: any;
  
  constructor() {
    this.client = config.getClient();
  }
  
  /**
   * Get comprehensive status for a user
   */
  async getStatus(
    walletAddress: `0x${string}`,
    userId: string
  ): Promise<GoldHorseStatus> {
    // Parallel fetch all data
    const [walletBalance, stakeInfo, userStatus, blueHorseStatus] = await Promise.all([
      this.getWalletBalance(walletAddress),
      this.getStakeInfo(walletAddress),
      this.getOnChainStatus(walletAddress),
      this.getBlueHorseStatus(userId),
    ]);
    
    const stakedBalance = stakeInfo?.amount ?? BigInt(0);
    const totalBalance = walletBalance + stakedBalance;
    const effectiveBalance = userStatus?.effectiveBalance ?? BigInt(0);
    const isGoldHorse = userStatus?.isGoldHorse ?? false;
    const tier = userStatus?.tier ?? 0;
    
    // Calculate progress to Gold Horse
    const GOLD_HORSE_THRESHOLD = BigInt(100_000 * 1e18);
    const progressToGoldHorse = Math.min(
      100,
      Number((effectiveBalance * BigInt(100)) / GOLD_HORSE_THRESHOLD)
    );
    
    // Determine combined status
    let statusType: 'none' | 'investor' | 'trusted' | 'elite' = 'none';
    if (blueHorseStatus && isGoldHorse) {
      statusType = 'elite';
    } else if (isGoldHorse) {
      statusType = 'investor';
    } else if (blueHorseStatus) {
      statusType = 'trusted';
    }
    
    return {
      isGoldHorse,
      walletBalance,
      stakedBalance,
      effectiveBalance,
      tier,
      tierName: this.getTierName(tier),
      progressToGoldHorse,
      statusType,
    };
  }
  
  private async getWalletBalance(address: `0x${string}`): Promise<bigint> {
    try {
      const balance = await readContract(this.client, {
        address: HASHI_TOKEN_ADDRESS,
        abi: erc20ABI,
        functionName: 'balanceOf',
        args: [address],
      });
      return balance as bigint;
    } catch {
      return BigInt(0);
    }
  }
  
  private async getStakeInfo(address: `0x${string}`): Promise<any> {
    try {
      const stake = await readContract(this.client, {
        address: HASHI_VAULT_ADDRESS,
        abi: vaultABI,
        functionName: 'stakes',
        args: [address],
      });
      return stake;
    } catch {
      return null;
    }
  }
  
  private async getOnChainStatus(address: `0x${string}`): Promise<any> {
    try {
      const status = await readContract(this.client, {
        address: HASHI_VAULT_ADDRESS,
        abi: vaultABI,
        functionName: 'userStatuses',
        args: [address],
      });
      return status;
    } catch {
      return null;
    }
  }
  
  private async getBlueHorseStatus(userId: string): Promise<boolean> {
    // Call your backend API
    const response = await fetch(`/api/v1/users/${userId}/blue-horse-status`);
    const data = await response.json();
    return data.is_blue_horse === true;
  }
  
  private getTierName(tier: number): string {
    const tiers = ['None', 'Silver', 'Gold', 'Platinum', 'Diamond'];
    return tiers[tier] || 'None';
  }
}
```

### 3.3 Blockchain Indexer Service

```typescript
// services/blockchain-indexer.ts
import { createPublicClient, http, parseAbiItem } from 'viem';
import { base } from 'viem/chains';

const client = createPublicClient({
  chain: base,
  transport: http('https://mainnet.base.org'),
});

const HASHI_VAULT_ADDRESS = '0x...' as `0x${string}`;

// Event ABIs
const events = {
  GoldHorseStatusChanged: parseAbiItem(
    'event GoldHorseStatusChanged(address indexed user, bool isGoldHorse)'
  ),
  Staked: parseAbiItem(
    'event Staked(address indexed user, uint256 amount, uint256 lockDuration)'
  ),
  Unstaked: parseAbiItem(
    'event Unstaked(address indexed user, uint256 amount)'
  ),
};

export class BlockchainIndexer {
  private lastProcessedBlock: bigint = BigInt(0);
  
  /**
   * Watch for status changes and sync to database
   */
  async startWatching() {
    // Watch for new events
    const unwatch = client.watchEvent({
      address: HASHI_VAULT_ADDRESS,
      onLogs: (logs) => this.processLogs(logs),
    });
    
    // Process historical logs on startup
    await this.processHistoricalEvents();
    
    return unwatch;
  }
  
  private async processLogs(logs: any[]) {
    for (const log of logs) {
      const eventName = log.eventName;
      
      switch (eventName) {
        case 'GoldHorseStatusChanged':
          await this.handleStatusChange(
            log.args.user,
            log.args.isGoldHorse
          );
          break;
        case 'Staked':
          await this.handleStake(
            log.args.user,
            log.args.amount,
            log.args.lockDuration
          );
          break;
        case 'Unstaked':
          await this.handleUnstake(log.args.user);
          break;
      }
    }
  }
  
  private async handleStatusChange(user: `0x${string}`, isGoldHorse: boolean) {
    // Update MongoDB
    await fetch('/api/v1/internal/sync-gold-horse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        wallet_address: user.toLowerCase(),
        is_gold_horse: isGoldHorse,
      }),
    });
    
    // Invalidate Redis cache
    await fetch('/api/v1/internal/cache-invalidate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: `gold_horse:${user.toLowerCase()}` }),
    });
  }
  
  private async handleStake(
    user: `0x${string}`,
    amount: bigint,
    lockDuration: bigint
  ) {
    // Record stake in database for historical tracking
    await fetch('/api/v1/internal/record-stake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        wallet_address: user.toLowerCase(),
        amount: amount.toString(),
        lock_duration: lockDuration.toString(),
        timestamp: Date.now(),
      }),
    });
  }
  
  private async handleUnstake(user: `0x${string}`) {
    // Mark stake as ended
    await fetch('/api/v1/internal/end-stake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        wallet_address: user.toLowerCase(),
        timestamp: Date.now(),
      }),
    });
  }
  
  private async processHistoricalEvents() {
    const currentBlock = await client.getBlockNumber();
    const fromBlock = this.lastProcessedBlock || currentBlock - BigInt(10000);
    
    // Fetch all status changes
    const statusChanges = await client.getLogs({
      address: HASHI_VAULT_ADDRESS,
      event: events.GoldHorseStatusChanged,
      fromBlock,
      toBlock: currentBlock,
    });
    
    for (const log of statusChanges) {
      await this.handleStatusChange(
        log.args.user,
        log.args.isGoldHorse
      );
    }
    
    this.lastProcessedBlock = currentBlock;
  }
}
```

---

## 4. Handling Volatility

### 4.1 The Problem

When someone holds 100,000 HASHI:
- **Scenario A**: Price goes UP → Their stake is worth MORE → Still Gold Horse ✓
- **Scenario B**: Price goes DOWN → Their stake is worth LESS → Still Gold Horse ✓ (based on token count)
- **Scenario C**: They SELL some tokens → Balance drops below 100K → Should lose Gold Horse

**Key Insight**: Gold Horse status is based on **token count**, not USD value. This makes it stable and predictable.

### 4.2 Status Protection Mechanisms

```solidity
// In HashiVault.sol

/**
 * @notice Grace period for status changes
 * Users don't lose Gold Horse immediately on small drops
 */
uint256 public constant GRACE_PERIOD = 24 hours;
uint256 public constant GRACE_THRESHOLD = 95; // 95% of threshold

mapping(address => uint256) public lastBelowThresholdTime;

function _checkStatusWithGrace(address user, uint256 effectiveBalance) internal returns (bool) {
    bool aboveThreshold = effectiveBalance >= GOLD_HORSE_THRESHOLD;
    bool aboveGraceThreshold = effectiveBalance >= (GOLD_HORSE_THRESHOLD * GRACE_THRESHOLD) / 100;
    
    // If above main threshold: definitely Gold Horse
    if (aboveThreshold) {
        lastBelowThresholdTime[user] = 0;
        return true;
    }
    
    // If above grace threshold: still Gold Horse during grace period
    if (aboveGraceThreshold) {
        if (lastBelowThresholdTime[user] == 0) {
            lastBelowThresholdTime[user] = block.timestamp;
        }
        
        // Still within grace period
        if (block.timestamp < lastBelowThresholdTime[user] + GRACE_PERIOD) {
            return true;
        }
        
        // Grace period expired
        return false;
    }
    
    // Below grace threshold: immediate status loss
    return false;
}
```

### 4.3 Price Volatility Protection (Optional USD-based Alternative)

```typescript
// services/volatility-protection.ts

export class VolatilityProtection {
  private priceHistory: number[] = [];
  private readonly LOOKBACK_PERIOD = 24 * 60 * 60 * 1000; // 24 hours
  
  /**
   * Calculate time-weighted average price for stability
   */
  calculateTWAP(): number {
    const now = Date.now();
    const relevantPrices = this.priceHistory.filter(
      p => p.timestamp > now - this.LOOKBACK_PERIOD
    );
    
    if (relevantPrices.length === 0) return 0;
    
    return relevantPrices.reduce((sum, p) => sum + p.price, 0) / relevantPrices.length;
  }
  
  /**
   * Determine if price movement is extreme
   */
  isExtremeVolatility(currentPrice: number): boolean {
    const twap = this.calculateTWAP();
    if (twap === 0) return false;
    
    const deviation = Math.abs(currentPrice - twap) / twap;
    return deviation > 0.30; // 30% deviation = extreme
  }
  
  /**
   * Get adjusted threshold based on volatility
   */
  getAdjustedThreshold(baseThreshold: number, currentPrice: number): number {
    if (this.isExtremeVolatility(currentPrice)) {
      // During extreme volatility, lower threshold by 10%
      // This prevents mass status loss during crashes
      return baseThreshold * 0.9;
    }
    return baseThreshold;
  }
}
```

### 4.4 Circuit Breaker for Status Loss

```typescript
// API endpoint for status changes with circuit breaker

app.post('/api/v1/internal/sync-gold-horse', async (req, res) => {
  const { wallet_address, is_gold_horse } = req.body;
  
  // Get current market conditions
  const marketConditions = await checkMarketConditions();
  
  // Circuit breaker: Don't process status losses during extreme conditions
  if (!is_gold_horse && marketConditions.isExtremeVolatility) {
    // Queue for later processing
    await queueStatusChange({
      wallet_address,
      new_status: is_gold_horse,
      reason: 'volatility_circuit_breaker',
      scheduled_at: Date.now() + 4 * 60 * 60 * 1000, // 4 hours
    });
    
    return res.json({
      status: 'deferred',
      reason: 'Market volatility circuit breaker active',
    });
  }
  
  // Process normally
  await updateGoldHorseStatus(wallet_address, is_gold_horse);
  
  res.json({ status: 'updated' });
});
```

---

## 5. Zora V4 Hooks Integration

### 5.1 What Zora V4 Provides

| Feature | Available | How We Use It |
|---------|-----------|---------------|
| Platform Referrer (20%) | ✅ Yes | iHhashi treasury address |
| Trade Referrer (4%) | ✅ Yes | Dynamic per trade |
| Creator Rewards (50%) | ✅ Yes | Custom distribution |
| AfterSwap Hook | ✅ Yes | Event emission |
| Custom Logic | ❌ Limited | Use wrapper contracts |

### 5.2 Fee Distribution Strategy

```typescript
// Zora V4 Fee Split (1% total trading fee)
// ─────────────────────────────────────────
// Platform Referrer (iHhashi):     20% → Treasury
// Trade Referrer:                  4% → Referrer
// Creator:                        50% → Redistribution
// Protocol (Zora):                 5% → Zora
// Doppler:                         1% → Doppler
// LP Rewards:                     20% → Locked liquidity

// Our redistribution of the 50% Creator portion:
// ─────────────────────────────────────────
// Merchants (Staked):    18% → Via HashiVault
// Drivers (Staked):      18% → Via HashiVault
// Customers (Staked):    12% → Via HashiVault
// Trade Referrer Bonus:   2% → Additional incentive
// ─────────────────────────────────────────
// Total:                 50%
```

### 5.3 Custom Hook for Fee Redistribution

Since we can't modify Zora's hook, we create a **reward distributor** that receives the creator portion:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title HashiRewardDistributor
 * @notice Receives creator rewards from Zora and distributes to stakeholders
 */
contract HashiRewardDistributor is Ownable {
    IERC20 public immutable hashiToken;
    address public immutable vault;
    
    // Fee distribution percentages (scaled by 10000)
    uint256 public constant MERCHANT_SHARE = 3600; // 36%
    uint256 public constant DRIVER_SHARE = 3600;   // 36%
    uint256 public constant CUSTOMER_SHARE = 2400; // 24%
    uint256 public constant RESERVE_SHARE = 400;   // 4%
    
    // Pools (updated by backend)
    uint256 public totalMerchantEffectiveBalance;
    uint256 public totalDriverEffectiveBalance;
    uint256 public totalCustomerEffectiveBalance;
    
    mapping(address => uint256) public merchantBalances;
    mapping(address => uint256) public driverBalances;
    mapping(address => uint256) public customerBalances;
    
    event RewardsDistributed(
        uint256 totalAmount,
        uint256 merchantAmount,
        uint256 driverAmount,
        uint256 customerAmount
    );
    
    event RewardsClaimed(
        address indexed user,
        string userType,
        uint256 amount
    );
    
    constructor(
        address _hashiToken,
        address _vault
    ) Ownable(msg.sender) {
        hashiToken = IERC20(_hashiToken);
        vault = _vault;
    }
    
    /**
     * @notice Receive rewards from Zora (creator portion)
     * Called when rewards are sent to this contract
     */
    receive() external payable {
        // Convert ETH to HASHI if needed, or distribute HASHI directly
    }
    
    /**
     * @notice Distribute accumulated rewards to pools
     */
    function distributeRewards() external {
        uint256 balance = hashiToken.balanceOf(address(this));
        require(balance > 0, "No rewards to distribute");
        
        uint256 merchantAmount = (balance * MERCHANT_SHARE) / 10000;
        uint256 driverAmount = (balance * DRIVER_SHARE) / 10000;
        uint256 customerAmount = (balance * CUSTOMER_SHARE) / 10000;
        // Reserve stays in contract for operations
        
        // Allocate to pools based on effective balances
        // This is a simplified version - actual implementation would track
        // individual shares more precisely
        
        emit RewardsDistributed(
            balance,
            merchantAmount,
            driverAmount,
            customerAmount
        );
    }
    
    /**
     * @notice Claim rewards (called by users)
     */
    function claimRewards(string calldata userType) external {
        uint256 amount;
        
        if (keccak256(bytes(userType)) == keccak256(bytes("merchant"))) {
            amount = merchantBalances[msg.sender];
            merchantBalances[msg.sender] = 0;
        } else if (keccak256(bytes(userType)) == keccak256(bytes("driver"))) {
            amount = driverBalances[msg.sender];
            driverBalances[msg.sender] = 0;
        } else if (keccak256(bytes(userType)) == keccak256(bytes("customer"))) {
            amount = customerBalances[msg.sender];
            customerBalances[msg.sender] = 0;
        }
        
        require(amount > 0, "No rewards to claim");
        
        hashiToken.transfer(msg.sender, amount);
        
        emit RewardsClaimed(msg.sender, userType, amount);
    }
    
    /**
     * @notice Update effective balances (called by backend/indexer)
     */
    function updateEffectiveBalances(
        uint256 _merchantTotal,
        uint256 _driverTotal,
        uint256 _customerTotal
    ) external onlyOwner {
        totalMerchantEffectiveBalance = _merchantTotal;
        totalDriverEffectiveBalance = _driverTotal;
        totalCustomerEffectiveBalance = _customerTotal;
    }
    
    /**
     * @notice Update individual user's claimable balance
     */
    function updateUserBalance(
        address user,
        string calldata userType,
        uint256 amount
    ) external onlyOwner {
        if (keccak256(bytes(userType)) == keccak256(bytes("merchant"))) {
            merchantBalances[user] = amount;
        } else if (keccak256(bytes(userType)) == keccak256(bytes("driver"))) {
            driverBalances[user] = amount;
        } else if (keccak256(bytes(userType)) == keccak256(bytes("customer"))) {
            customerBalances[user] = amount;
        }
    }
}
```

---

## 6. Database Schema Updates

### 6.1 New Models

```python
# backend/app/models/gold_horse.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class GoldHorseStatus(BaseModel):
    """On-chain Gold Horse status synced from blockchain"""
    user_id: str
    wallet_address: str
    is_gold_horse: bool
    effective_balance: int  # In wei
    tier: int  # 0-4
    staked_amount: int
    lock_duration: int
    stake_start_time: datetime
    
    # Volatility protection
    last_below_threshold: Optional[datetime] = None
    grace_period_end: Optional[datetime] = None
    
    # Sync metadata
    last_onchain_sync: datetime
    block_number: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CombinedStatus(BaseModel):
    """Combined Blue + Gold Horse status"""
    user_id: str
    
    # Blue Horse (Web2, verification-based)
    is_blue_horse: bool
    blue_horse_level: int  # 0-3
    blue_horse_verified_at: Optional[datetime] = None
    
    # Gold Horse (Web3, stake-based)
    is_gold_horse: bool
    gold_horse_tier: int  # 0-4
    effective_balance: int
    wallet_address: Optional[str] = None
    
    # Combined status
    status_type: str  # 'none', 'trusted', 'investor', 'elite'
    
    # Benefits
    fee_share_multiplier: float = 1.0
    discount_percentage: int = 0
    free_deliveries_per_month: int = 0
    has_governance_rights: bool = False
    
    updated_at: datetime

class StakingHistory(BaseModel):
    """Record of all stakes for a user"""
    user_id: str
    wallet_address: str
    
    events: list[dict] = Field(default_factory=list)
    # Each event: {
    #   type: 'stake' | 'unstake' | 'claim',
    #   amount: int,
    #   lock_duration: int (if stake),
    #   timestamp: datetime,
    #   tx_hash: str
    # }
    
    total_staked_all_time: int = 0
    total_rewards_claimed: int = 0
    
    created_at: datetime
    updated_at: datetime
```

### 6.2 API Endpoints

```python
# backend/app/routes/gold_horse.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/v1/gold-horse", tags=["Gold Horse"])

@router.get("/status/{user_id}")
async def get_combined_status(user_id: str):
    """Get combined Blue + Gold Horse status"""
    pass

@router.post("/connect-wallet")
async def connect_wallet(
    user_id: str,
    wallet_address: str,
    signature: str  # Proof of ownership
):
    """Connect wallet to user account"""
    pass

@router.post("/stake")
async def initiate_stake(
    user_id: str,
    amount: int,
    lock_duration: int
):
    """Get transaction data for staking"""
    # Returns unsigned transaction for frontend to sign
    pass

@router.get("/rewards/{user_id}")
async def get_pending_rewards(user_id: str):
    """Get pending reward claim amount"""
    pass

@router.post("/claim-rewards")
async def claim_rewards(user_id: str):
    """Claim accumulated rewards"""
    pass

@router.get("/leaderboard")
async def get_gold_horse_leaderboard(
    user_type: Optional[str] = None,  # 'merchant', 'driver', 'customer'
    limit: int = 100
):
    """Get leaderboard of Gold Horse holders"""
    pass

# Internal endpoints (for blockchain indexer)
@router.post("/internal/sync-status")
async def sync_onchain_status(
    wallet_address: str,
    is_gold_horse: bool,
    effective_balance: int,
    tier: int,
    block_number: int
):
    """Called by blockchain indexer to sync status"""
    pass
```

---

## 7. UX Flow

### 7.1 User Journey: Becoming a Gold Horse

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GOLD HORSE JOURNEY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. DISCOVERY                                                                │
│     ┌─────────────┐                                                         │
│     │ User sees   │    "Gold Horse holders earn 18% of trading fees!"      │
│     │ promo banner│                                                         │
│     └──────┬──────┘                                                         │
│            │                                                                 │
│            ▼                                                                 │
│  2. WALLET CONNECTION                                                        │
│     ┌─────────────┐                                                         │
│     │ Connect     │    User taps "Connect Wallet"                           │
│     │ Wallet      │    → MetaMask / WalletConnect / Coinbase Wallet         │
│     └──────┬──────┘                                                         │
│            │                                                                 │
│            ▼                                                                 │
│  3. BALANCE CHECK                                                            │
│     ┌─────────────┐                                                         │
│     │ Current     │    If no HASHI: "Buy HASHI to start your journey"       │
│     │ Balance     │    If < 100K: Progress bar showing 67% to Gold Horse    │
│     └──────┬──────┘    If >= 100K: "You qualify! Stake to unlock benefits"  │
│            │                                                                 │
│            ▼                                                                 │
│  4. STAKING FLOW                                                             │
│     ┌─────────────┐                                                         │
│     │ Select      │    Choose lock duration:                                │
│     │ Duration    │    • 30-89 days (Silver Vault) - 0.8x multiplier        │
│     │             │    • 90-179 days (Gold Vault) - 1.0x                    │
│     │             │    • 180-364 days (Platinum Vault) - 1.5x               │
│     │             │    • 365+ days (Diamond Vault) - 2.5x + governance      │
│     └──────┬──────┘                                                         │
│            │                                                                 │
│            ▼                                                                 │
│  5. TRANSACTION                                                              │
│     ┌─────────────┐                                                         │
│     │ Approve &   │    1. Approve HASHI spending                            │
│     │ Stake       │    2. Sign stake transaction                            │
│     └──────┬──────┘    3. Wait for confirmation                            │
│            │                                                                 │
│            ▼                                                                 │
│  6. STATUS ACHIEVED                                                          │
│     ┌─────────────┐                                                         │
│     │ 🐴 GOLD     │    "Congratulations! You are now a Gold Horse!"        │
│     │ HORSE       │    → Badge appears in profile                           │
│     │             │    → Fee share starts accumulating                      │
│     │             │    → Exclusive features unlocked                        │
│     └─────────────┘                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Status Display in App

```tsx
// components/StatusBadge.tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface StatusBadgeProps {
  isBlueHorse: boolean;
  isGoldHorse: boolean;
  tier?: number;
  compact?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  isBlueHorse,
  isGoldHorse,
  tier = 0,
  compact = false,
}) => {
  // Determine badge type
  const getStatus = () => {
    if (isBlueHorse && isGoldHorse) {
      return {
        label: 'Elite Partner',
        color: '#FFD700', // Gold
        icon: '👑',
        subtitle: 'Maximum benefits',
      };
    }
    if (isGoldHorse) {
      return {
        label: 'Gold Horse',
        color: '#FFD700',
        icon: '🐴',
        subtitle: `${getTierName(tier)} Vault`,
      };
    }
    if (isBlueHorse) {
      return {
        label: 'Blue Horse',
        color: '#1E90FF',
        icon: '🐴',
        subtitle: 'Verified',
      };
    }
    return null;
  };

  const status = getStatus();
  if (!status) return null;

  if (compact) {
    return (
      <View style={[styles.compactBadge, { borderColor: status.color }]}>
        <Text style={styles.compactIcon}>{status.icon}</Text>
        <Text style={[styles.compactLabel, { color: status.color }]}>
          {status.label}
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.badge, { borderColor: status.color }]}>
      <View style={styles.header}>
        <Text style={styles.icon}>{status.icon}</Text>
        <Text style={[styles.label, { color: status.color }]}>
          {status.label}
        </Text>
      </View>
      <Text style={styles.subtitle}>{status.subtitle}</Text>
    </View>
  );
};

const getTierName = (tier: number): string => {
  const tiers = ['None', 'Silver', 'Gold', 'Platinum', 'Diamond'];
  return tiers[tier] || 'None';
};

const styles = StyleSheet.create({
  badge: {
    padding: 12,
    borderRadius: 12,
    borderWidth: 2,
    backgroundColor: '#1a1a1a',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  icon: {
    fontSize: 24,
  },
  label: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
  compactBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    backgroundColor: '#1a1a1a',
    gap: 4,
  },
  compactIcon: {
    fontSize: 14,
  },
  compactLabel: {
    fontSize: 12,
    fontWeight: '600',
  },
});
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Deploy iHhashi Coin on Zora V4
- [ ] Set up blockchain indexer service
- [ ] Create HashiVault contract (staking)
- [ ] Add wallet connection to mobile app
- [ ] Database schema updates

### Phase 2: Status System (Weeks 3-4)
- [ ] Implement Gold Horse status tracking
- [ ] Create combined status API
- [ ] Build status badge component
- [ ] Set up Redis caching
- [ ] Implement grace period logic

### Phase 3: Fee Distribution (Weeks 5-6)
- [ ] Deploy HashiRewardDistributor
- [ ] Connect to Zora creator rewards
- [ ] Build reward claiming UI
- [ ] Create leaderboard
- [ ] Test end-to-end flow

### Phase 4: Polish & Launch (Weeks 7-8)
- [ ] Volatility protection testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] User documentation
- [ ] Marketing materials
- [ ] Mainnet deployment

---

## 9. Security Considerations

### 9.1 Smart Contract Security
- All contracts use OpenZeppelin's ReentrancyGuard
- Timelock on governance functions (48 hours)
- Multisig (3/5) for treasury operations
- Maximum withdrawal limits per transaction
- Pausable functionality for emergencies

### 9.2 Frontend Security
- Wallet signature verification
- Rate limiting on all API endpoints
- Input validation and sanitization
- HTTPS only
- Secure storage for sensitive data

### 9.3 Operational Security
- Real-time monitoring of all transactions
- Alerts for large movements
- Regular backup of database
- Incident response playbook

---

## 10. Summary

This design creates a **robust, defensible Gold Horse status system** that:

1. **Complements Blue Horse** - Trust (verification) + Commitment (staking) = Elite status
2. **Uses Zora V4 effectively** - Platform referrer for passive income, creator rewards for redistribution
3. **Handles volatility** - Grace periods, circuit breakers, TWAP-based thresholds
4. **Provides real utility** - Fee sharing, governance, exclusive benefits
5. **Maintains token value** - Staking reduces velocity, burns create scarcity

The key insight: **Gold Horse is about economic commitment, not just holding**. By requiring staking with time locks, we create genuine long-term alignment between stakeholders and the platform.

---

*Document Version: 1.0*
*Created: 2026-03-02*
*Author: Zo (Systems Integration Specialist)*
