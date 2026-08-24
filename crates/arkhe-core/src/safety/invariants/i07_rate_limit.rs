use crate::safety::symmetry_generator::{Invariant, InvariantClass, SystemState};

pub struct RateLimitInvariant;

impl Invariant for RateLimitInvariant {
    fn id(&self) -> &'static str { "I-07" }
    fn class(&self) -> InvariantClass { InvariantClass::High }
    fn check(&self, state: &SystemState) -> bool {
        state.rate_limit_remaining >= 0
    }
    fn margin(&self, state: &SystemState) -> f64 {
        if !self.check(state) {
            0.0
        } else {
            if state.config.max_rate_limit > 0 {
                (state.rate_limit_remaining as f64 / state.config.max_rate_limit as f64).min(1.0)
            } else {
                0.0
            }
        }
    }
}
