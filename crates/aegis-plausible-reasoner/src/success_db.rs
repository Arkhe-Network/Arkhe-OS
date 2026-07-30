//! Database of successful policy mutations, with context embeddings and outcomes.

use serde::{Serialize, Deserialize};
use crate::policy::PolicyRule;

/// A recorded successful mutation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuccessRecord {
    pub mutation_id: u32,
    pub context_embedding: Vec<f32>,   // e.g., calibration_error, interference, task_type
    pub original_rule: Option<PolicyRule>,
    pub new_rule: PolicyRule,
    pub outcome_improvement: f32,       // delta in acceptance rate
    pub applied_round: u32,
    pub domain: String,                 // e.g., "multihop_qa", "multilingual_fact"
}

/// Database of past successful edits, indexable by similarity.
pub struct SuccessDatabase {
    records: Vec<SuccessRecord>,
    // For fast similarity search (simplified: linear scan)
}

impl SuccessDatabase {
    pub fn new() -> Self {
        Self { records: Vec::new() }
    }

    pub fn add(&mut self, record: SuccessRecord) {
        self.records.push(record);
    }

    /// Find the top-k most similar records based on cosine similarity of context embeddings.
    pub fn find_similar(&self, query_embedding: &[f32], k: usize) -> Vec<&SuccessRecord> {
        let mut scored: Vec<(f32, &SuccessRecord)> = self.records.iter()
            .map(|r| (cosine_similarity(query_embedding, &r.context_embedding), r))
            .collect();
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
        scored.into_iter().take(k).map(|(_, r)| r).collect()
    }
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b).map(|(x,y)| x*y).sum();
    let na: f32 = a.iter().map(|x| x*x).sum::<f32>().sqrt();
    let nb: f32 = b.iter().map(|x| x*x).sum::<f32>().sqrt();
    if na == 0.0 || nb == 0.0 { 0.0 } else { dot / (na * nb) }
}
