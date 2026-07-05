use arkhe_inference::InferenceEngine;
use arkhe_session_evaluator::SessionTrajectory;
use crate::types::*;
use tracing::info;

/// Agente de reflexão — analisa sessões e extrai padrões aprendidos.
///
/// Genérico sobre InferenceEngine. Não depende de memória diretamente —
/// quem o instanciar decide se consolida padrões na memória.
pub struct ReflectorAgent<I: InferenceEngine> {
    _inference: std::sync::Arc<I>,
    config: ReflectorConfig,
}

impl<I: InferenceEngine> ReflectorAgent<I> {
    pub fn new(inference: std::sync::Arc<I>) -> Self {
        Self { _inference: inference, config: ReflectorConfig::default() }
    }

    pub fn with_config(inference: std::sync::Arc<I>, config: ReflectorConfig) -> Self {
        Self { _inference: inference, config }
    }

    /// Reflete sobre uma trajetória de sessão.
    pub async fn reflect(&self, trajectory: &SessionTrajectory) -> Result<ReflectionReport, String> {
        info!(session = %trajectory.id, "Reflecting");

        let causal = self.extract_causal(trajectory);
        let procedural = self.extract_procedural(trajectory);
        let corrections = self.extract_corrections(trajectory);
        let recommendations = self.recommend(&causal, &procedural, &corrections);

        let quality = ((causal.len() + procedural.len()) as f32 * 0.15).min(1.0);

        Ok(ReflectionReport {
            session_id: trajectory.id.clone(),
            timestamp: chrono::Utc::now(),
            causal_patterns: causal,
            procedural_skills: procedural,
            self_corrections: corrections,
            recommendations,
            quality_score: quality,
        })
    }

    fn extract_causal(&self, traj: &SessionTrajectory) -> Vec<ExtractedPattern> {
        let mut out = Vec::new();
        let causal_words = ["porque", "portanto", "logo", "consequentemente"];

        for turn in &traj.turns {
            if turn.role != arkhe_session_evaluator::TurnRole::Assistant { continue; }
            let lower = turn.content.to_lowercase();
            for word in &causal_words {
                if lower.contains(word) {
                    out.push(ExtractedPattern {
                        id: uuid::Uuid::new_v4().to_string(),
                        pattern_type: PatternType::CausalRule,
                        description: format!("Causal link em turno {}", turn.id),
                        trigger: word.to_string(),
                        confidence: 0.7,
                        source_turns: vec![turn.id.clone()],
                    });
                    break;
                }
            }
            if out.len() >= self.config.max_patterns_per_session { break; }
        }
        out
    }

    fn extract_procedural(&self, traj: &SessionTrajectory) -> Vec<ExtractedPattern> {
        let mut out = Vec::new();
        for artifact in &traj.artifacts {
            if artifact.artifact_type != arkhe_session_evaluator::ArtifactType::Code { continue; }
            let fn_count = artifact.content.lines().filter(|l| l.contains("pub fn ") || l.contains("fn ")).count();
            if fn_count >= 2 {
                out.push(ExtractedPattern {
                    id: uuid::Uuid::new_v4().to_string(),
                    pattern_type: PatternType::ProceduralSkill,
                    description: format!("Skill com {} funções (artefato {})", fn_count, artifact.id),
                    trigger: "Geração de código estruturado".to_string(),
                    confidence: 0.8,
                    source_turns: artifact.metadata.get("turn_id").and_then(|v| v.as_str()).map(String::from).into_iter().collect(),
                });
            }
        }
        out
    }

    fn extract_corrections(&self, traj: &SessionTrajectory) -> Vec<String> {
        traj.turns.iter()
            .filter(|t| {
                let l = t.content.to_lowercase();
                l.contains("corrigindo") || l.contains("na verdade") || l.contains("erro meu")
            })
            .map(|t| format!("Turno {}: auto-correção", t.id))
            .collect()
    }

    fn recommend(&self, causal: &[ExtractedPattern], proc: &[ExtractedPattern], corr: &[String]) -> Vec<String> {
        let mut r = Vec::new();
        if causal.is_empty() { r.push("Adicione raciocínio causal explícito.".to_string()); }
        if proc.is_empty() { r.push("Gere código mais estruturado para extrair skills.".to_string()); }
        if corr.is_empty() { r.push("Pratique auto-correção explícita.".to_string()); }
        if r.is_empty() { r.push("Sessão bem estruturada. Continue.".to_string()); }
        r
    }
}
