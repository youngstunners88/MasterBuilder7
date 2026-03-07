# 🚀 N8N 24-Agent Automation Environment

## Overview

This is the **MasterBuilder7 n8n Automation Facility** - a parallel execution environment where 24 AI agents operate in synchronicity across 3 Zo Computers for maximum development velocity.

```
╔══════════════════════════════════════════════════════════════════╗
║                    🤖 24-AGENT PARALLEL ORCHESTRATOR            ║
╠══════════════════════════════════════════════════════════════════╣
║  Tier 1: Elite Squad (8 agents)                                  ║
║  Tier 2: Specialized (8 agents)                                  ║
║  Tier 3: Support (8 agents)                                      ║
╠══════════════════════════════════════════════════════════════════╣
║  3 Zo Computers | Parallel Execution | Auto-Commit              ║
╚══════════════════════════════════════════════════════════════════╝
```

## 🎯 Repository

All commits go to: **https://github.com/youngstunners88/MasterBuilder7.git**

## 🏗️ Architecture

### 3 Zo Computers (Load Balanced)

| Computer | IP | Role | Agents |
|----------|-----|------|--------|
| Zo-1 (Primary) | 100.127.121.51 | Command & Control | 8 agents |
| Zo-2 (Secondary) | 100.127.121.52 | Execution | 8 agents |
| Zo-3 (Tertiary) | 100.127.121.53 | Testing & QA | 8 agents |

### 24 Agent Distribution

#### Tier 1: Elite Squad (8 agents)
1. **Captain** - Orchestration & decision making
2. **Meta-Router** - Load balancing & routing
3. **Architect** - System design & planning
4. **Frontend** - UI/UX development
5. **Backend** - API & database
6. **Guardian** - QA & security
7. **DevOps** - CI/CD & infrastructure
8. **Evolution** - ML & optimization

#### Tier 2: Specialized (8 agents)
9. **Surgical Editor** - Multi-file refactoring
10. **Intelligence Scout** - Real-time intel gathering
11. **Architecture Oracle** - Design review
12. **Test Warlord** - Test generation & coverage
13. **Security Sentinel** - SAST & vulnerability scanning
14. **Performance Hitman** - Optimization
15. **PR Commando** - PR automation
16. **Debug Detective** - Log analysis & RCA

#### Tier 3: Support (8 agents)
17. **Atom-of-Thought** - Logical decomposition
18. **Quantum-MCP** - Quantum computing
19. **Parallel Executor** - Concurrent execution
20. **Task Queue** - Backlog management
21. **Context Preloader** - Cache warming
22. **Change Summarizer** - Git tracking
23. **Vector Memory** - Embeddings & search
24. **Anomaly Detector** - Monitoring

## 🚀 Quick Start

### 1. Deploy All 24 Agents

```bash
cd ~/MasterBuilder7
bun deploy/agent-deployer.ts deploy --mode=parallel --stress
```

### 2. Start n8n Workflow

```bash
# Import workflow
n8n import:workflow --input=./n8n-workflows/24-agent-orchestrator.json

# Start n8n
n8n start
```

### 3. Start Inter-Zo Synchronization

```bash
bun core/inter-zo-protocol.ts start-sync
```

### 4. Run Stress Tests

```bash
bun core/stress-test-framework.ts run --duration=120 --agents=24
```

## 📋 Available Commands

### Agent Deployer
```bash
# Deploy with all options
bun deploy/agent-deployer.ts deploy \
  --mode=parallel \
  --stress \
  --no-test \
  --no-commit

Modes:
  parallel   Deploy all agents simultaneously
  sequential Deploy one by one
  canary     Deploy to one Zo first
```

### Inter-Zo Protocol
```bash
# Deploy 24 agents across 3 Zo computers
bun core/inter-zo-protocol.ts deploy

# Manual sync
bun core/inter-zo-protocol.ts sync

# Check status
bun core/inter-zo-protocol.ts status

# Start/stop continuous sync
bun core/inter-zo-protocol.ts start-sync
bun core/inter-zo-protocol.ts stop-sync
```

### Stress Test Framework
```bash
# Single stress test
bun core/stress-test-framework.ts run \
  --duration=60 \
  --agents=24 \
  --iterations=100 \
  --cpu=80 \
  --memory=512 \
  --latency=500

# Continuous rebuild cycle
bun core/stress-test-framework.ts continuous \
  --interval=300000 \
  --duration=60 \
  --agents=24
```

## 🔄 Automated Workflow

The n8n workflow runs automatically every 5 minutes:

1. **Initialize** - Load 24 agent configurations
2. **Distribute** - Spread agents across 3 Zo computers
3. **Deploy** - Deploy to each Zo in parallel
4. **Sync** - Synchronize agent status
5. **Git Sync** - Pull latest from MasterBuilder7
6. **Generate Tasks** - Create parallel work items
7. **Execute** - Run tasks across all agents
8. **Commit** - Push changes to MasterBuilder7
9. **Monitor** - Continuous health checks

## 📊 Stress Testing

### Default Thresholds
- **CPU**: 80%
- **Memory**: 512 MB
- **Latency**: 500ms
- **Error Rate**: 5%

### Continuous Rebuild Cycle
The system continuously:
1. Runs stress tests
2. Validates against thresholds
3. Rebuilds if tests pass
4. Commits to MasterBuilder7
5. Repeats every 5 minutes

## 🔗 Integration Points

### Git Repository
- **URL**: https://github.com/youngstunners88/MasterBuilder7.git
- **Branch**: master
- **Auto-commit**: Enabled
- **Commit message**: `Automated build: TIMESTAMP UTC - 24 agents parallel execution`

### Zo Computer API
- **Port**: 4200
- **Protocol**: HTTP/REST
- **Endpoints**:
  - `POST /api/agent/deploy` - Deploy agents
  - `POST /api/task/execute` - Execute tasks
  - `GET /api/status` - Health check

### n8n Webhooks
- **Workflow ID**: 24-agent-orchestrator
- **Trigger**: Every 5 minutes (configurable)
- **Parallel Execution**: Enabled

## 📈 Monitoring

### Dashboard Metrics
- Active agents (24/24)
- Zo computer health (3/3)
- Task queue depth
- Average execution time
- Error rate
- Git sync status

### Alerts
- Agent failure
- Zo computer offline
- High error rate (>5%)
- Git sync failure
- Threshold violations

## 🛠️ Troubleshooting

### Agents Not Deploying
```bash
# Check Zo computer connectivity
bun core/inter-zo-protocol.ts status

# Restart sync
bun core/inter-zo-protocol.ts stop-sync
bun core/inter-zo-protocol.ts start-sync
```

### Stress Test Failures
```bash
# Run with verbose output
bun core/stress-test-framework.ts run --duration=30 --agents=8

# Check thresholds
bun core/stress-test-framework.ts run --cpu=90 --memory=1024
```

### Git Sync Issues
```bash
# Manual sync
cd ~/MasterBuilder7
git pull mb7 master
git add -A
git commit -m "Manual sync"
git push mb7 master
```

## 🔐 Security

- All Zo computers use isolated networks
- Git credentials stored in environment variables
- No secrets committed to repository
- Agent communication encrypted (HTTPS)

## 📝 File Structure

```
MasterBuilder7/
├── n8n-workflows/
│   └── 24-agent-orchestrator.json    # n8n workflow definition
├── core/
│   ├── inter-zo-protocol.ts          # Inter-Zo communication
│   └── stress-test-framework.ts      # Stress testing
├── deploy/
│   └── agent-deployer.ts             # Agent deployment
├── agents/                           # Agent definitions
├── skills/                           # Skill implementations
└── N8N-AUTOMATION-README.md          # This file
```

## 🎮 Operation Modes

### Development Mode
```bash
# Quick iteration, no commit
bun deploy/agent-deployer.ts deploy --mode=parallel --no-commit --no-test
```

### Production Mode
```bash
# Full pipeline with stress testing
bun deploy/agent-deployer.ts deploy --mode=parallel --stress --auto-test --auto-commit
```

### Canary Mode
```bash
# Test on one Zo first
bun deploy/agent-deployer.ts deploy --mode=canary
```

## 🎯 Mission Status

```
╔══════════════════════════════════════════════════════════════════╗
║                    MISSION STATUS BOARD                          ║
╠══════════════════════════════════════════════════════════════════╣
║  🤖 Agents:        24/24 OPERATIONAL                             ║
║  🖥️  Zo Computers:  3/3 ONLINE                                   ║
║  🔄 Sync:           ACTIVE (5s interval)                         ║
║  🧪 Tests:          PASSING                                      ║
║  📊 Stress:         WITHIN THRESHOLDS                            ║
║  📁 Git:            SYNCED                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  🟢 ALL SYSTEMS OPERATIONAL                                      ║
╚══════════════════════════════════════════════════════════════════╝
```

## 💀 Ready for Combat

The facility is now operational. All 24 agents are deployed across 3 Zo computers, running in parallel with continuous stress testing and automated commits to MasterBuilder7.

**Command**: `bun deploy/agent-deployer.ts deploy --stress`

**Target**: https://github.com/youngstunners88/MasterBuilder7.git

**Status**: 🔥 MAXIMUM OVERDRIVE
