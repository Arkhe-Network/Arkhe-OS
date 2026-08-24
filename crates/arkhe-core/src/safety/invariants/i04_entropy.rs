use crate::safety::symmetry_generator::{Invariant, InvariantClass, SystemState};

pub struct EntropyInvariant;

impl Invariant for EntropyInvariant {
    fn id(&self) -> &'static str { "I-04" }
    fn class(&self) -> InvariantClass { InvariantClass::Critical }
    fn check(&self, state: &SystemState) -> bool {
        state.entropy_bits >= state.config.min_entropy
    }
    fn margin(&self, state: &SystemState) -> f64 {
        if !self.check(state) {
            0.0
        } else {
            if state.config.min_entropy > 0 {
                ((state.entropy_bits - state.config.min_entropy) as f64 / state.config.min_entropy as f64).min(1.0)
            } else {
                1.0
            }
        }
    }
}
