// Sub-Atomic Agent - Raspberry Pi Zero Worker
// Minimal resource usage for $5 devices

use subatomic_agents::core::agent::{WorkerAgent, AgentConfig, AgentType, Task};
use subatomic_agents::protocols::gossip::GossipProtocol;
use subatomic_agents::networking::mesh::MeshNetwork;
use subatomic_agents::incentives::reputation::{ReputationSystem, RewardSystem};

use std::sync::Arc;
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    env_logger::init();

    log::info!("Starting Sub-Atomic Agent on Raspberry Pi Zero...");

    // Get node ID from hostname or generate
    let node_id = gethostname::gethostname()
        .to_string_lossy()
        .to_string();

    log::info!("Node ID: {}", node_id);

    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();
    let mesh_id = args.get(1).cloned().unwrap_or_else(|| "township-alpha".to_string());
    let bootstrap = args.get(2).cloned();

    // Create agent configuration
    let config = AgentConfig {
        agent_type: AgentType::Worker,
        mesh_id: mesh_id.clone(),
        bootstrap_peers: bootstrap.into_iter().collect(),
        max_tasks: 100,
        task_timeout_secs: 30, // Short timeout for Pi Zero
        enable_metrics: true,
    };

    // Initialize gossip protocol
    let gossip = Arc::new(GossipProtocol::new(node_id.clone()));
    gossip.start().await;

    // Initialize mesh network
    let mesh = Arc::new(tokio::sync::RwLock::new(MeshNetwork::new(node_id.clone())));

    // Start TCP listener for mesh (port 8765)
    mesh.write().await.start_tcp("0.0.0.0:8765".parse()?).await?;

    // Connect to bootstrap if provided
    if let Some(bootstrap_addr) = bootstrap {
        log::info!("Connecting to bootstrap: {}", bootstrap_addr);
        if let Ok(addr) = bootstrap_addr.parse() {
            mesh.read().await.connect(addr).await?;
        }
    }

    // Initialize reputation and reward systems
    let reputation = Arc::new(ReputationSystem::new(30, 0.01));
    let rewards = Arc::new(RewardSystem::new(0.001));

    // Create worker agent
    let mut worker = WorkerAgent::new(config);
    worker.initialize().await?;

    log::info!("Worker agent initialized and ready");

    // Task processing loop
    let mut task_rx = create_task_receiver().await?;

    loop {
        // Check memory usage
        if let Some(mem_mb) = get_memory_usage() {
            if mem_mb > 80.0 {
                log::warn!("Memory usage high: {:.1}MB", mem_mb);
                // Force GC or restart
                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
            }
        }

        // Wait for task with timeout
        match tokio::time::timeout(
            tokio::time::Duration::from_secs(5),
            task_rx.recv()
        ).await {
            Ok(Some(task)) => {
                log::info!("Received task: {}", task.task_type);

                // Execute task
                let result = worker.execute_task(task).await?;

                // Record result
                reputation.record_task_completion(
                    &node_id,
                    result.success,
                    10
                ).await;

                log::info!("Task completed: success={}, time={}ms",
                    result.success, result.execution_time_ms);

                // Worker dies after task - recreate
                worker = WorkerAgent::new(AgentConfig {
                    agent_type: AgentType::Worker,
                    mesh_id: mesh_id.clone(),
                    bootstrap_peers: vec![],
                    max_tasks: 100,
                    task_timeout_secs: 30,
                    enable_metrics: true,
                });
                worker.initialize().await?;
            }
            Ok(None) => {
                // Channel closed
                break;
            }
            Err(_) => {
                // Timeout - check heartbeat
                log::debug!("No tasks received, sending heartbeat...");
            }
        }

        // Periodic stats logging
        let stats = gossip.get_stats().await;
        log::debug!("Network stats: {} peers, {} messages seen",
            stats.peers_count, stats.messages_seen);
    }

    // Graceful shutdown
    log::info!("Shutting down...");
    worker.shutdown().await?;

    Ok(())
}

/// Get current memory usage in MB (Linux only)
fn get_memory_usage() -> Option<f32> {
    #[cfg(target_os = "linux")]
    {
        std::fs::read_to_string("/proc/self/status")
            .ok()
            .and_then(|content| {
                content.lines()
                    .find(|line| line.starts_with("VmRSS:"))
                    .and_then(|line| {
                        line.split_whitespace()
                            .nth(1)
                            .and_then(|v| v.parse::<f32>().ok())
                            .map(|kb| kb / 1024.0)
                    })
            })
    }
    #[cfg(not(target_os = "linux"))]
    {
        None
    }
}

/// Create task receiver
async fn create_task_receiver() -> Result<mpsc::Receiver<Task>, Box<dyn std::error::Error>> {
    // In production, would listen on Unix socket or HTTP
    let (tx, rx) = mpsc::channel(100);

    // Spawn HTTP listener for task submission
    tokio::spawn(async move {
        let app = axum::Router::new()
            .route("/task", axum::routing::post({
                let tx = tx.clone();
                move |axum::Json(payload): axum::Json<serde_json::Value>| async move {
                    let task = Task::new(
                        payload.get("type").and_then(|v| v.as_str()).unwrap_or("echo"),
                        serde_json::to_vec(&payload).unwrap_or_default()
                    );
                    let _ = tx.send(task).await;
                    axum::Json(serde_json::json!({"status": "queued"}))
                }
            }));

        let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
        axum::serve(listener, app).await.unwrap();
    });

    Ok(rx)
}
