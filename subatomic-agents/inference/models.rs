// Model definitions and management

use serde::{Serialize, Deserialize};

/// Model format
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelFormat {
    /// ONNX format
    Onnx,
    /// GGUF format (llama.cpp)
    Gguf,
    /// PyTorch format
    Pytorch,
    /// TensorFlow format
    TensorFlow,
    /// SafeTensors format
    SafeTensors,
}

/// Model information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    /// Model ID
    pub id: String,
    /// Model name
    pub name: String,
    /// Model format
    pub format: ModelFormat,
    /// Model size in bytes
    pub size_bytes: u64,
    /// Number of parameters
    pub num_parameters: u64,
    /// Required RAM (MB)
    pub required_ram_mb: usize,
    /// Supported tasks
    pub supported_tasks: Vec<String>,
    /// Download URL
    pub download_url: Option<String>,
    /// Checksum
    pub checksum: Option<String>,
}

/// Model registry
pub struct ModelRegistry {
    models: Vec<ModelInfo>,
}

impl ModelRegistry {
    /// Create new model registry
    pub fn new() -> Self {
        Self {
            models: vec![
                ModelInfo {
                    id: "phi-2".to_string(),
                    name: "Microsoft Phi-2".to_string(),
                    format: ModelFormat::Gguf,
                    size_bytes: 1_600_000_000,
                    num_parameters: 2_700_000_000,
                    required_ram_mb: 2000,
                    supported_tasks: vec!["generate".to_string(), "embed".to_string()],
                    download_url: Some("https://huggingface.co/microsoft/phi-2".to_string()),
                    checksum: None,
                },
                ModelInfo {
                    id: "tinyllama".to_string(),
                    name: "TinyLlama 1.1B".to_string(),
                    format: ModelFormat::Gguf,
                    size_bytes: 600_000_000,
                    num_parameters: 1_100_000_000,
                    required_ram_mb: 800,
                    supported_tasks: vec!["generate".to_string(), "chat".to_string()],
                    download_url: Some("https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0".to_string()),
                    checksum: None,
                },
                ModelInfo {
                    id: "qwen2-0.5b".to_string(),
                    name: "Qwen2 0.5B".to_string(),
                    format: ModelFormat::Gguf,
                    size_bytes: 300_000_000,
                    num_parameters: 500_000_000,
                    required_ram_mb: 400,
                    supported_tasks: vec!["generate".to_string(), "classify".to_string()],
                    download_url: Some("https://huggingface.co/Qwen/Qwen2-0.5B-Instruct".to_string()),
                    checksum: None,
                },
            ],
        }
    }

    /// Get model by ID
    pub fn get_model(&self, id: &str) -> Option<&ModelInfo> {
        self.models.iter().find(|m| m.id == id)
    }

    /// Get models that fit in given RAM
    pub fn get_models_for_ram(&self, available_ram_mb: usize) -> Vec<&ModelInfo> {
        self.models
            .iter()
            .filter(|m| m.required_ram_mb <= available_ram_mb)
            .collect()
    }

    /// Get models supporting a task
    pub fn get_models_for_task(&self, task: &str) -> Vec<&ModelInfo> {
        self.models
            .iter()
            .filter(|m| m.supported_tasks.contains(&task.to_string()))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_registry() {
        let registry = ModelRegistry::new();

        let phi2 = registry.get_model("phi-2");
        assert!(phi2.is_some());
        assert_eq!(phi2.unwrap().required_ram_mb, 2000);

        let small_models = registry.get_models_for_ram(500);
        assert_eq!(small_models.len(), 1); // Only qwen2-0.5b
    }
}
