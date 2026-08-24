use crate::safety::symmetry_generator::{Invariant, InvariantClass, SystemState};

pub struct AgentCountInvariant;

impl Invariant for AgentCountInvariant {
    fn id(&self) -> &'static str { "I-02" }
    fn class(&self) -> InvariantClass { InvariantClass::High }
    fn check(&self, state: &SystemState) -> bool {
        state.agent_count <= state.config.max_agents
    }
    fn margin(&self, state: &SystemState) -> f64 {
        if !self.check(state) {
            0.0
        } else {
            if state.config.max_agents > 0 {
                1.0 - (state.agent_count as f64 / state.config.max_agents as f64)
            } else {
                0.0
            }
        }
    }
}
