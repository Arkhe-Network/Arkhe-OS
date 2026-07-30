use aegis_plausible_reasoner::{SuccessRecord, SuccessDatabase};
use crate::policy::PolicyRule;

pub struct SuccessRecorder {
    db: SuccessDatabase,
}

impl SuccessRecorder {
    pub fn new() -> Self {
        Self { db: SuccessDatabase::new() }
    }

    pub fn record_improvement(
        &mut self,
        mutation_id: u32,
        context: &[f32],
        original_rule: Option<PolicyRule>,
        new_rule: PolicyRule,
        improvement: f32,
        round: u32,
        domain: &str,
    ) {
        let record = SuccessRecord {
            mutation_id,
            context_embedding: context.to_vec(),
            original_rule,
            new_rule,
            outcome_improvement: improvement,
            applied_round: round,
            domain: domain.to_string(),
        };
        self.db.add(record);
    }

    pub fn get_db(&self) -> &SuccessDatabase {
        &self.db
    }
}
