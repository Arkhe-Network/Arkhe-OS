//! Verificação Formal via Lean4 — Provas Matemáticas de Correção

pub mod constraint;
pub mod lean4;

pub use constraint::{Constraint, ConstraintResult};
pub use lean4::Lean4Verifier;

/// Verificador de restrições via Lean4.
pub trait Verifier: Send + Sync {
    fn verify(&self, constraint: &Constraint, context: &serde_json::Value) -> ConstraintResult;
}
