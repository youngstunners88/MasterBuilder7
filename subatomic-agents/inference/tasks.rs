// Inference task definitions

use serde::{Serialize, Deserialize};

/// NLP task types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NLPTask {
    /// Text classification
    Classification { text: String, labels: Vec<String> },
    /// Named entity recognition
    NER { text: String },
    /// Sentiment analysis
    Sentiment { text: String },
    /// Text generation
    Generation { prompt: String, max_tokens: u32 },
    /// Summarization
    Summarization { text: String, max_length: u32 },
    /// Question answering
    QA { question: String, context: String },
    /// Text embedding
    Embedding { text: String },
    /// Translation
    Translation { text: String, source_lang: String, target_lang: String },
}

/// Vision task types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VisionTask {
    /// Image classification
    ImageClassification { image_data: Vec<u8> },
    /// Object detection
    ObjectDetection { image_data: Vec<u8> },
    /// OCR
    OCR { image_data: Vec<u8> },
}

/// Audio task types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AudioTask {
    /// Speech recognition
    SpeechToText { audio_data: Vec<u8> },
    /// Text to speech
    TextToSpeech { text: String },
}

/// Combined inference task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InferenceTaskType {
    NLP(NLPTask),
    Vision(VisionTask),
    Audio(AudioTask),
}

impl InferenceTaskType {
    /// Get task complexity (affects resource requirements)
    pub fn complexity(&self) -> TaskComplexity {
        match self {
            InferenceTaskType::NLP(nlp) => match nlp {
                NLPTask::Classification { .. } => TaskComplexity::Low,
                NLPTask::Sentiment { .. } => TaskComplexity::Low,
                NLPTask::Embedding { .. } => TaskComplexity::Low,
                NLPTask::NER { .. } => TaskComplexity::Medium,
                NLPTask::QA { .. } => TaskComplexity::Medium,
                NLPTask::Summarization { .. } => TaskComplexity::High,
                NLPTask::Generation { max_tokens, .. } => {
                    if *max_tokens < 50 {
                        TaskComplexity::Medium
                    } else {
                        TaskComplexity::High
                    }
                }
                NLPTask::Translation { .. } => TaskComplexity::Medium,
            },
            InferenceTaskType::Vision(_) => TaskComplexity::High,
            InferenceTaskType::Audio(_) => TaskComplexity::Medium,
        }
    }

    /// Get required memory (MB)
    pub fn required_memory_mb(&self) -> usize {
        match self.complexity() {
            TaskComplexity::Low => 100,
            TaskComplexity::Medium => 300,
            TaskComplexity::High => 600,
        }
    }
}

/// Task complexity
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskComplexity {
    Low,
    Medium,
    High,
}
