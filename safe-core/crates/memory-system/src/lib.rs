//! memory-system — Memória de Longo Prazo com Selagem Merkle
//!
//! Banco vetorial (Qdrant) + Merkle Tree externa para integridade.
//! API qdrant-client 1.18 verificada com builder pattern.

pub mod store;
pub mod seal;
pub mod vector;
pub mod error;

pub use store::MerkleSealedVectorStore;
pub use seal::{MemorySealer, MemorySnapshot};
pub use vector::{VectorEntry, SealedVector};
pub use error::MemoryError;
