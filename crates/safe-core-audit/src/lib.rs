//! Auditoria Imutável — Cadeia de Merkle para Decisões de Governança

pub mod merkle;
pub mod event;
pub mod trail;

pub use merkle::{MerkleTree, MerkleProof};
pub use event::{AuditEvent, EventType};
pub use trail::AuditTrail;

#[derive(Debug, thiserror::Error)]
pub enum AuditError {
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}
