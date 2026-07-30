use thiserror::Error;

#[derive(Debug, Error)]
pub enum MemoryError {
    #[error("Qdrant connection failed: {0}")]
    Connection(String),

    #[error("Collection error: {0}")]
    Collection(String),

    #[error("Invalid dimension: expected {expected}, got {got}")]
    InvalidDimension { expected: u64, got: usize },

    #[error("Merkle error: {0}")]
    Merkle(String),

    #[error("Crypto error: {0}")]
    Crypto(String),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Point not found: {0}")]
    PointNotFound(String),

    #[error("Proof verification failed")]
    ProofVerificationFailed,

    #[error("Empty tree")]
    EmptyTree,

    #[error("Qdrant client error: {0}")]
    Qdrant(String),
}

impl From<qdrant_client::QdrantError> for MemoryError {
    fn from(e: qdrant_client::QdrantError) -> Self {
        MemoryError::Qdrant(e.to_string())
    }
}

impl From<rs_merkle::Error> for MemoryError {
    fn from(e: rs_merkle::Error) -> Self {
        MemoryError::Merkle(e.to_string())
    }
}

impl From<serde_json::Error> for MemoryError {
    fn from(e: serde_json::Error) -> Self {
        MemoryError::Serialization(e.to_string())
    }
}
