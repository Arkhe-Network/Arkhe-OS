use thiserror::Error;

#[derive(Debug, Error)]
pub enum CognitiveError {
    #[error("Model load failed: {0}")]
    ModelLoad(String),

    #[error("Inference failed: {0}")]
    Inference(String),

    #[error("Tokenizer error: {0}")]
    Tokenizer(String),

    #[error("Plan generation failed: {0}")]
    PlanGeneration(String),

    #[error("Plan validation failed: depth {depth} exceeds max {max}")]
    PlanDepthExceeded { depth: usize, max: usize },

    #[error("Plan contains cycles")]
    PlanCycleDetected,

    #[error("Embedding generation failed: {0}")]
    Embedding(String),

    #[error("HuggingFace Hub error: {0}")]
    HfHub(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Candle error: {0}")]
    Candle(String),
}

impl From<candle_core::Error> for CognitiveError {
    fn from(e: candle_core::Error) -> Self {
        CognitiveError::Candle(e.to_string())
    }
}

impl From<tokenizers::Error> for CognitiveError {
    fn from(e: tokenizers::Error) -> Self {
        CognitiveError::Tokenizer(e.to_string())
    }
}
