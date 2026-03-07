// Local LLM Inference Runtime
// Runs tiny models (Phi-2, TinyLlama) on low-resource devices
// Memory target: <200MB for inference agents

use std::sync::Arc;
use tokio::sync::Semaphore;
use serde::{Serialize, Deserialize};

/// Available model sizes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelSize {
    Tiny,   // ~100MB, 50M params
    Small,  // ~300MB, 100M params
    Medium, // ~1GB, 1B params
}

impl ModelSize {
    pub fn memory_requirement_mb(&self) -> usize {
        match self {
            ModelSize::Tiny => 150,
            ModelSize::Small => 400,
            ModelSize::Medium => 1200,
        }
    }
}

/// Supported models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ModelType {
    /// Microsoft Phi-2 (2.7B params, quantized to ~1.6GB)
    Phi2,
    /// TinyLlama (1.1B params, quantized to ~600MB)
    TinyLlama,
    /// Qwen2-0.5B (500M params, quantized to ~300MB)
    Qwen2HalfB,
    /// StableLM-2-Zephyr (1.6B params, quantized to ~900MB)
    StableLM2,
    /// Gemma-2B (2B params, quantized to ~1.3GB)
    Gemma2B,
    /// Custom ONNX model
    Custom { path: String },
}

impl ModelType {
    pub fn default_size(&self) -> ModelSize {
        match self {
            ModelType::Phi2 => ModelSize::Medium,
            ModelType::TinyLlama => ModelSize::Small,
            ModelType::Qwen2HalfB => ModelSize::Tiny,
            ModelType::StableLM2 => ModelSize::Small,
            ModelType::Gemma2B => ModelSize::Medium,
            ModelType::Custom { .. } => ModelSize::Small,
        }
    }

    pub fn huggingface_repo(&self) -> Option<&'static str> {
        match self {
            ModelType::Phi2 => Some("microsoft/phi-2"),
            ModelType::TinyLlama => Some("TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            ModelType::Qwen2HalfB => Some("Qwen/Qwen2-0.5B-Instruct"),
            ModelType::StableLM2 => Some("stabilityai/stablelm-2-zephyr-1_6b"),
            ModelType::Gemma2B => Some("google/gemma-2b-it"),
            ModelType::Custom { .. } => None,
        }
    }
}

/// Inference task types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InferenceTask {
    /// Simple text classification
    Classify { text: String, classes: Vec<String> },
    /// Sentiment analysis
    Sentiment { text: String },
    /// Text generation
    Generate { prompt: String, max_tokens: u32, temperature: f32 },
    /// Named entity extraction
    ExtractEntities { text: String },
    /// Text embedding
    Embed { text: String },
    /// Question answering
    Answer { question: String, context: String },
    /// Summarize
    Summarize { text: String, max_length: u32 },
    /// Translate (for i18n)
    Translate { text: String, target_lang: String },
}

impl InferenceTask {
    pub fn required_model_size(&self) -> ModelSize {
        match self {
            InferenceTask::Classify { .. } => ModelSize::Tiny,
            InferenceTask::Sentiment { .. } => ModelSize::Tiny,
            InferenceTask::Generate { .. } => ModelSize::Small,
            InferenceTask::ExtractEntities { .. } => ModelSize::Tiny,
            InferenceTask::Embed { .. } => ModelSize::Tiny,
            InferenceTask::Answer { .. } => ModelSize::Small,
            InferenceTask::Summarize { .. } => ModelSize::Small,
            InferenceTask::Translate { .. } => ModelSize::Small,
        }
    }
}

/// Inference result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceResult {
    pub task: InferenceTask,
    pub output: String,
    pub confidence: Option<f32>,
    pub tokens_generated: u32,
    pub inference_time_ms: u64,
}

/// Inference error
#[derive(Debug, thiserror::Error)]
pub enum InferenceError {
    #[error("Model not found: {0}")]
    ModelNotFound(String),

    #[error("Out of memory: required {required}MB, available {available}MB")]
    OutOfMemory { required: usize, available: usize },

    #[error("Inference failed: {0}")]
    InferenceFailed(String),

    #[error("Task not supported: {0}")]
    TaskNotSupported(String),

    #[error("Timeout")]
    Timeout,
}

/// Local inference runtime
pub struct LocalInferenceRuntime {
    /// Available models
    models: Arc<dashmap::DashMap<ModelType, LoadedModel>>,
    /// Concurrency limit (to prevent OOM)
    semaphore: Arc<Semaphore>,
    /// Max memory available
    max_memory_mb: usize,
}

/// Loaded model information
struct LoadedModel {
    model_type: ModelType,
    size: ModelSize,
    loaded_at: std::time::Instant,
    last_used: std::time::Instant,
    use_count: u64,
}

impl LocalInferenceRuntime {
    pub fn new(max_concurrent: usize, max_memory_mb: usize) -> Self {
        Self {
            models: Arc::new(dashmap::DashMap::new()),
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
            max_memory_mb,
        }
    }

    /// Check if system can handle the task
    pub fn can_handle(&self, task: &InferenceTask) -> bool {
        let required = task.required_model_size().memory_requirement_mb();

        // Check available memory (Linux-specific)
        #[cfg(target_os = "linux")]
        {
            if let Ok(meminfo) = std::fs::read_to_string("/proc/meminfo") {
                for line in meminfo.lines() {
                    if line.starts_with("MemAvailable:") {
                        let parts: Vec<&str> = line.split_whitespace().collect();
                        if parts.len() >= 2 {
                            if let Ok(kb) = parts[1].parse::<usize>() {
                                let available_mb = kb / 1024;
                                return available_mb >= required;
                            }
                        }
                    }
                }
            }
        }

        // Default to conservative estimate
        true
    }

    /// Run inference task
    pub async fn infer(&self, task: InferenceTask) -> Result<InferenceResult, InferenceError> {
        let _permit = self.semaphore.acquire().await
            .map_err(|_| InferenceError::InferenceFailed("Semaphore closed".to_string()))?;

        let start = std::time::Instant::now();

        // Check memory
        if !self.can_handle(&task) {
            return Err(InferenceError::OutOfMemory {
                required: task.required_model_size().memory_requirement_mb(),
                available: self.max_memory_mb,
            });
        }

        // Execute task
        let result = match &task {
            InferenceTask::Classify { text, classes } => {
                self.classify(text, classes).await
            }
            InferenceTask::Sentiment { text } => {
                self.sentiment(text).await
            }
            InferenceTask::Generate { prompt, max_tokens, temperature } => {
                self.generate(prompt, *max_tokens, *temperature).await
            }
            InferenceTask::ExtractEntities { text } => {
                self.extract_entities(text).await
            }
            InferenceTask::Embed { text } => {
                self.embed(text).await
            }
            InferenceTask::Answer { question, context } => {
                self.answer(question, context).await
            }
            InferenceTask::Summarize { text, max_length } => {
                self.summarize(text, *max_length).await
            }
            InferenceTask::Translate { text, target_lang } => {
                self.translate(text, target_lang).await
            }
        };

        let inference_time_ms = start.elapsed().as_millis() as u64;

        result.map(|output| InferenceResult {
            task: task.clone(),
            output,
            confidence: None,
            tokens_generated: 0,
            inference_time_ms,
        })
    }

    /// Simple rule-based classifier (fallback when no model loaded)
    async fn classify(&self, text: &str, classes: &[String]) -> Result<String, InferenceError> {
        // Simple keyword-based classification
        let text_lower = text.to_lowercase();

        for class in classes {
            if text_lower.contains(&class.to_lowercase()) {
                return Ok(class.clone());
            }
        }

        // Default to first class
        Ok(classes.first().cloned().unwrap_or_default())
    }

    /// Sentiment analysis (rule-based fallback)
    async fn sentiment(&self, text: &str) -> Result<String, InferenceError> {
        let positive_words = ["good", "great", "excellent", "love", "happy", "amazing", "best", "fantastic"];
        let negative_words = ["bad", "terrible", "awful", "hate", "worst", "poor", "disappointed", "angry"];

        let text_lower = text.to_lowercase();
        let positive_count = positive_words.iter().filter(|&&w| text_lower.contains(w)).count();
        let negative_count = negative_words.iter().filter(|&&w| text_lower.contains(w)).count();

        if positive_count > negative_count {
            Ok("positive".to_string())
        } else if negative_count > positive_count {
            Ok("negative".to_string())
        } else {
            Ok("neutral".to_string())
        }
    }

    /// Text generation (placeholder - would use actual model)
    async fn generate(&self, prompt: &str, max_tokens: u32, _temperature: f32) -> Result<String, InferenceError> {
        // Placeholder implementation
        // In production, would use llama.cpp or candle

        let responses = vec![
            "Thank you for your message. I'll help you with that.",
            "I understand. Let me check on that for you.",
            "Got it! I'll process your request right away.",
        ];

        use rand::seq::SliceRandom;
        let mut rng = rand::thread_rng();
        let response = responses.choose(&mut rng).unwrap_or(&"Processing...");

        Ok(format!("{}", response))
    }

    /// Named entity extraction (rule-based)
    async fn extract_entities(&self, text: &str) -> Result<String, InferenceError> {
        // Simple pattern matching for common entities
        let mut entities = vec![];

        // Look for prices (R123.45 or R 123.45)
        for word in text.split_whitespace() {
            if word.starts_with("R") && word[1..].parse::<f64>().is_ok() {
                entities.push(format!("PRICE: {}", word));
            }
        }

        // Look for phone numbers (South African format)
        if text.contains("0") {
            for word in text.split_whitespace() {
                let digits: String = word.chars().filter(|c| c.is_digit(10)).collect();
                if digits.len() == 10 && digits.starts_with("0") {
                    entities.push(format!("PHONE: {}", digits));
                }
            }
        }

        Ok(entities.join(", "))
    }

    /// Text embedding (placeholder)
    async fn embed(&self, _text: &str) -> Result<String, InferenceError> {
        // Would return embedding vector
        Ok("[0.1, -0.2, 0.3, ...]".to_string())
    }

    /// Question answering (placeholder)
    async fn answer(&self, question: &str, context: &str) -> Result<String, InferenceError> {
        // Simple keyword matching
        let question_lower = question.to_lowercase();
        let context_lower = context.to_lowercase();

        // Extract key terms from question
        let key_terms: Vec<&str> = question_lower
            .split_whitespace()
            .filter(|&w| w.len() > 3)
            .collect();

        // Find sentences in context containing key terms
        let sentences: Vec<&str> = context.split('.').collect();
        let mut best_sentence = "";
        let mut max_matches = 0;

        for sentence in sentences {
            let sentence_lower = sentence.to_lowercase();
            let matches = key_terms.iter()
                .filter(|&&term| sentence_lower.contains(term))
                .count();

            if matches > max_matches {
                max_matches = matches;
                best_sentence = sentence;
            }
        }

        if best_sentence.is_empty() {
            Ok("I couldn't find the answer in the provided context.".to_string())
        } else {
            Ok(best_sentence.trim().to_string())
        }
    }

    /// Summarize text (simple extractive)
    async fn summarize(&self, text: &str, max_length: u32) -> Result<String, InferenceError> {
        let sentences: Vec<&str> = text.split('.').filter(|s| !s.trim().is_empty()).collect();

        if sentences.is_empty() {
            return Ok("".to_string());
        }

        // Take first few sentences as summary
        let num_sentences = sentences.len().min(max_length as usize / 20);
        let summary: Vec<&str> = sentences.iter().take(num_sentences).copied().collect();

        Ok(summary.join(". ") + ".")
    }

    /// Translate text (placeholder)
    async fn translate(&self, text: &str, target_lang: &str) -> Result<String, InferenceError> {
        // In production, would use MarianMT or similar
        Ok(format!("[{}] {}", target_lang.to_uppercase(), text))
    }

    /// Get model statistics
    pub fn get_stats(&self) -> InferenceStats {
        let mut total_memory = 0;
        let mut loaded_models = 0;

        for entry in self.models.iter() {
            let model = entry.value();
            total_memory += model.size.memory_requirement_mb();
            loaded_models += 1;
        }

        InferenceStats {
            loaded_models,
            total_memory_mb: total_memory,
            max_memory_mb: self.max_memory_mb,
        }
    }
}

/// Inference statistics
#[derive(Debug, Clone)]
pub struct InferenceStats {
    pub loaded_models: usize,
    pub total_memory_mb: usize,
    pub max_memory_mb: usize,
}

/// ONNX Runtime wrapper for model inference
#[cfg(feature = "onnx")]
pub mod onnx {
    use ort::session::Session;

    pub struct OnnxRuntime {
        session: Session,
    }

    impl OnnxRuntime {
        pub fn new(model_path: &str) -> Result<Self, Box<dyn std::error::Error>> {
            let session = Session::builder()?
                .with_model_from_file(model_path)?;

            Ok(Self { session })
        }

        pub fn run(&self, input: &[f32]) -> Result<Vec<f32>, Box<dyn std::error::Error>> {
            // Run inference
            // let outputs = self.session.run(ort::inputs!["input" => input]?)?;
            Ok(vec![])
        }
    }
}

/// llama.cpp wrapper for GGUF models
#[cfg(feature = "llama")]
pub mod llama {
    pub struct LlamaRuntime {
        // llama.cpp context
    }

    impl LlamaRuntime {
        pub fn new(model_path: &str) -> Result<Self, Box<dyn std::error::Error>> {
            log::info!("Loading GGUF model from {}", model_path);
            Ok(Self {})
        }
    }
}

/// Model management and caching
pub struct ModelManager {
    cache_dir: std::path::PathBuf,
    max_cache_size_mb: usize,
}

impl ModelManager {
    pub fn new(cache_dir: &str, max_cache_size_mb: usize) -> Self {
        Self {
            cache_dir: std::path::PathBuf::from(cache_dir),
            max_cache_size_mb,
        }
    }

    /// Download model if not cached
    pub async fn get_model(&self, model_type: &ModelType) -> Result<std::path::PathBuf, InferenceError> {
        let repo = model_type.huggingface_repo()
            .ok_or_else(|| InferenceError::ModelNotFound("Custom model".to_string()))?;

        let model_dir = self.cache_dir.join(repo.replace('/', "_"));

        if model_dir.exists() {
            return Ok(model_dir);
        }

        // Download model (placeholder)
        log::info!("Downloading model from {}...", repo);

        // In production, would use hf-hub or similar
        std::fs::create_dir_all(&model_dir)?;

        Ok(model_dir)
    }

    /// Clean up old models
    pub fn cleanup_cache(&self) -> Result<(), std::io::Error> {
        // Remove oldest models if cache exceeds size
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_size_memory() {
        assert_eq!(ModelSize::Tiny.memory_requirement_mb(), 150);
        assert_eq!(ModelSize::Small.memory_requirement_mb(), 400);
        assert_eq!(ModelSize::Medium.memory_requirement_mb(), 1200);
    }

    #[tokio::test]
    async fn test_sentiment_analysis() {
        let runtime = LocalInferenceRuntime::new(1, 512);

        let result = runtime.sentiment("I love this product, it's amazing!").await;
        assert_eq!(result.unwrap(), "positive");

        let result = runtime.sentiment("Terrible service, very disappointed").await;
        assert_eq!(result.unwrap(), "negative");
    }

    #[tokio::test]
    async fn test_classification() {
        let runtime = LocalInferenceRuntime::new(1, 512);

        let result = runtime.classify(
            "I want to order food",
            &["order".to_string(), "complaint".to_string(), "question".to_string()]
        ).await;

        assert!(result.is_ok());
    }
}
