use crate::safety::symmetry_generator::{Invariant, InvariantClass, SystemState};

pub struct TokenBudgetInvariant;

impl Invariant for TokenBudgetInvariant {
    fn id(&self) -> &'static str { "I-01" }
    fn class(&self) -> InvariantClass { InvariantClass::Critical }
    fn check(&self, state: &SystemState) -> bool {
        state.token_budget >= 0 && state.token_budget <= state.config.max_tokens
    }
    fn margin(&self, state: &SystemState) -> f64 {
        if !self.check(state) {
            0.0
        } else {
            if state.config.max_tokens > 0 {
                (state.token_budget as f64 / state.config.max_tokens as f64).min(1.0)
            } else {
                0.0
            }
        }
    }
}
