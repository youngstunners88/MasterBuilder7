// Gateway Node - Bridges mesh network to internet/iHhashi API
// Runs on more capable hardware (Raspberry Pi 4, old laptop, etc.)

use subatomic_agents::core::agent::{Agent, AgentConfig, AgentType, Task};
use subatomic_agents::protocols::gossip::{GossipProtocol, MessagePayload};
use subatomic_agents::networking::mesh::{MeshNetwork, MeshPacket};
use subatomic_agents::integration::ihhashi::IhhashiIntegration;
use subatomic_agents::inference::runtime::LocalInferenceRuntime;
use subatomic_agents::incentives::reputation::{ReputationSystem, RewardSystem};
use subatomic_agents::consensus::raft::RaftNode;

use std::sync::Arc;
use tokio::sync::RwLock;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();

    log::info!("╔══════════════════════════════════════════════════════════════╗");
    log::info!("║     iHhashi Sub-Atomic Agent - Gateway Node                  ║");
    log::info!("║     Bridging mesh network to iHhashi cloud                   ║");
    log::info!("╚══════════════════════════════════════════════════════════════╝");

    let node_id = gethostname::gethostname().to_string_lossy().to_string();
    log::info!("Gateway Node ID: {}", node_id);

    // Parse configuration
    let api_endpoint = std::env::var("IHHASHI_API")
        .unwrap_or_else(|_| "https://api.ihhashi.co.za".to_string());

    let mesh_port = std::env::var("MESH_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8765);

    // Initialize components
    log::info!("Initializing gossip protocol...");
    let gossip = Arc::new(GossipProtocol::new(node_id.clone()));
    gossip.start().await;

    log::info!("Initializing mesh network on port {}...", mesh_port);
    let mesh = Arc::new(RwLock::new(MeshNetwork::new(node_id.clone())));
    mesh.write().await.start_tcp(format!("0.0.0.0:{}", mesh_port).parse()?).await?;

    log::info!("Initializing inference runtime...");
    let inference = Arc::new(LocalInferenceRuntime::new(2, 1024));

    log::info!("Initializing reputation system...");
    let reputation = Arc::new(ReputationSystem::new(30, 0.01));

    log::info!("Initializing reward system...");
    let rewards = Arc::new(RewardSystem::new(0.001));

    log::info!("Initializing iHhashi integration...");
    let integration = Arc::new(IhhashiIntegration::new(
        node_id.clone(),
        gossip.clone(),
        mesh.clone(),
        inference.clone(),
        reputation.clone(),
        rewards.clone(),
        Some(api_endpoint.clone()),
    ));

    integration.start().await;

    log::info!("Gateway node initialized successfully!");
    log::info!("API Endpoint: {}", api_endpoint);
    log::info!("Mesh Port: {}", mesh_port);

    // Start bridge tasks
    let bridge_handle = start_api_bridge(
        gossip.clone(),
        mesh.clone(),
        integration.clone(),
        api_endpoint.clone(),
    );

    // Start metrics exporter
    let metrics_handle = start_metrics_exporter(
        gossip.clone(),
        mesh.clone(),
        reputation.clone(),
    );

    // Start admin API
    let admin_handle = start_admin_api(
        gossip.clone(),
        mesh.clone(),
        integration.clone(),
    );

    // Wait for all tasks
    tokio::try_join!(bridge_handle, metrics_handle, admin_handle)?;

    Ok(())
}

/// Bridge mesh messages to/from iHhashi API
async fn start_api_bridge(
    gossip: Arc<GossipProtocol>,
    mesh: Arc<RwLock<MeshNetwork>>,
    integration: Arc<IhhashiIntegration>,
    api_endpoint: String,
) -> Result<(), Box<dyn std::error::Error>> {
    log::info!("Starting API bridge...");

    // Create HTTP client
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()?;

    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;

        // Check internet connectivity
        let has_internet = check_internet().await;

        if has_internet {
            // Sync with iHhashi API
            if let Err(e) = integration.sync_with_api().await {
                log::warn!("API sync failed: {}", e);
            }

            // Forward queued messages
            // In production, would maintain a queue of messages to forward
        } else {
            log::debug!("No internet connection, operating in offline mode");
        }

        // Get mesh topology
        let topology = mesh.read().await.get_topology().await;
        log::debug!("Mesh topology: {} neighbors, {} routes",
            topology.neighbors, topology.routes);
    }
}

/// Check internet connectivity
async fn check_internet() -> bool {
    match tokio::time::timeout(
        std::time::Duration::from_secs(5),
        reqwest::get("https://1.1.1.1")
    ).await {
        Ok(Ok(_)) => true,
        _ => false,
    }
}

/// Export metrics for monitoring
async fn start_metrics_exporter(
    gossip: Arc<GossipProtocol>,
    mesh: Arc<RwLock<MeshNetwork>>,
    reputation: Arc<ReputationSystem>,
) -> Result<(), Box<dyn std::error::Error>> {
    let bind_addr = std::env::var("METRICS_BIND")
        .unwrap_or_else(|_| "0.0.0.0:9090".to_string());

    log::info!("Starting metrics exporter on {}...", bind_addr);

    let app = axum::Router::new()
        .route("/metrics", axum::routing::get({
            let gossip = gossip.clone();
            let mesh = mesh.clone();

            move || {
                let gossip = gossip.clone();
                let mesh = mesh.clone();

                async move {
                    let gossip_stats = gossip.get_stats().await;
                    let topology = mesh.read().await.get_topology().await;

                    let output = format!(
                        "# Sub-Atomic Agent Gateway Metrics\n\
                         subatomic_gossip_peers {}\n\
                         subatomic_gossip_messages_seen {}\n\
                         subatomic_gossip_bytes_sent {}\n\
                         subatomic_gossip_bytes_received {}\n\
                         subatomic_mesh_neighbors {}\n\
                         subatomic_mesh_routes {}\n",
                        gossip_stats.peers_count,
                        gossip_stats.messages_seen,
                        gossip_stats.bytes_sent,
                        gossip_stats.bytes_received,
                        topology.neighbors,
                        topology.routes,
                    );

                    ([("content-type", "text/plain")], output)
                }
            }
        }))
        .route("/health", axum::routing::get(|| async {
            axum::Json(serde_json::json!({
                "status": "healthy",
                "timestamp": std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs()
            }))
        }));

    let listener = tokio::net::TcpListener::bind(&bind_addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Admin API for managing the gateway
async fn start_admin_api(
    gossip: Arc<GossipProtocol>,
    mesh: Arc<RwLock<MeshNetwork>>,
    integration: Arc<IhhashiIntegration>,
) -> Result<(), Box<dyn std::error::Error>> {
    let bind_addr = std::env::var("ADMIN_BIND")
        .unwrap_or_else(|_| "0.0.0.0:8080".to_string());

    log::info!("Starting admin API on {}...", bind_addr);

    let app = axum::Router::new()
        .route("/status", axum::routing::get({
            let gossip = gossip.clone();
            let mesh = mesh.clone();

            move || {
                let gossip = gossip.clone();
                let mesh = mesh.clone();

                async move {
                    let gossip_stats = gossip.get_stats().await;
                    let topology = mesh.read().await.get_topology().await;

                    axum::Json(serde_json::json!({
                        "status": "operational",
                        "gossip": {
                            "peers": gossip_stats.peers_count,
                            "messages_seen": gossip_stats.messages_seen,
                            "bytes_sent": gossip_stats.bytes_sent,
                            "bytes_received": gossip_stats.bytes_received,
                        },
                        "mesh": {
                            "neighbors": topology.neighbors,
                            "routes": topology.routes,
                        }
                    }))
                }
            }
        }))
        .route("/broadcast", axum::routing::post({
            let gossip = gossip.clone();

            move |axum::Json(payload): axum::Json<serde_json::Value>| {
                let gossip = gossip.clone();

                async move {
                    // Parse and broadcast message
                    let msg_type = payload.get("message_type")
                        .and_then(|v| v.as_str())
                        .unwrap_or("custom");

                    let custom_payload = MessagePayload::Custom {
                        app_id: "admin".to_string(),
                        data: serde_json::to_vec(&payload).unwrap_or_default(),
                    };

                    match gossip.broadcast(custom_payload).await {
                        Ok(_) => axum::Json(serde_json::json!({
                            "status": "broadcasted",
                            "message_type": msg_type
                        })),
                        Err(e) => axum::Json(serde_json::json!({
                            "status": "error",
                            "error": e.to_string()
                        }))
                    }
                }
            }
        }));

    let listener = tokio::net::TcpListener::bind(&bind_addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
