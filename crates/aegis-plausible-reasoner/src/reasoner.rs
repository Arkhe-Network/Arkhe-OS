//! Plausible reasoning engine that generates structural policy mutations by analogy.

use crate::success_db::SuccessDatabase;
use crate::policy::{Policy, PolicyRule, Condition, PolicyAction};
use rand::Rng;

pub struct PlausibleReasoner {
    success_db: SuccessDatabase,
    rng: rand::rngs::ThreadRng,
}

impl PlausibleReasoner {
    pub fn new() -> Self {
        Self {
            success_db: SuccessDatabase::new(),
            rng: rand::thread_rng(),
        }
    }

    /// Propose new policy rules based on analogies with past successful mutations.
    /// `context_embedding` describes the current failure situation.
    /// `current_policy` is the policy being evolved.
    /// Returns a list of candidate new rules (or modifications to existing rules).
    pub fn propose_structural_edits(
        &mut self,
        context_embedding: &[f32],
        current_policy: &Policy,
    ) -> Vec<PolicyMutation> {
        let mut candidates = Vec::new();
        // Find similar past successes
        let similar = self.success_db.find_similar(context_embedding, 3);
        for record in similar {
            // Generate analogies based on the successful mutation pattern
            let mutation = self.analogical_transfer(&record.new_rule, current_policy);
            candidates.push(mutation);
        }
        // Also generate a few random structural mutations for exploration
        candidates.push(self.random_structural_mutation(current_policy));
        candidates
    }

    /// Transfer a successful rule pattern to a new context, adapting its conditions and action.
    fn analogical_transfer(&self, source_rule: &PolicyRule, target_policy: &Policy) -> PolicyMutation {
        // Example analogical mapping:
        // If source rule had condition "step_count % 5 == 0" and action "Prove",
        // we might propose "step_count % 10 == 0" or "step_count % 5 == 0 AND confidence < 0.5".
        let new_condition = self.analogical_condition(&source_rule.condition);
        let new_action = self.analogical_action(&source_rule.action);
        PolicyMutation::AddRule(PolicyRule {
            id: target_policy.rules.iter().map(|r| r.id).max().unwrap_or(0) + 1,
            condition: new_condition,
            action: new_action,
            priority: 128, // middle priority
        })
    }

    fn analogical_condition(&self, cond: &Condition) -> Condition {
        let mut rng = rand::thread_rng();
        match cond {
            Condition::StepCountModulo(m) => {
                // Explore nearby moduli (e.g., if 5 worked, try 10 or 3)
                let new_m = if rng.gen_bool(0.5) { m * 2 } else { m / 2 };
                Condition::StepCountModulo(new_m.max(1))
            }
            Condition::ActionRisk(risk) => Condition::ActionRisk(risk.clone()),
            Condition::UserTrustLevel(level) => Condition::UserTrustLevel(level.clone()),
            Condition::LastProofFailed(b) => Condition::LastProofFailed(*b),
            Condition::ConfidenceBelow(th) => Condition::ConfidenceBelow(*th * 0.9),
            Condition::InterferenceAbove(th) => Condition::InterferenceAbove(*th * 0.8),
            Condition::And(left, _right) => {
                // Simplify: just keep one part
                self.analogical_condition(left)
            }
            Condition::Or(left, _right) => self.analogical_condition(left),
        }
    }

    fn analogical_action(&self, action: &PolicyAction) -> PolicyAction {
        let mut rng = rand::thread_rng();
        match action {
            PolicyAction::Prove => {
                if rng.gen_bool(0.3) {
                    PolicyAction::ProveAndVerifyOnChain
                } else {
                    PolicyAction::Prove
                }
            }
            PolicyAction::ProveAndVerifyOnChain => PolicyAction::ProveAndVerifyOnChain,
            PolicyAction::EmergencyHalt => PolicyAction::EmergencyHalt,
            PolicyAction::ConservativeMode => PolicyAction::ConservativeMode,
            PolicyAction::AdjustThreshold { field, value } => {
                PolicyAction::AdjustThreshold { field: field.clone(), value: *value * 1.2 }
            }
            _ => PolicyAction::Prove,
        }
    }

    fn random_structural_mutation(&mut self, target_policy: &Policy) -> PolicyMutation {
        // Randomly add a rule with a simple condition
        let condition = match self.rng.gen_range(0..4) {
            0 => Condition::StepCountModulo(self.rng.gen_range(1..20)),
            1 => Condition::ActionRisk("high".to_string()),
            2 => Condition::ConfidenceBelow(0.6),
            _ => Condition::InterferenceAbove(0.7),
        };
        let action = if self.rng.gen_bool(0.7) { PolicyAction::Prove } else { PolicyAction::Skip };
        PolicyMutation::AddRule(PolicyRule {
            id: target_policy.rules.iter().map(|r| r.id).max().unwrap_or(0) + 1,
            condition,
            action,
            priority: self.rng.gen_range(0..255),
        })
    }
}

/// Represents a structural change to the policy.
#[derive(Debug, Clone)]
pub enum PolicyMutation {
    AddRule(PolicyRule),
    RemoveRule(u32),
    ModifyRule { rule_id: u32, new_condition: Condition, new_action: PolicyAction },
}
