// Mesh Networking Layer - P2P Communication for Offline Operation
// Supports WiFi Direct, Bluetooth LE, and LoRa

use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::sync::{mpsc, RwLock};
use serde::{Serialize, Deserialize};

/// Maximum packet size (fit in single WiFi frame)
const MAX_PACKET_SIZE: usize = 1400;

/// Keep-alive interval
const KEEPALIVE_INTERVAL_SECS: u64 = 10;

/// Connection timeout
const CONNECTION_TIMEOUT_SECS: u64 = 30;

/// Transport types supported
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransportType {
    WiFiDirect,
    BluetoothLE,
    LoRa,
    TCP,
    WebRTC,
}

/// Mesh node address
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MeshAddress {
    WiFiDirect { mac: String, ip: Option<String> },
    BluetoothLE { mac: String },
    LoRa { node_id: u16 },
    TCP { addr: SocketAddr },
}

impl MeshAddress {
    pub fn transport_type(&self) -> TransportType {
        match self {
            MeshAddress::WiFiDirect { .. } => TransportType::WiFiDirect,
            MeshAddress::BluetoothLE { .. } => TransportType::BluetoothLE,
            MeshAddress::LoRa { .. } => TransportType::LoRa,
            MeshAddress::TCP { .. } => TransportType::TCP,
        }
    }

    pub fn to_string(&self) -> String {
        match self {
            MeshAddress::WiFiDirect { mac, ip } => {
                format!("wifi://{}@{}", mac, ip.as_deref().unwrap_or("?"))
            }
            MeshAddress::BluetoothLE { mac } => format!("ble://{}", mac),
            MeshAddress::LoRa { node_id } => format!("lora://{}", node_id),
            MeshAddress::TCP { addr } => format!("tcp://{}", addr),
        }
    }
}

/// Mesh packet
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshPacket {
    pub src: String,
    pub dst: Option<String>, // None = broadcast
    pub ttl: u8,
    pub payload: Vec<u8>,
    pub timestamp: u64,
}

impl MeshPacket {
    pub fn broadcast(src: String, payload: Vec<u8>) -> Self {
        Self {
            src,
            dst: None,
            ttl: 10,
            payload,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    pub fn unicast(src: String, dst: String, payload: Vec<u8>) -> Self {
        Self {
            src,
            dst: Some(dst),
            ttl: 10,
            payload,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    pub fn decrement_ttl(mut self) -> Option<Self> {
        if self.ttl > 0 {
            self.ttl -= 1;
            Some(self)
        } else {
            None
        }
    }
}

/// Neighbor information
#[derive(Debug, Clone)]
pub struct Neighbor {
    pub node_id: String,
    pub addresses: Vec<MeshAddress>,
    pub last_seen: std::time::Instant,
    pub rssi: i32, // Signal strength
    pub hop_count: u8,
}

impl Neighbor {
    pub fn is_alive(&self) -> bool {
        self.last_seen.elapsed().as_secs() < CONNECTION_TIMEOUT_SECS
    }
}

/// Routing table entry
#[derive(Debug, Clone)]
pub struct Route {
    pub dest: String,
    pub next_hop: String,
    pub hop_count: u8,
    pub metric: u32, // Lower is better
    pub last_updated: std::time::Instant,
}

/// Mesh network layer
pub struct MeshNetwork {
    node_id: String,
    neighbors: Arc<RwLock<HashMap<String, Neighbor>>>,
    routes: Arc<RwLock<HashMap<String, Route>>>,
    tx: mpsc::Sender<MeshPacket>,
    rx: mpsc::Receiver<MeshPacket>,
    listeners: Vec<Box<dyn TransportListener>>,
}

impl MeshNetwork {
    pub fn new(node_id: String) -> Self {
        let (tx, rx) = mpsc::channel(1000);

        Self {
            node_id,
            neighbors: Arc::new(RwLock::new(HashMap::new())),
            routes: Arc::new(RwLock::new(HashMap::new())),
            tx,
            rx,
            listeners: vec![],
        }
    }

    /// Start mesh network with TCP transport (for testing/development)
    pub async fn start_tcp(&mut self, bind_addr: SocketAddr) -> Result<(), MeshError> {
        let listener = TcpListener::bind(bind_addr).await?;
        log::info!("Mesh TCP listener started on {}", bind_addr);

        let node_id = self.node_id.clone();
        let tx = self.tx.clone();
        let neighbors = self.neighbors.clone();

        // Accept connections
        tokio::spawn(async move {
            loop {
                match listener.accept().await {
                    Ok((stream, addr)) => {
                        log::debug!("New connection from {}", addr);
                        let node_id = node_id.clone();
                        let tx = tx.clone();
                        let neighbors = neighbors.clone();

                        tokio::spawn(async move {
                            handle_tcp_connection(stream, addr, node_id, tx, neighbors).await;
                        });
                    }
                    Err(e) => {
                        log::error!("Accept error: {}", e);
                    }
                }
            }
        });

        // Start route maintenance
        self.start_route_maintenance().await;

        // Start packet processor
        self.start_packet_processor().await;

        Ok(())
    }

    /// Connect to a bootstrap peer
    pub async fn connect(&self, addr: SocketAddr) -> Result<(), MeshError> {
        let stream = TcpStream::connect(addr).await?;

        let node_id = self.node_id.clone();
        let tx = self.tx.clone();
        let neighbors = self.neighbors.clone();

        tokio::spawn(async move {
            handle_tcp_connection(stream, addr, node_id, tx, neighbors).await;
        });

        Ok(())
    }

    /// Send packet to destination
    pub async fn send(&self, packet: MeshPacket) -> Result<(), MeshError> {
        if let Some(dst) = &packet.dst {
            // Unicast - find route
            let routes = self.routes.read().await;
            if let Some(route) = routes.get(dst) {
                // Forward to next hop
                let neighbors = self.neighbors.read().await;
                if let Some(neighbor) = neighbors.get(&route.next_hop) {
                    // In real impl, would use actual transport
                    log::debug!("Routing packet to {} via {}", dst, route.next_hop);
                }
            } else {
                // No route - flood
                self.flood(packet).await?;
            }
        } else {
            // Broadcast - flood
            self.flood(packet).await?;
        }

        Ok(())
    }

    /// Flood packet to all neighbors
    async fn flood(&self, packet: MeshPacket) -> Result<(), MeshError> {
        let packet = match packet.decrement_ttl() {
            Some(p) => p,
            None => return Ok(()), // TTL expired
        };

        let neighbors = self.neighbors.read().await;
        for (node_id, neighbor) in neighbors.iter() {
            if packet.src == *node_id {
                continue; // Don't send back to source
            }

            // Send to neighbor (in real impl)
            log::debug!("Flooding packet to {}", node_id);
        }

        Ok(())
    }

    /// Receive packets
    pub async fn recv(&mut self) -> Option<MeshPacket> {
        self.rx.recv().await
    }

    /// Start route maintenance task
    async fn start_route_maintenance(&self) {
        let neighbors = self.neighbors.clone();
        let routes = self.routes.clone();
        let node_id = self.node_id.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(
                std::time::Duration::from_secs(KEEPALIVE_INTERVAL_SECS)
            );

            loop {
                interval.tick().await;

                // Send hello to all neighbors
                let neighbors_guard = neighbors.read().await;
                for (id, neighbor) in neighbors_guard.iter() {
                    if neighbor.is_alive() {
                        // Send hello packet
                        log::debug!("Sending hello to {}", id);
                    }
                }
                drop(neighbors_guard);

                // Update routes
                let mut routes_guard = routes.write().await;
                routes_guard.retain(|_, route| {
                    route.last_updated.elapsed().as_secs() < 300 // 5 min expiry
                });
            }
        });
    }

    /// Start packet processor
    async fn start_packet_processor(&mut self) {
        let mut rx = self.rx.resubscribe();
        let neighbors = self.neighbors.clone();
        let routes = self.routes.clone();
        let node_id = self.node_id.clone();
        let tx = self.tx.clone();

        tokio::spawn(async move {
            while let Some(packet) = rx.recv().await {
                // Update neighbor info
                {
                    let mut neighbors_guard = neighbors.write().await;
                    neighbors_guard.entry(packet.src.clone())
                        .and_modify(|n| {
                            n.last_seen = std::time::Instant::now();
                        });
                }

                // Update routing table
                {
                    let mut routes_guard = routes.write().await;
                    routes_guard.insert(packet.src.clone(), Route {
                        dest: packet.src.clone(),
                        next_hop: packet.src.clone(),
                        hop_count: 10 - packet.ttl,
                        metric: (10 - packet.ttl) as u32,
                        last_updated: std::time::Instant::now(),
                    });
                }

                // Check if packet is for us or needs forwarding
                if let Some(dst) = &packet.dst {
                    if dst == &node_id {
                        // Packet is for us - process it
                        log::debug!("Received packet for us from {}", packet.src);
                    } else {
                        // Forward to destination
                        let _ = tx.send(packet).await;
                    }
                } else {
                    // Broadcast - process and forward
                    log::debug!("Received broadcast from {}", packet.src);
                }
            }
        });
    }

    /// Get network topology info
    pub async fn get_topology(&self) -> NetworkTopology {
        NetworkTopology {
            node_id: self.node_id.clone(),
            neighbors: self.neighbors.read().await.len(),
            routes: self.routes.read().await.len(),
        }
    }
}

/// Handle incoming TCP connection
async fn handle_tcp_connection(
    mut stream: TcpStream,
    addr: SocketAddr,
    _node_id: String,
    tx: mpsc::Sender<MeshPacket>,
    neighbors: Arc<RwLock<HashMap<String, Neighbor>>>,
) {
    let mut buffer = [0u8; MAX_PACKET_SIZE];

    loop {
        // Read length prefix (4 bytes)
        let len = match stream.read_u32().await {
            Ok(len) => len as usize,
            Err(_) => break,
        };

        if len > MAX_PACKET_SIZE {
            log::error!("Packet too large: {} bytes", len);
            break;
        }

        // Read payload
        let mut payload = vec![0u8; len];
        if let Err(e) = stream.read_exact(&mut payload).await {
            log::error!("Read error: {}", e);
            break;
        }

        // Deserialize packet
        match bincode::deserialize::<MeshPacket>(&payload) {
            Ok(packet) => {
                // Update neighbor
                {
                    let mut neighbors_guard = neighbors.write().await;
                    neighbors_guard.entry(packet.src.clone())
                        .and_modify(|n| {
                            n.last_seen = std::time::Instant::now();
                        })
                        .or_insert_with(|| Neighbor {
                            node_id: packet.src.clone(),
                            addresses: vec![MeshAddress::TCP { addr }],
                            last_seen: std::time::Instant::now(),
                            rssi: -50,
                            hop_count: 1,
                        });
                }

                // Forward to mesh layer
                let _ = tx.send(packet).await;
            }
            Err(e) => {
                log::error!("Deserialize error: {}", e);
            }
        }
    }
}

/// Network topology info
#[derive(Debug, Clone)]
pub struct NetworkTopology {
    pub node_id: String,
    pub neighbors: usize,
    pub routes: usize,
}

/// Transport listener trait
#[async_trait::async_trait]
pub trait TransportListener: Send + Sync {
    async fn start(&mut self) -> Result<(), MeshError>;
    async fn stop(&mut self) -> Result<(), MeshError>;
}

/// Mesh errors
#[derive(Debug, thiserror::Error)]
pub enum MeshError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("No route to destination: {0}")]
    NoRoute(String),

    #[error("Transport error: {0}")]
    Transport(String),
}

/// WiFi Direct transport (Linux-specific)
#[cfg(target_os = "linux")]
pub mod wifi_direct {
    use super::*;

    /// Initialize WiFi Direct group owner
    pub async fn init_group_owner(interface: &str) -> Result<String, MeshError> {
        // Use wpa_supplicant or iwd to create P2P group
        // This is platform-specific and requires root
        log::info!("Initializing WiFi Direct on {}", interface);

        // Placeholder - actual implementation would use D-Bus or direct control
        Ok("192.168.49.1".to_string())
    }

    /// Discover peers
    pub async fn discover_peers(interface: &str) -> Result<Vec<String>, MeshError> {
        log::info!("Discovering WiFi Direct peers on {}", interface);
        Ok(vec![])
    }

    /// Connect to peer
    pub async fn connect_peer(interface: &str, peer_mac: &str) -> Result<String, MeshError> {
        log::info!("Connecting to WiFi Direct peer {}", peer_mac);
        Ok("192.168.49.2".to_string())
    }
}

/// Bluetooth LE transport
pub mod bluetooth {
    use super::*;

    /// Initialize BLE GATT server for mesh
    pub async fn init_ble_server() -> Result<(), MeshError> {
        log::info!("Initializing BLE mesh server");
        Ok(())
    }

    /// Scan for BLE mesh nodes
    pub async fn scan() -> Result<Vec<String>, MeshError> {
        log::info!("Scanning for BLE mesh nodes");
        Ok(vec![])
    }
}

/// LoRa transport
pub mod lora {
    use super::*;

    /// LoRa packet
    #[derive(Debug, Clone)]
    pub struct LoRaPacket {
        pub node_id: u16,
        pub payload: Vec<u8>,
        pub rssi: i32,
        pub snr: f32,
    }

    /// Initialize LoRa radio
    pub async fn init_lora() -> Result<(), MeshError> {
        log::info!("Initializing LoRa radio");
        // Would interface with SX1262 or similar
        Ok(())
    }

    /// Send packet over LoRa
    pub async fn send_lora(packet: &LoRaPacket) -> Result<(), MeshError> {
        log::debug!("Sending LoRa packet from node {}", packet.node_id);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mesh_packet() {
        let packet = MeshPacket::broadcast(
            "node1".to_string(),
            b"hello".to_vec()
        );

        assert_eq!(packet.src, "node1");
        assert!(packet.dst.is_none());
        assert_eq!(packet.ttl, 10);
    }

    #[test]
    fn test_mesh_address() {
        let addr = MeshAddress::TCP {
            addr: "127.0.0.1:8080".parse().unwrap()
        };

        assert_eq!(addr.to_string(), "tcp://127.0.0.1:8080");
        assert_eq!(addr.transport_type(), TransportType::TCP);
    }
}
