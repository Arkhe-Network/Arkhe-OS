use async_trait::async_trait;
use crate::{
    InferenceRequest, InferenceResponse, InferenceResult, ModelId, StreamChunk,
};
use tokio::sync::mpsc;

/// Trait principal do motor de inferência.
#[async_trait]
pub trait InferenceEngine: Send + Sync {
    /// Retorna o ModelId atualmente carregado.
    fn model_id(&self) -> &ModelId;

    /// Executa inferência completa (non-streaming).
    async fn complete(&self, request: InferenceRequest) -> InferenceResult<InferenceResponse>;

    /// Executa inferência com streaming.
    ///
    /// Retorna um receiver de chunks. O último chunk terá `finish_reason` preenchido.
    /// Implementação padrão delega para `complete()` e envia tudo de uma vez.
    async fn stream(
        &self,
        request: InferenceRequest,
    ) -> InferenceResult<mpsc::Receiver<StreamChunk>> {
        let response = self.complete(request).await?;
        let (tx, rx) = mpsc::channel(2);

        let chunk = StreamChunk {
            token: response.content,
            finish_reason: Some(response.finish_reason),
            timestamp: response.timestamp,
        };
        tokio::spawn(async move {
            let _ = tx.send(chunk).await;
        });

        Ok(rx)
    }

    /// Verifica se o motor está pronto para inferência.
    fn is_ready(&self) -> bool { true }

    /// Retorna o número máximo de tokens de contexto.
    fn max_context_tokens(&self) -> u32 { 4096 }
}
