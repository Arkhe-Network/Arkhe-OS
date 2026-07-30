// crates/kernel/src/lib.rs
//! kernel — Orquestrador AGI com heartbit-core::Orchestrator
//!
//! Integra:
//! - cognitive-core: Planejamento Hierárquico (DagAgent)
//! - action-executor: Execução sandboxed (fork+execvp+Landlock)
//! - memory-system: Memória vetorial com selagem Merkle

pub mod orchestrator;
pub mod lifecycle;
pub mod error;

pub use orchestrator::SafeCoreOrchestrator;
pub use lifecycle::SystemLifecycle;
pub use error::KernelError;
