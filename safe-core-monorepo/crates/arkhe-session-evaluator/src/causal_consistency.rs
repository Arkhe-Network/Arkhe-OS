use std::collections::HashSet;
use crate::types::*;
use tracing::debug;

pub struct CausalConsistencyScorer;

impl Default for CausalConsistencyScorer {
    fn default() -> Self { Self }
}

const CAUSAL_PATTERNS: &[(&str, CausalRelation)] = &[
    ("porque", CausalRelation::Premise),
    ("ja que", CausalRelation::Premise),
    ("portanto", CausalRelation::Refinement),
    ("consequentemente", CausalRelation::Refinement),
    ("logo", CausalRelation::Refinement),
    ("corrigindo", CausalRelation::Correction),
    ("na verdade", CausalRelation::Correction),
    ("verifiquei que", CausalRelation::Validation),
    ("assim", CausalRelation::Refinement),
];

impl CausalConsistencyScorer {
    pub async fn score(&self, trajectory: &SessionTrajectory) -> DimensionScore {
        let mut links = Vec::new();
        for turn in &trajectory.turns {
            let text = turn.content.to_lowercase();
            for (pattern, relation) in CAUSAL_PATTERNS {
                if text.contains(pattern) {
                    if let Some(prev) = trajectory.turns.iter().filter(|t| t.id != turn.id).last() {
                        links.push(CausalLink {
                            from_turn: prev.id.clone(),
                            to_turn: turn.id.clone(),
                            relation: relation.clone(),
                            strength: 0.7,
                        });
                    }
                    break; // Um link por turno
                }
            }
        }

        if links.is_empty() {
            return DimensionScore::new(0.5, "Nenhum link causal explícito encontrado.");
        }

        let assistant_turns: Vec<&Turn> = trajectory.turns.iter().filter(|t| t.role == TurnRole::Assistant).collect();
        let linked_turns: HashSet<&str> = links.iter().flat_map(|l| [l.from_turn.as_str(), l.to_turn.as_str()]).collect();
        let coverage = linked_turns.len() as f32 / assistant_turns.len().max(1) as f32;

        let evidence: Vec<String> = links.iter()
            .map(|l| format!("Causal: {} → {} ({:?})", l.from_turn, l.to_turn, l.relation))
            .collect();

        debug!(links = links.len(), coverage = %format!("{:.2}", coverage), "Causal scored");

        DimensionScore::new(coverage, format!("{} links em {} turns.", links.len(), assistant_turns.len()))
            .with_evidence(evidence)
    }
}
