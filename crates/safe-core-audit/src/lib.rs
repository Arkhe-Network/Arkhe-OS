//! Auditoria Imutável — Cadeia de Merkle para Decisões de Governança

pub mod event;
pub mod merkle;
pub mod trail;

pub use event::{AuditEvent, EventType};
pub use merkle::{MerkleProof, MerkleTree};
pub use trail::AuditTrail;

#[derive(Debug, thiserror::Error)]
pub enum AuditError {
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}
