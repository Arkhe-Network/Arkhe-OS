use async_trait::async_trait;
use chrono::Utc;
use tokio::sync::mpsc;
use crate::{
    InferenceEngine, InferenceRequest, InferenceResponse, InferenceResult,
    ModelId, TokenUsage, FinishReason, StreamChunk,
};

/// Motor nulo — retorna echo sem chamada real.
/// Útil para testes e desenvolvimento.
pub struct NullEngine {
    model_id: ModelId,
    max_context: u32,
}

impl NullEngine {
    pub fn new(model_id: ModelId) -> Self {
        Self { model_id, max_context: 4096 }
    }

    /// Cria com contexto customizado.
    pub fn with_max_context(model_id: ModelId, max_context: u32) -> Self {
        Self { model_id, max_context }
    }
}

#[async_trait]
impl InferenceEngine for NullEngine {
    fn model_id(&self) -> &ModelId { &self.model_id }

    async fn complete(&self, request: InferenceRequest) -> InferenceResult<InferenceResponse> {
        let last_user = request
            .messages
            .iter()
            .rev()
            .find(|m| m.role == crate::ChatRole::User)
            .map(|m| m.content.as_str())
            .unwrap_or("(empty)");

        // Estimar tokens (4 chars ≈ 1 token)
        let total_input: usize = request.messages.iter().map(|m| m.content.len()).sum();
        let prompt_tokens = (total_input / 4) as u32;
        let completion_tokens = (last_user.len() / 4) as u32 + 5;

        Ok(InferenceResponse {
            content: format!("[NullEngine:{}/{}] Echo: {}", self.model_id.family(), self.model_id.name(), last_user),
            tool_calls: Vec::new(),
            usage: TokenUsage::new(prompt_tokens, completion_tokens),
            finish_reason: FinishReason::Stop,
            timestamp: Utc::now(),
            metadata: Default::default(),
        })
    }

    async fn stream(&self, request: InferenceRequest) -> InferenceResult<mpsc::Receiver<StreamChunk>> {
        let response = self.complete(request).await?;
        let (tx, rx) = mpsc::channel(8);

        // Simula streaming: envia palavra por palavra
        let words: Vec<String> = response.content.split_whitespace().map(String::from).collect();
        tokio::spawn(async move {
            for (i, word) in words.iter().enumerate() {
                let is_last = i == words.len() - 1;
                let chunk = StreamChunk {
                    token: if is_last { format!("{}\n", word) } else { format!("{} ", word) },
                    finish_reason: if is_last { Some(response.finish_reason) } else { None },
                    timestamp: Utc::now(),
                };
                if tx.send(chunk).await.is_err() { break; }
                tokio::time::sleep(std::time::Duration::from_millis(10)).await;
            }
        });

        Ok(rx)
    }

    fn is_ready(&self) -> bool { true }
    fn max_context_tokens(&self) -> u32 { self.max_context }
}
