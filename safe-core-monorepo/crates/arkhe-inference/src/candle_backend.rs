#![cfg(feature = "candle-backend")]

use async_trait::async_trait;
use crate::*;
use std::path::PathBuf;
use tracing::warn;

pub struct CandleEngine { model_id: ModelId, path: PathBuf, loaded: bool }

impl CandleEngine {
    pub fn new(model_id: ModelId, path: PathBuf) -> Self { Self { model_id, path, loaded: false } }
    pub async fn load(&mut self) -> InferenceResult<()> {
        if self.loaded { return Ok(()); }
        if !self.path.exists() { return Err(InferenceError::LoadFailed(format!("Not found: {}", self.path.display()))); }
        // ✅ M2: usa candle_transformers::models::gemma, não quantized_gemma3
        warn!("Candle backend is a stub — integrate candle-transformers::models::gemma here");
        self.loaded = true;
        Ok(())
    }
}

#[async_trait]
impl InferenceEngine for CandleEngine {
    fn model_id(&self) -> &ModelId { &self.model_id }
    async fn complete(&self, _req: InferenceRequest) -> InferenceResult<InferenceResponse> {
        if !self.loaded { return Err(InferenceError::NotReady { model_id: self.model_id.clone() }); }
        Err(InferenceError::Internal("Candle stub — implement with candle-transformers".into()))
    }
    fn is_ready(&self) -> bool { self.loaded }
}
