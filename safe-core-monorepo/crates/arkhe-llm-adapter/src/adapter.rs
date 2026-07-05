use arkhe_inference::{InferenceEngine, InferenceRequest, InferenceResponse, ModelId};
use async_trait::async_trait;
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InferenceBackend {
    MistralRs,
    Candle,
    LlamaCpp,
    Null,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModelFamily {
    DeepSeekV3,
    Gemma4_12B,
    MistralLeanstral,
}

/// Adaptador unificado para LLMs.
pub struct LlmAdapter {
    engine: Arc<dyn InferenceEngine>,
}

impl LlmAdapter {
    pub fn new(engine: Arc<dyn InferenceEngine>) -> Self {
        Self { engine }
    }

    pub async fn chat(&self, prompt: &str) -> Result<String, String> {
        let request = InferenceRequest::simple(prompt);
        let response = self.engine.complete(request).await
            .map_err(|e| e.to_string())?;
        Ok(response.content)
    }

    pub fn model_id(&self) -> &ModelId {
        self.engine.model_id()
    }
}
