#![cfg(feature = "gguf-backend")]

use async_trait::async_trait;
use crate::*;
use std::path::PathBuf;
use tracing::warn;

pub struct GGUFEngine { model_id: ModelId, path: PathBuf, loaded: bool }

impl GGUFEngine {
    pub fn new(model_id: ModelId, path: PathBuf) -> Self { Self { model_id, path, loaded: false } }
    pub async fn load(&mut self) -> InferenceResult<()> {
        if self.loaded { return Ok(()); }
        if !self.path.exists() { return Err(InferenceError::LoadFailed(format!("Not found: {}", self.path.display()))); }
        warn!("GGUF backend is a stub — integrate llama-cpp-2 API here");
        self.loaded = true;
        Ok(())
    }
}

#[async_trait]
impl InferenceEngine for GGUFEngine {
    fn model_id(&self) -> &ModelId { &self.model_id }
    async fn complete(&self, _req: InferenceRequest) -> InferenceResult<InferenceResponse> {
        if !self.loaded { return Err(InferenceError::NotReady { model_id: self.model_id.clone() }); }
        Err(InferenceError::Internal("GGUF stub — implement with llama-cpp-2".into()))
    }
    fn is_ready(&self) -> bool { self.loaded }
}
