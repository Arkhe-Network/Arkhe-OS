use regex::Regex;
use crate::types::*;

pub struct ValidationDetector { patterns: Vec<Regex> }

impl Default for ValidationDetector {
    fn default() -> Self { Self::new() }
}

impl ValidationDetector {
    pub fn new() -> Self {
        Self {
            patterns: [r"verifiquei que .+", r"confirme que .+", r"valide que .+", r"assegure que .+"]
                .iter().filter_map(|p| Regex::new(p).ok()).collect(),
        }
    }

    pub async fn score(&self, trajectory: &SessionTrajectory) -> DimensionScore {
        let assistant: Vec<&Turn> = trajectory.turns.iter().filter(|t| t.role == TurnRole::Assistant).collect();
        let mut count = 0usize;
        let mut evidence = Vec::new();

        for turn in &assistant {
            for re in &self.patterns {
                if re.is_match(&turn.content) {
                    count += 1;
                    evidence.push(format!("Turno {} tem validação explícita", turn.id));
                    break;
                }
            }
        }

        let score = if assistant.is_empty() { 0.0 } else { count as f32 / assistant.len() as f32 };
        DimensionScore::new(score, format!("{}/{} turns com validação.", count, assistant.len()))
            .with_evidence(evidence)
    }
}
