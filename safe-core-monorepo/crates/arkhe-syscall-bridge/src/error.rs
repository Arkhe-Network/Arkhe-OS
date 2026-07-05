use thiserror::Error;

#[derive(Debug, Error)]
pub enum BridgeError {
    #[error("Syscall not found: {side}::{number}")]
    SyscallNotFound { side: String, number: u32 },

    #[error("No mapping for {from_side}::{from_number} → {to_side}")]
    NoMapping {
        from_side: String,
        from_number: u32,
        to_side: String,
    },

    #[error("Mapping blocked by policy: {reason}")]
    Blocked { reason: String },

    #[error("Ambiguous mapping: {from_side}::{from_number} → {candidates:?}")]
    Ambiguous {
        from_side: String,
        from_number: u32,
        candidates: Vec<String>,
    },

    #[error("Invalid syscall number: {side}::{number}")]
    InvalidNumber { side: String, number: u32 },

    #[error("Internal error: {0}")]
    Internal(String),
}

pub type BridgeResult<T> = Result<T, BridgeError>;
