use crate::constraint::{Constraint, ConstraintResult};
use crate::Verifier;

pub struct Lean4Verifier;

impl Lean4Verifier {
    pub fn new() -> Self {
        Self
    }
}

impl Default for Lean4Verifier {
    fn default() -> Self {
        Self::new()
    }
}

impl Verifier for Lean4Verifier {
    fn verify(&self, constraint: &Constraint, context: &serde_json::Value) -> ConstraintResult {
        // Stub implementation
        let valid = match constraint.expression.as_str() {
            "percentage <= 20" => {
                context.get("percentage")
                    .and_then(|v| v.as_f64())
                    .map(|p| p <= 20.0)
                    .unwrap_or(false)
            }
            "amount <= 100000" => {
                context.get("amount")
                    .and_then(|v| v.as_f64())
                    .map(|a| a <= 100000.0)
                    .unwrap_or(false)
            }
            _ => true,
        };

        ConstraintResult {
            valid,
            counterexample: if valid { None } else { Some("Violação detectada".to_string()) },
            proof: None,
        }
    }
}
