//! Arkhe Core — Tipos fundacionais e traits de integração.
//!
//! Este crate define:
//! - Tipos base (hash, erro, resultado)
//! - Traits de assinatura (para PEA/identity)
//! - **Traits de integração** (para arkhe-agi se comunicar com PEA e Memória
//!   sem dependência direta)

#![warn(missing_docs)]
#![deny(unsafe_code)]

pub mod error;
pub mod hash;
pub mod safety;
pub mod memory_traits;

pub use error::{ArkheError, ArkheResult, ArkheHash};
pub use safety::{SafetyVerdict, SafetyVerifier, AlwaysAllowVerifier, AlwaysRejectVerifier};
pub use memory_traits::{AgentMemory, MemoryEntry, MemoryLayer, InMemoryAgentMemory};
