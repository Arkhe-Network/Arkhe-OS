pub mod i01_token_budget;
pub mod i02_agent_count;
pub mod i03_sandbox_fuel;
pub mod i04_entropy;
pub mod i05_pii;
pub mod i06_signature;
pub mod i07_rate_limit;
pub mod i08_capability;

use crate::safety::symmetry_generator::Invariant;

pub fn all_invariants() -> Vec<Box<dyn Invariant>> {
    vec![
        Box::new(i01_token_budget::TokenBudgetInvariant),
        Box::new(i02_agent_count::AgentCountInvariant),
        Box::new(i03_sandbox_fuel::SandboxFuelInvariant),
        Box::new(i04_entropy::EntropyInvariant),
        Box::new(i05_pii::PiiScrubbedInvariant),
        Box::new(i06_signature::SignatureValidInvariant),
        Box::new(i07_rate_limit::RateLimitInvariant),
        Box::new(i08_capability::CapabilityInvariant),
    ]
}
