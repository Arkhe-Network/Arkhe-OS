use thiserror::Error;

/// Hash tipografada — wrapper em torno de [u8; 32].
pub type ArkheHash = [u8; 32];

/// Resultado tipado do Arkhe.
pub type ArkheResult<T> = Result<T, ArkheError>;

/// Erros centrais do sistema Arkhe.
#[derive(Debug, Error)]
pub enum ArkheError {
    #[error("Internal error: {0}")]
    Internal(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Timeout: {0:?}")]
    Timeout(std::time::Duration),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error(transparent)]
    Other(#[from] Box<dyn std::error::Error + Send + Sync>),
}
