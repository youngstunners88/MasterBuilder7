# Sub-Atomic Agent Architecture
## Enterprise-Grade Automation on Ultra-Low Resources

### Vision
Instead of 10 expensive cloud agents costing $500+/month, deploy 1000+ sub-atomic agents running on $5 Raspberry Pi Zeros, old smartphones, and refurbished hardware. Each agent consumes <100MB RAM and communicates via P2P mesh networks.

### Target Context: South African Townships
- **Electricity**: Intermittent (load shedding up to 12 hours/day)
- **Internet**: Expensive, unreliable, often prepaid mobile data
- **Hardware**: Mobile phones more common than computers
- **Budget**: Ultra-low cost essential for viability

---

## Core Principles

### 1. Ephemeral by Design
```
Spawn → Execute → Die (in seconds, not hours)
```
- Agents live for single tasks
- No persistent state on device
- Stateless recovery from any node

### 2. Swarm Intelligence
- No central coordinator
- Emergent behavior from simple rules
- Self-healing through redundancy

### 3. Offline-First
- Mesh networking (WiFi Direct, Bluetooth, LoRa)
- CRDTs for conflict-free synchronization
- Store-and-forward messaging

### 4. Resource Constraints
- <100MB RAM per agent
- <50MB disk footprint
- Works on Raspberry Pi Zero W ($5), old Android phones

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUB-ATOMIC AGENT SWARM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  Worker     │  │  Worker     │  │  Worker     │  │  Worker     │        │
│   │  Agent      │  │  Agent      │  │  Agent      │  │  Agent      │        │
│   │  (Pi Zero)  │  │  (Phone)    │  │  (Pi Zero)  │  │  (Phone)    │        │
│   │  512MB RAM  │  │  1GB RAM    │  │  512MB RAM  │  │  2GB RAM    │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          │                │                │                │               │
│          └────────────────┴────────────────┴────────────────┘               │
│                              Gossip Protocol                                  │
│                    (WiFi Direct / Bluetooth / LoRa)                          │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                    Mesh Network Layer                            │       │
│   │         ┌──────────┐    ┌──────────┐    ┌──────────┐           │       │
│   │         │ Gateway  │◄──►│ Gateway  │◄──►│ Gateway  │           │       │
│   │         │ Node     │    │ Node     │    │ Node     │           │       │
│   │         └────┬─────┘    └────┬─────┘    └────┬─────┘           │       │
│   │              │               │               │                  │       │
│   │              └───────────────┴───────────────┘                  │       │
│   │                        Internet (when available)                 │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              iHhashi Core Integration Layer                      │       │
│   │         Order Routing │ Payments │ Tracking │ Analytics          │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Types

### 1. Worker Agents (W)
- **Task**: Execute single micro-tasks
- **Lifespan**: 10-60 seconds
- **Resources**: 50-100MB RAM
- **Examples**: Validate order, calculate route segment, check inventory

### 2. Router Agents (R)
- **Task**: Route messages, maintain routing tables
- **Lifespan**: Persistent (with failover)
- **Resources**: 80-120MB RAM
- **Examples**: Message broker, task distributor

### 3. Consensus Agents (C)
- **Task**: Participate in distributed consensus
- **Lifespan**: Persistent
- **Resources**: 100-150MB RAM
- **Examples**: Vote on transaction validity, resolve conflicts

### 4. Inference Agents (I)
- **Task**: Run tiny LLMs locally
- **Lifespan**: Persistent
- **Resources**: 150-300MB RAM
- **Examples**: Text classification, simple generation, sentiment analysis

### 5. Storage Agents (S)
- **Task**: Store CRDT data shards
- **Lifespan**: Persistent
- **Resources**: 100-200MB RAM + storage
- **Examples**: Order state, user profiles, route cache

---

## Cost Analysis

### Hardware Options

| Device | Cost (ZAR) | Cost (USD) | RAM | Power | Use Case |
|--------|------------|------------|-----|-------|----------|
| Raspberry Pi Zero 2 W | R180 | $10 | 512MB | 2.5W | Worker, Router |
| Raspberry Pi Zero W | R150 | $8 | 512MB | 1.5W | Worker, Storage |
| Refurbished Android (2018) | R200-400 | $11-22 | 2-4GB | 5W | Inference, Router |
| ESP32-S3 | R80 | $4 | 512KB | 0.5W | Sensor, Minimal Worker |
| Orange Pi Zero 2 | R200 | $11 | 512MB | 2W | Worker, Storage |

### Monthly Operating Costs (Per Agent)

| Component | Cost (ZAR/month) | Cost (USD/month) |
|-----------|------------------|------------------|
| Electricity (2W avg, 12h/day) | R5 | $0.28 |
| Mobile data (100MB/day) | R30 | $1.67 |
| Hardware amortization (2 years) | R8 | $0.44 |
| **Total per agent** | **R43** | **$2.39** |

### Swarm Economics (1000 Agents)

| Metric | Traditional Cloud | Sub-Atomic Swarm | Savings |
|--------|-------------------|------------------|---------|
| Monthly cost | $5,000+ | $2,390 | 52% |
| Hardware upfront | $0 | $10,000 | N/A |
| Offline capability | No | Yes | Critical |
| Fault tolerance | Limited | Extreme | High |
| Latency (local) | 50-200ms | 1-10ms | 95% |

---

## Implementation Stack

### Core Language: Rust
- Zero-cost abstractions
- Memory safety without GC
- Small binary sizes (<10MB)
- Excellent async/await

### Inference: Python (selective)
- ONNX Runtime for tiny models
- llama.cpp for local LLMs
- Only on capable nodes

### Mesh Networking: Go (optional bridges)
- libp2p implementation
- Bluetooth LE support

---

## File Structure

```
subatomic-agents/
├── core/                    # Agent lifecycle & core types
│   ├── agent.rs            # Base agent trait
│   ├── lifecycle.rs        # Spawn/execute/die logic
│   ├── task.rs             # Task definitions
│   └── swarm.rs            # Swarm coordination
├── protocols/              # Communication protocols
│   ├── gossip.rs           # Gossip protocol
│   ├── crdt.rs             # CRDT implementations
│   ├── message.rs          # Message formats
│   └── routing.rs          # Mesh routing
├── inference/              # Local LLM inference
│   ├── models.rs           # Model definitions
│   ├── runtime.rs          # ONNX runtime wrapper
│   └── tasks.rs            # Inference tasks
├── networking/             # P2P networking
│   ├── mesh.rs             # Mesh network layer
│   ├── transport.rs        # Transport abstractions
│   ├── wifi_direct.rs      # WiFi Direct implementation
│   └── bluetooth.rs        # Bluetooth mesh
├── consensus/              # Distributed consensus
│   ├── raft.rs             # Raft implementation (light)
│   ├── gossip_consensus.rs # Gossip-based consensus
│   └── voting.rs           # Voting mechanisms
├── incentives/             # Economic incentives
│   ├── reputation.rs       # Reputation system
│   ├── rewards.rs          # Reward distribution
│   └── proof_of_work.rs    # Lightweight PoW
├── integration/            # iHhashi integration
│   ├── orders.rs           # Order processing
│   ├── payments.rs         # Payment validation
│   ├── routing.rs          # Route optimization
│   └── sync.rs             # State synchronization
├── examples/               # Example implementations
│   ├── pi_zero_worker/     # Pi Zero worker agent
│   ├── android_agent/      # Android agent app
│   ├── gateway_node/       # Gateway node
│   └── inference_node/     # Inference-capable node
└── docs/                   # Documentation
    ├── ARCHITECTURE.md     # This file
    ├── DEPLOYMENT.md       # Deployment guide
    └── API.md              # API reference
```

---

## Quick Start

```bash
# Build for Pi Zero (ARMv6)
cd core && cargo build --release --target arm-unknown-linux-gnueabihf

# Build for Android
./scripts/build-android.sh

# Deploy to Pi Zero
./scripts/deploy-pi.sh pi@192.168.1.100

# Start agent swarm
./subatomic-agent --mode worker --mesh-id township-alpha --bootstrap 192.168.1.1
```

---

## Security Model

### Threats Addressed
1. **Byzantine nodes**: Tolerate up to f faulty nodes in 3f+1 total
2. **Sybil attacks**: Reputation-based entry, proof-of-work for new nodes
3. **Eavesdropping**: All messages encrypted with ephemeral keys
4. **Replay attacks**: Sequence numbers + timestamps

### Encryption
- Noise Protocol for transport encryption
- Ephemeral keys per session
- No central certificate authority

---

## Integration with iHhashi

The sub-atomic agent swarm integrates with iHhashi to provide:

1. **Offline Order Routing**: Orders route through mesh when internet down
2. **Local ETA Calculation**: Swarm calculates ETAs using route memory
3. **Payment Validation**: Consensus validates payment state
4. **Delivery Confirmation**: Multi-agent confirmation of delivery
5. **Dispute Resolution**: Swarm votes on dispute outcomes

See `integration/` directory for implementation details.

---

## Next Steps

1. **Phase 1**: Core agent lifecycle (Week 1-2)
2. **Phase 2**: Gossip protocol + CRDTs (Week 3-4)
3. **Phase 3**: Mesh networking (Week 5-6)
4. **Phase 4**: Consensus mechanism (Week 7-8)
5. **Phase 5**: iHhashi integration (Week 9-10)
6. **Phase 6**: Township pilot (Week 11-12)

---

## License

MIT - Designed for the people of South Africa
