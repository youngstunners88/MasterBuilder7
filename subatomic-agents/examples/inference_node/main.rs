// Inference Node - Runs tiny LLMs for AI tasks
// Requires more RAM (2GB+) but can handle local AI inference

use subatomic_agents::inference::runtime::{
    LocalInferenceRuntime, InferenceTask, ModelType, ModelSize
};
use subatomic_agents::protocols::gossip::{GossipProtocol, MessagePayload};
use subatomic_agents::incentives::reputation::{ReputationSystem, ContributionProof};

use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();

    log::info!("╔══════════════════════════════════════════════════════════════╗");
    log::info!("║     iHhashi Sub-Atomic Agent - Inference Node                ║");
    log::info!("║     Local AI for offline operation                           ║");
    log::info!("╚══════════════════════════════════════════════════════════════╝");

    let node_id = gethostname::gethostname().to_string_lossy().to_string();
    log::info!("Inference Node ID: {}", node_id);

    // Check available memory
    let available_memory = get_available_memory_mb();
    log::info!("Available memory: {}MB", available_memory);

    // Determine which models we can run
    let supported_models = determine_supported_models(available_memory);
    log::info!("Supported models: {:?}", supported_models);

    // Initialize inference runtime
    let inference = Arc::new(LocalInferenceRuntime::new(1, available_memory));

    // Initialize gossip protocol
    let gossip = Arc::new(GossipProtocol::new(node_id.clone()));
    gossip.start().await;

    // Initialize reputation
    let reputation = Arc::new(ReputationSystem::new(30, 0.01));

    // Announce capabilities
    let capabilities = supported_models.iter()
        .map(|m| format!("{:?}", m))
        .collect::<Vec<_>>()
        .join(",");

    gossip.broadcast(MessagePayload::Heartbeat {
        node_id: node_id.clone(),
        capabilities: 0x02, // Inference capability
        agents_count: supported_models.len() as u32,
    }).await?;

    log::info!("Inference node ready. Capabilities: {}", capabilities);

    // Start inference task processor
    start_inference_processor(
        node_id.clone(),
        inference.clone(),
        gossip.clone(),
        reputation.clone(),
    ).await;

    // Keep running
    tokio::signal::ctrl_c().await?;
    log::info!("Shutting down...");

    Ok(())
}

/// Start processing inference tasks
async fn start_inference_processor(
    node_id: String,
    inference: Arc<LocalInferenceRuntime>,
    gossip: Arc<GossipProtocol>,
    reputation: Arc<ReputationSystem>,
) {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(1));

        loop {
            interval.tick().await;

            // Check for inference tasks in gossip
            // In production, would listen for specific task announcements

            // Simulate processing a task occasionally
            if rand::random::<f32>() < 0.1 {
                let task = InferenceTask::Sentiment {
                    text: "I love the food delivery service!".to_string()
                };

                if inference.can_handle(&task) {
                    match inference.infer(task).await {
                        Ok(result) => {
                            log::info!("Inference result: {}", result.output);

                            // Record contribution
                            let proof = ContributionProof::new(
                                node_id.clone(),
                                format!("infer-{}", uuid::Uuid::new_v4()),
                                "sentiment_analysis".to_string(),
                                result.inference_time_ms,
                                sha256(&result.output),
                            );

                            let rep = reputation.get_reputation(&node_id).await;
                            // rewards.reward(&proof, &rep).await;
                        }
                        Err(e) => {
                            log::error!("Inference failed: {}", e);
                        }
                    }
                }
            }
        }
    });
}

/// Get available memory in MB
fn get_available_memory_mb() -> usize {
    #[cfg(target_os = "linux")]
    {
        std::fs::read_to_string("/proc/meminfo")
            .ok()
            .and_then(|content| {
                content.lines()
                    .find(|line| line.starts_with("MemAvailable:"))
                    .and_then(|line| {
                        line.split_whitespace()
                            .nth(1)
                            .and_then(|v| v.parse::<usize>().ok())
                            .map(|kb| kb / 1024)
                    })
            })
            .unwrap_or(512) // Default to 512MB if unknown
    }
    #[cfg(not(target_os = "linux"))]
    {
        2048 // Assume 2GB on non-Linux
    }
}

/// Determine which models can run given available memory
fn determine_supported_models(available_mb: usize) -> Vec<ModelType> {
    let mut models = vec![];

    if available_mb >= ModelSize::Tiny.memory_requirement_mb() {
        models.push(ModelType::Qwen2HalfB);
    }

    if available_mb >= ModelSize::Small.memory_requirement_mb() {
        models.push(ModelType::TinyLlama);
        models.push(ModelType::StableLM2);
    }

    if available_mb >= ModelSize::Medium.memory_requirement_mb() {
        models.push(ModelType::Phi2);
        models.push(ModelType::Gemma2B);
    }

    models
}

/// Simple SHA256 hash
fn sha256(data: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    format!("{:x}", hasher.finalize())
}
