use crate::registry::ModelId;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum InferenceError {
    #[error("Model not found: {0}")]
    ModelNotFound(String),

    #[error("Model load failed: {0}")]
    LoadFailed(String),

    #[error("Inference failed: {0}")]
    InferenceFailed(String),

    #[error("Context length exceeded: requested {requested}, max {max}")]
    ContextOverflow { requested: usize, max: usize },

    #[error("Unsupported capability: {0}")]
    UnsupportedCapability(String),

    #[error("Backend not available: {0}. Enable feature '{1}' in Cargo.toml")]
    BackendNotAvailable(String, String),

    #[error("Timeout after {0:?}")]
    Timeout(std::time::Duration),

    #[error("Engine not ready: {model_id}")]
    NotReady { model_id: ModelId },

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Internal inference error: {0}")]
    Internal(String),
}

// Conversão manual — evita #[from] ArkheError que causaria acoplamento circular.
impl From<arkhe_core::ArkheError> for InferenceError {
    fn from(e: arkhe_core::ArkheError) -> Self {
        InferenceError::Internal(e.to_string())
    }
}
