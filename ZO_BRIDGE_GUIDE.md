# 🔗 Zo Computer Bridge Guide

Connect Kimi CLI ↔ Zo Computer Elite Squad for tandem AI operation.

## Quick Start

```bash
# 1. Setup the bridge
./setup-zo-bridge.sh

# 2. Test connection
~/.config/kimi/skills/zo-bridge/zo.sh test

# 3. Start tandem mode
cd apex && bun run zo-connector.ts start &
```

## Available Commands

### From Any Terminal (via zo.sh)

```bash
# Send message to Zo
~/.config/kimi/skills/zo-bridge/zo.sh ask "Deploy iHhashi to production"

# Check for responses
~/.config/kimi/skills/zo-bridge/zo.sh sync

# Get Zo fleet status
~/.config/kimi/skills/zo-bridge/zo.sh status

# Broadcast to all Zo agents
~/.config/kimi/skills/zo-bridge/zo.sh broadcast "Urgent: Critical bug in production"

# Run continuous sync daemon
~/.config/kimi/skills/zo-bridge/zo.sh daemon &
```

### From APEX Fleet

```bash
cd ~/MasterBuilder7/apex

# Start tandem operation mode
bun run zo-connector.ts start &

# Delegate specific task types
bun run zo-connector.ts delegate frontend "Build login page"
bun run zo-connector.ts delegate backend "Create payment API"
bun run zo-connector.ts delegate devops "Setup K8s cluster"
bun run zo-connector.ts delegate testing "Write E2E tests"

# Check tandem status
bun run zo-connector.ts status

# Manual sync
bun run zo-connector.ts sync
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       TANDEM OPERATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Kimi CLI (35.235.249.249)          Zo Computer (kofi.zo)      │
│   ┌─────────────────────┐            ┌─────────────────────┐    │
│   │   APEX Fleet        │◄──────────►│   Elite Squad       │    │
│   │   64 Agents         │   HTTPS    │   Specialized       │    │
│   │                     │            │   Deep Work         │    │
│   │ • Frontend (15)     │◄──────────►│                     │    │
│   │ • Backend (15)      │   Sync     │ • Complex Tasks     │    │
│   │ • Testing (10)      │  10s int.  │ • Research          │    │
│   │ • DevOps (8)        │            │ • Architecture      │    │
│   │ • Reliability (5)   │◄──────────►│ • Strategy          │    │
│   │ • Evolution (3)     │  Tasks     │                     │    │
│   └─────────────────────┘            └─────────────────────┘    │
│          │                                    │                  │
│          └────────────┬───────────────────────┘                  │
│                       ▼                                          │
│              ┌─────────────────┐                                │
│              │  Shared State   │                                │
│              │  • Task Queue   │                                │
│              │  • Context      │                                │
│              │  • Results      │                                │
│              └─────────────────┘                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Message Flow

```
Kimi CLI                    Zo Computer
    │                           │
    │  1. Send Message          │
    │ ─────────────────────────>│
    │                           │
    │  2. Process & Route       │
    │     to appropriate        │
    │     Zo agent              │
    │                           │
    │  3. Response              │
    │ <─────────────────────────│
    │                           │
    │  4. Display to user       │
```

### 2. Task Delegation

```
APEX Fleet identifies task
         │
         ▼
┌─────────────────┐
│  Can APEX do    │──Yes──► APEX agents handle it
│  it efficiently?│
└─────────────────┘
         │ No
         ▼
┌─────────────────┐
│ Delegate to Zo  │──► Zo handles complex/deep work
│  specialist     │
└─────────────────┘
         │
         ▼
   Result returned
   to APEX Fleet
```

### 3. Continuous Sync

- **Interval**: 10 seconds
- **Shared Context**: Task status, results, errors
- **Auto-retry**: Failed messages queued for retry
- **Bidirectional**: Both systems can initiate tasks

## Use Cases

### Scenario 1: iHhashi Deployment

```bash
# You ask Kimi CLI:
"Deploy iHhashi to production"

# What happens:
1. Kimi CLI → APEX Fleet
2. APEX DevOps agents prepare deployment
3. Complex configuration → Delegated to Zo
4. Zo handles edge cases
5. APEX executes final deployment
6. Both systems confirm success
```

### Scenario 2: Feature Development

```bash
# You ask:
"Build a payment system for iHhashi"

# Tandem execution:
1. APEX Planning agents design architecture
2. Zo reviews and optimizes design
3. APEX Frontend agents build UI (parallel)
4. APEX Backend agents build API (parallel)
5. Zo handles complex Paystack integration
6. APEX Testing agents validate
7. Zo performs security audit
8. APEX DevOps deploys
```

### Scenario 3: 24/7 Operations

```bash
# Both systems running continuously:

APEX Fleet (always on):
├── Monitors 100+ metrics
├── Handles routine tasks
├── Runs automated tests
└── Manages deployments

Zo Computer (on-demand):
├── Handles escalations
├── Complex debugging
├── Strategic decisions
└── Architecture reviews
```

## Configuration

### Environment Variables

```bash
# ~/.bashrc or ~/.zshrc
export ZO_ENDPOINT="https://kofi.zo.computer/api/kimi-bridge"
export APEX_DAILY_BUDGET="500"
export APEX_HOURLY_BUDGET="50"
export KIMI_ZO_SYNC_INTERVAL="10"
```

### Skill Configuration

Location: `~/.config/kimi/skills/zo-bridge/skill.yaml`

Edit to customize:
- Default timeout
- Retry behavior
- Command aliases

## Troubleshooting

### Bridge Not Connecting

```bash
# Test basic connectivity
curl -I https://kofi.zo.computer/api/kimi-bridge

# Check if Zo is online
~/.config/kimi/skills/zo-bridge/zo.sh status
```

### Messages Not Syncing

```bash
# Check queue
cat /tmp/zo_bridge_queue.json

# Clear stuck queue
rm /tmp/zo_bridge_queue.json

# Restart daemon
pkill -f zo.sh
~/.config/kimi/skills/zo-bridge/zo.sh daemon &
```

### APEX Not Delegating

```bash
# Check APEX connector status
cd ~/MasterBuilder7/apex
bun run zo-connector.ts status

# Manual sync
bun run zo-connector.ts sync
```

## Advanced Usage

### Custom Task Types

Create your own task delegations:

```typescript
// In your script
const task = {
  task_id: crypto.randomUUID(),
  type: "custom_research",
  description: "Research South African payment regulations",
  priority: "high",
  context: { 
    domain: "fintech",
    country: "ZA",
    deadline: "2026-03-10"
  }
};

await zo.delegateTask(task);
```

### Shared State

Both systems can read/write to shared state:

```bash
# Kimi CLI writes
~/.config/kimi/skills/zo-bridge/zo.sh ask "Context: iHhashi v1.2.0 released"

# Zo reads and acts on context
# Zo updates with new findings
# Kimi CLI reads updates via sync
```

### Batch Operations

```bash
# Send multiple tasks
for task in "frontend" "backend" "devops"; do
  bun run zo-connector.ts delegate "$task" "Setup $task for new project"
done
```

## Best Practices

1. **Start Simple**: Test with single messages before full tandem mode
2. **Monitor Costs**: Both systems use AI - track combined spend
3. **Use Queues**: Don't overwhelm Zo - let queue handle retries
4. **Sync Regularly**: Run daemon or sync every few minutes
5. **Share Context**: Always include relevant context with tasks
6. **Review Results**: Check both APEX and Zo outputs regularly

## Integration with OpenFang

To include OpenFang in the tandem:

```bash
# OpenFang runs on 127.0.0.1:4200
# Configure it to forward to Zo bridge:

curl -X POST http://127.0.0.1:4200/api/configure \
  -d '{
    "zo_bridge": "https://kofi.zo.computer/api/kimi-bridge",
    "apex_endpoint": "http://localhost:7777"
  }'
```

## Security Notes

- All communication is HTTPS encrypted
- API keys stored in environment variables
- Queue files are temporary (RAM or /tmp)
- No persistent credentials in code

## Support

For issues:
1. Check logs: `/var/log/apex-zo/`
2. Test connection: `zo.sh test`
3. Review GitHub: https://github.com/youngstunners88/APEX-Fleet

---

**Result**: You now have 64 APEX agents + Zo Elite Squad working together 24/7! 🦀⚡🔗
