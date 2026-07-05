use thiserror::Error;

#[derive(Debug, Error)]
pub enum GovBridgeError {
    #[error("Identity not found: {side}:{identifier}")]
    IdentityNotFound { side: String, identifier: String },

    #[error("Mapping conflict: DID {did} already mapped to {existing}")]
    MappingConflict {
        did: String,
        existing: String,
    },

    #[error("Policy evaluation failed: {0}")]
    PolicyEvaluation(String),

    #[error("Platform not supported: {0}")]
    UnsupportedPlatform(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

pub type GovBridgeResult<T> = Result<T, GovBridgeError>;
