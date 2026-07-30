#[async_trait::async_trait]
pub trait InferenceEngine: Send + Sync {
    async fn generate(&self, prompt: &str, temperature: f32, max_tokens: usize) -> Result<String, String>;
}
