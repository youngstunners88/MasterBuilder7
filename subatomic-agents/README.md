# Sub-Atomic Agent Swarm

> **Enterprise-grade automation on ultra-low resources**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust Version](https://img.shields.io/badge/rust-1.70%2B-blue.svg)](https://www.rust-lang.org)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

## The Concept

Instead of 10 expensive cloud agents costing $500+/month, deploy **1000+ sub-atomic agents** running on:
- $5 Raspberry Pi Zeros
- Old smartphones (Android 8+)
- Refurbished hardware

Each agent:
- Consumes **<100MB RAM**
- Communicates via **P2P mesh** (WiFi Direct, Bluetooth, LoRa)
- Specializes in **single micro-tasks**
- **Self-organizes** into complex behaviors
- **Survives node failures** gracefully

## Why?

Built for **South African townships** where:
- ⚡ Electricity is intermittent (load shedding up to 12 hours/day)
- 📶 Internet is expensive/unreliable
- 💰 Hardware must be ultra-cheap
- 📱 Mobile phones are more common than computers

## Quick Start

### Raspberry Pi Zero Worker

```bash
# Install
curl -sSL https://get.ihhashi.co.za/subatomic | sh

# Run
subatomic-agent --mode worker --mesh-id township-alpha --bootstrap 192.168.1.1
```

### Docker (Development)

```bash
docker run -it --rm \
  -p 8765:8765 \
  -e MESH_ID=township-alpha \
  ihhashi/subatomic-agent:latest
```

### Build from Source

```bash
git clone https://github.com/ihhashi/subatomic-agents.git
cd subatomic-agents

# For Raspberry Pi Zero
cargo build --release --target arm-unknown-linux-gnueabihf

# For x86_64
cargo build --release

# Run
./target/release/subatomic-agent --help
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SUB-ATOMIC AGENT SWARM                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Worker Agents (W)          Router Agents (R)              │
│   ┌─────────────────┐       ┌─────────────────┐             │
│   │  Ephemeral      │       │  Message        │             │
│   │  Single-task    │◄─────►│  Routing        │             │
│   │  <50MB RAM      │       │  Persistent     │             │
│   └─────────────────┘       └─────────────────┘             │
│           │                          │                       │
│           │   Gossip Protocol        │                       │
│           ▼                          ▼                       │
│   ┌─────────────────────────────────────────────┐            │
│   │           Mesh Network Layer                 │            │
│   │   WiFi Direct ◄──► Bluetooth ◄──► LoRa      │            │
│   └─────────────────────────────────────────────┘            │
│                        │                                     │
│                        ▼                                     │
│   ┌─────────────────────────────────────────────┐            │
│   │          Gateway Nodes (Internet)            │            │
│   │      Bridge to iHhashi Cloud API            │            │
│   └─────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Agent Types

| Type | RAM | Lifespan | Purpose |
|------|-----|----------|---------|
| **Worker (W)** | 50-100MB | 10-60s | Execute single micro-tasks |
| **Router (R)** | 80-120MB | Persistent | Route messages, maintain tables |
| **Consensus (C)** | 100-150MB | Persistent | Distributed consensus voting |
| **Inference (I)** | 150-300MB | Persistent | Run tiny LLMs locally |
| **Storage (S)** | 100-200MB | Persistent | Store CRDT data shards |

## Hardware Options

| Device | Cost (ZAR) | Cost (USD) | RAM | Power | Best For |
|--------|------------|------------|-----|-------|----------|
| Raspberry Pi Zero 2 W | R180 | $10 | 512MB | 2.5W | Worker, Router |
| Raspberry Pi Zero W | R150 | $8 | 512MB | 1.5W | Worker, Storage |
| Refurbished Android | R200-400 | $11-22 | 2-4GB | 5W | Inference, Router |
| ESP32-S3 | R80 | $4 | 512KB | 0.5W | Minimal Worker |
| Orange Pi Zero 2 | R200 | $11 | 512MB | 2W | Worker, Storage |

## Cost Analysis

### Per Agent (Monthly)

| Component | Cost (ZAR/month) | Cost (USD/month) |
|-----------|------------------|------------------|
| Electricity (2W avg) | R5 | $0.28 |
| Mobile data (100MB/day) | R30 | $1.67 |
| Hardware amortization | R8 | $0.44 |
| **Total** | **R43** | **$2.39** |

### Swarm Economics (1000 Agents)

| Metric | Traditional Cloud | Sub-Atomic Swarm | Savings |
|--------|-------------------|------------------|---------|
| Monthly cost | $5,000+ | $2,390 | **52%** |
| Offline capable | ❌ No | ✅ Yes | Critical |
| Fault tolerance | Limited | Extreme | High |
| Local latency | 50-200ms | 1-10ms | **95%** |

## Features

### ✅ Implemented

- [x] **Agent Lifecycle**: Spawn, execute, die in seconds
- [x] **Gossip Protocol**: Epidemic broadcast for P2P communication
- [x] **CRDTs**: Conflict-free replicated data types for offline sync
- [x] **Mesh Networking**: WiFi Direct, Bluetooth, LoRa support
- [x] **Lightweight Consensus**: Raft implementation for <100MB RAM
- [x] **Local Inference**: Tiny LLM support (Phi-2, TinyLlama)
- [x] **Reputation System**: Proof-of-work and proof-of-contribution
- [x] **iHhashi Integration**: Food delivery platform integration

### 🚧 In Progress

- [ ] **LoRa Mesh**: Long-range radio mesh backbone
- [ ] **Mobile App**: Android agent app
- [ ] **Quantum Dispatch**: D-Wave integration for route optimization
- [ ] **Auto-scaling**: Dynamic agent spawning based on load

## Project Structure

```
subatomic-agents/
├── core/              # Agent lifecycle and core types
│   ├── agent.rs       # Base agent trait
│   ├── lifecycle.rs   # Spawn/execute/die logic
│   └── swarm.rs       # Swarm coordination
├── protocols/         # Communication protocols
│   ├── gossip.rs      # Gossip protocol
│   └── crdt.rs        # CRDT implementations
├── networking/        # P2P networking
│   ├── mesh.rs        # Mesh network layer
│   ├── wifi_direct.rs # WiFi Direct implementation
│   └── bluetooth.rs   # Bluetooth mesh
├── consensus/         # Distributed consensus
│   └── raft.rs        # Lightweight Raft
├── inference/         # Local LLM inference
│   └── runtime.rs     # ONNX/llama.cpp wrapper
├── incentives/        # Economic incentives
│   └── reputation.rs  # Reputation system
├── integration/       # Platform integrations
│   └── ihhashi.rs     # iHhashi food delivery
├── examples/          # Example implementations
│   ├── pi_zero_worker/
│   ├── gateway_node/
│   └── inference_node/
└── docs/              # Documentation
```

## Usage Examples

### Validate Order

```rust
use subatomic_agents::integration::ihhashi::{IhhashiIntegration, IhhashiTask};

let result = integration.process_task(IhhashiTask::ValidateOrder {
    order_id: "ORD-123".to_string(),
    items: vec![
        OrderItem { product_id: "BUR-001".to_string(), quantity: 2, price: 65.0 },
    ],
}).await?;
```

### Calculate ETA with Route Memory

```rust
let result = integration.process_task(IhhashiTask::CalculateETA {
    pickup: Location { lat: -26.2, lng: 28.0, address: "Soweto Mall".to_string() },
    delivery: Location { lat: -26.25, lng: 28.05, address: "123 Vilakazi St".to_string() },
}).await?;

// Returns: { "eta_minutes": 15, "confidence": 0.8 }
```

### Run Local Inference

```rust
use subatomic_agents::inference::runtime::{LocalInferenceRuntime, InferenceTask};

let runtime = LocalInferenceRuntime::new(1, 512);

let result = runtime.infer(InferenceTask::Sentiment {
    text: "The food was amazing!".to_string(),
}).await?;

// result.output: "positive"
```

## Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment guides.

### Quick Deployment (Raspberry Pi)

```bash
# Flash SD card with Raspberry Pi OS Lite
# Enable SSH and WiFi

# SSH into Pi
ssh pi@raspberrypi.local

# Install subatomic-agent
curl -sSL https://get.ihhashi.co.za/subatomic | sudo sh

# Configure
sudo nano /etc/subatomic/config.toml

# Start service
sudo systemctl enable --now subatomic-agent

# Check status
sudo systemctl status subatomic-agent
```

## Monitoring

### Prometheus Metrics

```
subatomic_gossip_peers 42
subatomic_gossip_messages_seen 15234
subatomic_mesh_neighbors 8
subatomic_tasks_completed 892
subatomic_memory_usage_mb 45.2
```

### Grafana Dashboard

Import `docs/grafana-dashboard.json` for pre-built dashboards.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repo
git clone https://github.com/ihhashi/subatomic-agents.git
cd subatomic-agents

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Run tests
cargo test

# Run with logging
RUST_LOG=debug cargo run --example gateway_node
```

## Roadmap

### Phase 1: Foundation ✅
- [x] Core agent lifecycle
- [x] Gossip protocol
- [x] CRDTs
- [x] Basic mesh networking

### Phase 2: Production (Q1 2026)
- [ ] Full mesh networking (WiFi Direct, Bluetooth, LoRa)
- [ ] Raft consensus
- [ ] iHhashi integration complete
- [ ] Township pilot (Soweto)

### Phase 3: Scale (Q2 2026)
- [ ] Auto-scaling
- [ ] Quantum dispatch integration
- [ ] Mobile apps
- [ ] Multi-township deployment

### Phase 4: Intelligence (Q3 2026)
- [ ] Federated learning
- [ ] Predictive routing
- [ ] AI-powered optimization
- [ ] Cross-country expansion

## License

MIT License - See [LICENSE](LICENSE) for details.

Designed for the people of South Africa 🇿🇦

## Support

- 📖 Documentation: https://docs.ihhashi.co.za/subatomic
- 🐛 GitHub Issues: https://github.com/ihhashi/subatomic-agents/issues
- 💬 Telegram: https://t.me/ihhashi_dev
- 📧 Email: dev@ihhashi.co.za

## Acknowledgments

- [iHhashi](https://ihhashi.co.za) - Food delivery platform for South Africa
- [Rust](https://rust-lang.org) - For zero-cost abstractions and memory safety
- [libp2p](https://libp2p.io) - For P2P networking inspiration
- [CRDT.tech](https://crdt.tech) - For CRDT research and implementations

---

<p align="center">
  <strong>Built with ❤️ in South Africa</strong><br>
  Empowering townships through technology
</p>
