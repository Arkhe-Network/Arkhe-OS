#![warn(missing_docs)]
#![deny(unsafe_code)]

pub mod error;
pub mod types;
pub mod registry;
pub mod engine;
pub mod null;

#[cfg(feature = "mistralrs-backend")]
pub mod mistralrs_backend;

#[cfg(feature = "candle-backend")]
pub mod candle_backend;

#[cfg(feature = "gguf-backend")]
pub mod gguf_backend;

pub use error::InferenceError;
pub use types::{
    InferenceRequest, InferenceResponse, TokenUsage, FinishReason,
    ChatMessage, ChatRole, SamplingParams, ToolDefinition, ToolCall,
    StreamChunk, StreamEvent,
};
pub use registry::{ModelId, ModelRegistry, ModelCapabilities, BackendType, ModelLicense};
pub use engine::InferenceEngine;
pub use null::NullEngine;

pub type InferenceResult<T> = Result<T, InferenceError>;
