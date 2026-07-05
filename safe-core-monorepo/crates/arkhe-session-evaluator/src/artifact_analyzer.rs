use crate::types::*;

pub struct ArtifactAnalyzer;
impl Default for ArtifactAnalyzer { fn default() -> Self { Self } }

const CODE_INDICATORS: &[&str] = &["fn main()", "use ", "impl ", "pub fn ", "pub struct ", "pub enum "];
const TEST_INDICATORS: &[&str] = &["#[cfg(test)]", "#[test]", "assert_eq!", "assert!"];

impl ArtifactAnalyzer {
    pub async fn score(&self, trajectory: &SessionTrajectory) -> DimensionScore {
        let code: Vec<&Artifact> = trajectory.artifacts.iter()
            .filter(|a| a.artifact_type == ArtifactType::Code)
            .collect();

        if code.is_empty() {
            return DimensionScore::new(0.0, "Nenhum artefato de código.");
        }

        let mut compilable = 0usize;
        let mut testable = 0usize;
        let mut evidence = Vec::new();

        for a in &code {
            let c = CODE_INDICATORS.iter().any(|i| a.content.contains(i));
            let t = TEST_INDICATORS.iter().any(|i| a.content.contains(i));
            if c { compilable += 1; }
            if t { testable += 1; }
            let mut tags = Vec::new();
            if c { tags.push("compilável"); }
            if t { tags.push("testável"); }
            if tags.is_empty() { tags.push("sem indicadores"); }
            evidence.push(format!("Artefato {}: {}", a.id, tags.join(", ")));
        }

        let n = code.len();
        let score = (compilable as f32 / n as f32) * 0.6 + (testable as f32 / n as f32) * 0.4;
        DimensionScore::new(score, format!("{}/{} compilam, {} testáveis.", compilable, n, testable))
            .with_evidence(evidence)
    }
}
