use crate::safety::symmetry_generator::{Invariant, InvariantClass, SystemState};

pub struct SandboxFuelInvariant;

impl Invariant for SandboxFuelInvariant {
    fn id(&self) -> &'static str { "I-03" }
    fn class(&self) -> InvariantClass { InvariantClass::Critical }
    fn check(&self, state: &SystemState) -> bool {
        state.sandbox_fuel >= state.config.min_fuel
    }
    fn margin(&self, state: &SystemState) -> f64 {
        if !self.check(state) {
            0.0
        } else {
            if state.config.max_sandbox_fuel > 0 {
                (state.sandbox_fuel as f64 / state.config.max_sandbox_fuel as f64).min(1.0)
            } else {
                0.0
            }
        }
    }
}
