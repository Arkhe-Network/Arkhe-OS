use thiserror::Error;

#[derive(Debug, Error)]
pub enum CryptoError {
    #[error("Chave pública vazia")]
    EmptyPublicKey,
    #[error("Falha na assinatura threshold: {0}")]
    ThresholdError(String),
}
