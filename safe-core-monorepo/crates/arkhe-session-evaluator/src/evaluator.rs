use crate::types::*;
use crate::causal_consistency::CausalConsistencyScorer;
use crate::contradiction::ContradictionDetector;
use crate::validation_detector::ValidationDetector;
use crate::artifact_analyzer::ArtifactAnalyzer;
use tracing::info;

const W_CAUSAL: f32 = 0.30;
const W_CONTRA: f32 = 0.25;
const W_VALID: f32 = 0.20;
const W_ARTIF: f32 = 0.25;

pub struct SessionEvaluator {
    causal: CausalConsistencyScorer,
    contradiction: ContradictionDetector,
    validation: ValidationDetector,
    artifact: ArtifactAnalyzer,
}

impl SessionEvaluator {
    pub fn new() -> Self {
        Self {
            causal: CausalConsistencyScorer,
            contradiction: ContradictionDetector,
            validation: ValidationDetector::new(),
            artifact: ArtifactAnalyzer,
        }
    }

    pub async fn evaluate(&self, trajectory: &SessionTrajectory) -> EvaluationResult {
        info!(session = %trajectory.id, turns = trajectory.turns.len(), "Evaluating session");

        let cs = self.causal.score(trajectory).await;
        let ct = self.contradiction.score(trajectory).await;
        let vd = self.validation.score(trajectory).await;
        let aa = self.artifact.score(trajectory).await;

        let dimensions = vec![
            EvaluationDimension { name: "Consistência Causal".into(), score: cs.score, weight: W_CAUSAL, details: cs.details.clone(), evidence: cs.evidence },
            EvaluationDimension { name: "Ausência de Contradição".into(), score: ct.score, weight: W_CONTRA, details: ct.details.clone(), evidence: ct.evidence },
            EvaluationDimension { name: "Validação Explícita".into(), score: vd.score, weight: W_VALID, details: vd.details.clone(), evidence: vd.evidence },
            EvaluationDimension { name: "Qualidade de Artefatos".into(), score: aa.score, weight: W_ARTIF, details: aa.details.clone(), evidence: aa.evidence },
        ];

        let overall: f32 = dimensions.iter().map(|d| d.score * d.weight).sum();

        let (summary, highlights, concerns, suggestions) = self.report(&dimensions, overall);

        info!(session = %trajectory.id, score = %format!("{:.1}%", overall * 100.0), "Evaluation done");

        EvaluationResult { session_id: trajectory.id.clone(), overall_score: overall, dimensions, summary, highlights, concerns, suggestions }
    }

    fn report(&self, dims: &[EvaluationDimension], overall: f32) -> (String, Vec<String>, Vec<String>, Vec<String>) {
        let mut hi = Vec::new();
        let mut co = Vec::new();
        let mut su = Vec::new();

        for d in dims {
            if d.score >= 0.8 {
                hi.push(format!("✅ {} — {:.0}%", d.name, d.score * 100.0));
            } else if d.score < 0.5 {
                co.push(format!("⚠️ {} — {:.0}%: {}", d.name, d.score * 100.0, d.details));
                su.push(match d.name.as_str() {
                    "Consistência Causal" => "Adicione conectivos causais (porque, portanto, logo).",
                    "Ausência de Contradição" => "Revise turnos antes de afirmar o oposto. Use 'corrigindo'.",
                    "Validação Explícita" => "Adicione 'verifiquei que...' nos turnos do assistente.",
                    "Qualidade de Artefatos" => "Inclua #[test] e estrutura compilável (use, impl, pub fn).",
                    _ => "Revise esta dimensão.",
                }.to_string());
            }
        }

        let summary = match overall {
            s if s >= 0.8 => format!("Alta qualidade ({:.0}%).", s * 100.0),
            s if s >= 0.5 => format!("Qualidade moderada ({:.0}%). {} preocupação(ões).", s * 100.0, co.len()),
            _ => format!("Baixa qualidade ({:.0}%). Revisão urgente.", overall * 100.0),
        };

        if co.is_empty() && hi.len() == dims.len() {
            hi.push("🏆 Todas as dimensões ≥ 80%.".to_string());
        }

        (summary, hi, co, su)
    }
}

impl Default for SessionEvaluator { fn default() -> Self { Self::new() } }
