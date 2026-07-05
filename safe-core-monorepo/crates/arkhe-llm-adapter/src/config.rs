use arkhe_inference::ModelId;

#[derive(Debug, Clone)]
pub struct AdapterConfig {
    pub model_id: ModelId,
    pub backend: InferenceBackend,
    pub quantized: bool,
    pub device: String,
}

impl Default for AdapterConfig {
    fn default() -> Self {
        Self {
            model_id: ModelId::new("deepseek", "deepseek-v3"),
            backend: InferenceBackend::MistralRs,
            quantized: true,
            device: "cuda".to_string(),
        }
    }
}
