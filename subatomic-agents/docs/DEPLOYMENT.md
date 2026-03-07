# Sub-Atomic Agent Deployment Guide

## Quick Start

### Raspberry Pi Zero (Worker Node)

```bash
# 1. Flash Raspberry Pi OS Lite (64-bit)
# Download from: https://www.raspberrypi.com/software/operating-systems/

# 2. Enable SSH and WiFi before first boot
# Create wpa_supplicant.conf in boot partition:
cat > /boot/wpa_supplicant.conf << 'EOF'
country=ZA
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourWiFiName"
    psk="YourWiFiPassword"
}
EOF

# Create empty ssh file to enable SSH
touch /boot/ssh

# 3. Boot Pi and SSH in
ssh pi@raspberrypi.local

# 4. Install Rust (if building from source)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 5. Clone and build
git clone https://github.com/ihhashi/subatomic-agents.git
cd subatomic-agents
cargo build --release --target arm-unknown-linux-gnueabihf

# 6. Create systemd service
sudo tee /etc/systemd/system/subatomic-agent.service << 'EOF'
[Unit]
Description=Sub-Atomic Agent Worker
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/subatomic-agents
ExecStart=/home/pi/subatomic-agents/target/arm-unknown-linux-gnueabihf/release/pi_zero_worker
Restart=always
RestartSec=5
Environment=RUST_LOG=info

[Install]
WantedBy=multi-user.target
EOF

# 7. Enable and start service
sudo systemctl enable subatomic-agent
sudo systemctl start subatomic-agent

# 8. Check status
sudo systemctl status subatomic-agent
journalctl -u subatomic-agent -f
```

### Android Phone (Worker Node)

```bash
# Option 1: Termux (easiest)
# Install Termux from F-Droid

# In Termux:
pkg update
pkg install rust git

git clone https://github.com/ihhashi/subatomic-agents.git
cd subatomic-agents
cargo build --release

# Run agent
./target/release/android_agent
```

```kotlin
// Option 2: Native Android App
// See examples/android_agent/MainActivity.kt
// Build with Android Studio and sideload APK
```

### Gateway Node (Raspberry Pi 4 / Old Laptop)

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build gateway node
git clone https://github.com/ihhashi/subatomic-agents.git
cd subatomic-agents
cargo build --release --example gateway_node

# Configure environment
export IHHASHI_API=https://api.ihhashi.co.za
export MESH_PORT=8765
export METRICS_BIND=0.0.0.0:9090
export ADMIN_BIND=0.0.0.0:8080

# Run
./target/release/examples/gateway_node
```

## Network Configuration

### WiFi Direct (P2P)

```bash
# On Raspberry Pi
# Install wpa_supplicant with WiFi Direct support
sudo apt-get install -y wpasupplicant

# Start WiFi Direct group owner
sudo wpa_cli p2p_group_add
sudo wpa_cli p2p_group_owner

# Get P2P interface IP
ip addr show p2p-wlan0-0

# Other devices can now connect to this group
```

### Bluetooth Mesh

```bash
# Install BlueZ
sudo apt-get install -y bluez

# Enable BLE advertising
sudo hciconfig hci0 up
sudo hciconfig hci0 leadv 3

# Scan for peers
sudo hcitool lescan
```

### LoRa (Long Range)

```bash
# Requires SX1262 or similar radio module
# Connect via SPI or UART

# Install dependencies
sudo apt-get install -y python3-pip
pip3 install RPi.GPIO spidev

# Build LoRa driver
cd /home/pi/subatomic-agents
make lora-module
```

## Township Deployment Guide

### Site Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Gateway nodes | 1 per 1000 residents | 1 per 500 residents |
| Worker nodes | 10 per 1000 residents | 50 per 1000 residents |
| Power | 5W per node average | Solar + battery backup |
| Internet | 1 gateway with data | Multiple gateways |

### Example: Soweto Township Deployment

```
Population: ~1.3 million
Area: ~200 km²

Deployment Plan:
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   🏠 Gateway Nodes (50) - Schools, shops, community centers │
│   ├── Connected to internet (4G/5G or fiber)               │
│   ├── Raspberry Pi 4 or old laptops                        │
│   └── Run full stack + API bridge                          │
│                                                              │
│   📱 Worker Nodes (2,600) - Old phones, Pi Zeros           │
│   ├── Distributed throughout neighborhood                  │
│   ├── Battery or solar powered                             │
│   └── Run lightweight agents                               │
│                                                              │
│   🔗 Mesh Network                                           │
│   ├── WiFi Direct for local clusters                       │
│   ├── Bluetooth for close proximity                        │
│   └── LoRa for long-range backbone                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Cost Estimate:
- Gateway nodes: 50 × R800 = R40,000
- Worker nodes: 2,600 × R200 = R520,000
- Networking equipment: R50,000
- Solar panels + batteries: R100,000
- Total: ~R710,000 ($39,000 USD)

Per capita cost: R0.55 ($0.03 USD)
```

## Monitoring

### Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'subatomic-agents'
    static_configs:
      - targets:
        - 'gateway-1.local:9090'
        - 'gateway-2.local:9090'
        - 'gateway-3.local:9090'
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Sub-Atomic Agent Swarm",
    "panels": [
      {
        "title": "Active Nodes",
        "targets": [
          {
            "expr": "subatomic_gossip_peers"
          }
        ]
      },
      {
        "title": "Network Traffic",
        "targets": [
          {
            "expr": "rate(subatomic_gossip_bytes_sent[5m])"
          }
        ]
      },
      {
        "title": "Task Completion Rate",
        "targets": [
          {
            "expr": "rate(subatomic_tasks_completed[5m])"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting

### High Memory Usage

```bash
# Check memory usage
free -h
cat /proc/meminfo

# Enable swap if needed
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Restart agent
sudo systemctl restart subatomic-agent
```

### Network Issues

```bash
# Check mesh connectivity
subatomic-cli mesh status

# View routing table
subatomic-cli mesh routes

# Test connectivity to peer
subatomic-cli mesh ping <peer-id>

# Restart mesh
sudo systemctl restart subatomic-mesh
```

### Sync Issues with iHhashi API

```bash
# Check API connectivity
curl https://api.ihhashi.co.za/health

# View sync queue
subatomic-cli sync queue

# Force sync
subatomic-cli sync now

# View logs
journalctl -u subatomic-agent --since "1 hour ago"
```

## Security

### Firewall Configuration

```bash
# Allow mesh ports
sudo ufw allow 8765/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 9090/tcp

# Rate limit
sudo ufw limit 8765/tcp

# Enable firewall
sudo ufw enable
```

### Encryption Keys

```bash
# Generate node keypair
subatomic-cli keys generate

# Backup keys
cp ~/.subatomic/keys/node.key /backup/

# Rotate keys monthly
subatomic-cli keys rotate
```

## Updates

### Automated Updates

```bash
# Create update script
sudo tee /usr/local/bin/update-subatomic.sh << 'EOF'
#!/bin/bash
cd /home/pi/subatomic-agents
git pull origin main
cargo build --release --target arm-unknown-linux-gnueabihf
sudo systemctl restart subatomic-agent
EOF

sudo chmod +x /usr/local/bin/update-subatomic.sh

# Add to crontab (weekly updates)
0 3 * * 0 /usr/local/bin/update-subatomic.sh >> /var/log/subatomic-update.log 2>&1
```

## Cost Analysis

### Monthly Operating Costs (Per Node)

| Component | Pi Zero | Pi 4 | Android Phone |
|-----------|---------|------|---------------|
| Electricity | R5 | R15 | R10 |
| Data (100MB/day) | R30 | R50 | R30 |
| Maintenance | R2 | R5 | R2 |
| **Total** | **R37** | **R70** | **R42** |

### Total Cost of Ownership (3 years)

| Deployment Size | Hardware | Operating | Total |
|-----------------|----------|-----------|-------|
| Small (100 nodes) | R20,000 | R133,200 | R153,200 |
| Medium (1000 nodes) | R200,000 | R1,332,000 | R1,532,000 |
| Large (5000 nodes) | R1,000,000 | R6,660,000 | R7,660,000 |

### Comparison: Cloud vs Sub-Atomic Swarm

| Metric | Cloud (AWS) | Sub-Atomic Swarm | Savings |
|--------|-------------|------------------|---------|
| 1000 agents/month | $5,000 | $2,390 | 52% |
| 3-year TCO | $180,000 | $85,000 | 53% |
| Offline capable | No | Yes | N/A |
| Local latency | 50-200ms | 1-10ms | 95% |
| Community owned | No | Yes | N/A |

## Support

- Documentation: https://docs.ihhashi.co.za/subatomic
- GitHub Issues: https://github.com/ihhashi/subatomic-agents/issues
- Telegram: https://t.me/ihhashi_dev
- Email: dev@ihhashi.co.za
