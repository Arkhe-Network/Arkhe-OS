use aegis_plausible_reasoner::{PlausibleReasoner, PolicyMutation, Condition, PolicyAction};
use crate::digester::DigestSummary;
use crate::policy::{Policy, PolicyRule};

pub enum EditProposal {
    AdjustParam { param: &'static str, new_value: f32 },
    AddRule { rule: PolicyRule },
    RemoveRule(u32),
    ModifyRule { rule_id: u32, new_condition: Condition, new_action: PolicyAction },
}

pub struct Planner {
    plausible_reasoner: PlausibleReasoner,
}

impl Planner {
    pub fn new() -> Self {
        Self {
            plausible_reasoner: PlausibleReasoner::new(),
        }
    }

    pub fn plan(
        &mut self,
        summary: &DigestSummary,
        current_policy: &Policy,
    ) -> Vec<EditProposal> {
        let mut proposals = Vec::new();

        // Standard parameter tuning (existing code)
        if summary.calibration_error > 0.3 {
            proposals.push(EditProposal::AdjustParam {
                param: "commitment_interval",
                new_value: 50.0,
            });
        }

        // If parameter tuning stagnates (e.g., no improvement for 3 rounds), try structural edits
        if summary.stagnation_rounds > 2 {
            let context_embedding = self.build_context_embedding(summary);
            let mutations = self.plausible_reasoner.propose_structural_edits(&context_embedding, current_policy);
            for mutation in mutations {
                let edit = self.mutation_to_edit(mutation);
                proposals.push(edit);
            }
        }

        proposals
    }

    fn build_context_embedding(&self, summary: &DigestSummary) -> Vec<f32> {
        // Create a small vector from relevant metrics
        vec![
            summary.calibration_error,
            summary.avg_interference,
            summary.acceptance_rate,
            summary.proof_latency_ms as f32 / 1000.0,
        ]
    }

    fn mutation_to_edit(&self, mutation: PolicyMutation) -> EditProposal {
        match mutation {
            PolicyMutation::AddRule(rule) => EditProposal::AddRule {
                rule: PolicyRule {
                    id: rule.id,
                    condition: rule.condition,
                    action: rule.action,
                    priority: rule.priority,
                },
            },
            PolicyMutation::RemoveRule(rule_id) => EditProposal::RemoveRule(rule_id),
            PolicyMutation::ModifyRule { rule_id, new_condition, new_action } => {
                EditProposal::ModifyRule {
                    rule_id,
                    new_condition,
                    new_action,
                }
            }
        }
    }
}
