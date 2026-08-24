use crate::safety::symmetry_generator::{Invariant, InvariantClass, SystemState};

pub struct PiiScrubbedInvariant;

impl Invariant for PiiScrubbedInvariant {
    fn id(&self) -> &'static str { "I-05" }
    fn class(&self) -> InvariantClass { InvariantClass::Critical }
    fn check(&self, state: &SystemState) -> bool {
        state.pii_scrubbed
    }
}
