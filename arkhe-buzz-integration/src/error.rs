//! Error types for Arkhe Buzz Integration.

use thiserror::Error;

#[derive(Error, Debug)]
pub enum ArkheBuzzError {
    #[error("Failed to compute S-Measure: {0}")]
    SMeasureComputation(String),

    #[error("Safety barrier triggered. Action rolled back. Delta S: {delta_s}")]
    SafetyBarrierTriggered { delta_s: f32 },

    #[error("Safety violation: {0}")]
    SafetyViolation(f32),

    #[error("Safety violation string: {0}")]
    SafetyViolationString(String),

    #[error("Snapshot failed: {0}")]
    SnapshotFailed(String),

    #[error("Publish failed: {0}")]
    PublishFailed(String),

    #[error("Event validation failed: {0}")]
    EventValidation(String),

    #[error("IPFS not configured")]
    IpfsNotConfigured,

    #[error("IPFS error: {0}")]
    IpfsError(String),
}

pub type Result<T> = std::result::Result<T, ArkheBuzzError>;
