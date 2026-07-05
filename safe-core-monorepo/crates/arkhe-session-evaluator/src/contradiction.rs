use crate::types::*;

pub struct ContradictionDetector;

impl Default for ContradictionDetector {
    fn default() -> Self { Self }
}

const NEGATION_PAIRS: &[(&str, &str)] = &[
    ("não", "sim"), ("falso", "verdadeiro"), ("errado", "certo"),
    ("incorreto", "correto"), ("impossível", "possível"),
];

impl ContradictionDetector {
    pub async fn score(&self, trajectory: &SessionTrajectory) -> DimensionScore {
        let mut contradictions = Vec::new();
        let mut evidence = Vec::new();

        for i in 0..trajectory.turns.len() {
            for j in (i + 1)..trajectory.turns.len() {
                if let Some(desc) = self.detect(&trajectory.turns[i], &trajectory.turns[j]) {
                    evidence.push(format!("Contradição: {} vs {} — {}", trajectory.turns[i].id, trajectory.turns[j].id, desc));
                    contradictions.push(desc);
                }
            }
        }

        let score = if contradictions.is_empty() {
            1.0
        } else {
            (1.0 - (contradictions.len() as f32 / trajectory.turns.len().max(1) as f32) * 0.3).max(0.0)
        };

        DimensionScore::new(
            score,
            if contradictions.is_empty() { "Nenhuma contradição.".to_string() }
            else { format!("{} contradição(ões).", contradictions.len()) },
        ).with_evidence(evidence)
    }

    fn detect(&self, a: &Turn, b: &Turn) -> Option<String> {
        let ta = a.content.to_lowercase();
        let tb = b.content.to_lowercase();

        for (neg, pos) in NEGATION_PAIRS {
            let a_neg = ta.contains(neg) && tb.contains(pos);
            let a_pos = ta.contains(pos) && tb.contains(neg);
            if a_neg || a_pos {
                let sim = strsim::normalized_levenshtein(&ta, &tb);
                if sim > 0.8 {
                    return Some(format!("Negeração oposta: '{}' vs '{}'", neg, pos));
                }
            }
        }
        None
    }
}
