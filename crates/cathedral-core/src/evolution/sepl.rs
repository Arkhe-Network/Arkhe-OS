use crate::skill::builtin::qvac_inference::{QVACInferenceExecutor, QVACConfig};

// Mock structures to fulfill the required signature types
#[derive(Debug, Clone)]
pub struct EvolutionContext {
    pub resource_id: String,
    pub agent_id: String,
    pub goal: String,
}

#[derive(Debug, Clone)]
pub struct Observation {
    pub resource_id: String,
    pub current_version: String,
    pub context: String,
}

#[derive(Debug, Clone)]
pub struct Proposal {
    pub resource_id: String,
    pub target_version: String,
    pub rationale: String,
    pub proposed_by: String,
}

pub struct AutogenesisOperator {
    pub qvac_executor: Option<QVACInferenceExecutor>,
    pub use_qvac: bool,
}

impl AutogenesisOperator {
    pub async fn new_with_qvac(
        default_model_hash: &str,
        qvac_config: QVACConfig,
    ) -> Result<Self, String> {
        let qvac_executor = QVACInferenceExecutor::new(
            qvac_config,
            default_model_hash,
        );

        Ok(Self {
            qvac_executor: Some(qvac_executor),
            use_qvac: true,
        })
    }

    pub fn disable_qvac(&mut self) {
        self.use_qvac = false;
    }

    pub async fn infer_with_strategy(
        &self,
        prompt: &str,
        trace_id: Option<&str>,
    ) -> Result<String, String> {
        if self.use_qvac {
            if let Some(qvac) = &self.qvac_executor {
                match qvac.infer(prompt, None, trace_id).await {
                    Ok(result) => {
                        tracing::info!("✅ [QVAC] Inferência local bem-sucedida");
                        return Ok(result);
                    }
                    Err(e) => {
                        tracing::warn!("❌ [QVAC] Falha: {}, fallback para remote (simulado)", e);
                    }
                }
            }
        }

        tracing::info!("☁️ [Remote] Usando inferência na nuvem (fallback)");
        // Fallback strategy logic here
        Ok(format!("[Fallback] {}", prompt))
    }

    pub async fn reflect(
        &self,
        context: &EvolutionContext,
    ) -> Result<Observation, String> {
        tracing::info!("🔍 [SEPL] Refletindo sobre recurso: {}", context.resource_id);

        let prompt = format!(
            "Analyze resource '{}'. Goal: {}. Produce structured observation.",
            context.resource_id, context.goal
        );

        let response = self.infer_with_strategy(&prompt, None).await?;

        Ok(Observation {
            resource_id: context.resource_id.clone(),
            current_version: "1.0.0".to_string(),
            context: response,
        })
    }

    pub async fn propose(
        &self,
        observation: &Observation,
        context: &EvolutionContext,
    ) -> Result<Proposal, String> {
        tracing::info!("💡 [SEPL] Propondo evolução para: {}", observation.resource_id);

        let prompt = format!(
            "Based on observation: {:?}, propose concrete changes.",
            observation
        );

        let response = self.infer_with_strategy(&prompt, None).await?;

        Ok(Proposal {
            resource_id: observation.resource_id.clone(),
            target_version: format!("{}-proposed", observation.current_version),
            rationale: response,
            proposed_by: context.agent_id.clone(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::skill::builtin::qvac_inference::QVACConfig;

    #[tokio::test]
    async fn test_qvac_hybrid_inference_fallback() {
        let config = QVACConfig::default();
        let mut operator = AutogenesisOperator::new_with_qvac("test_hash", config).await.unwrap();

        // 1. Test local flow
        let result_local = operator.infer_with_strategy("test prompt", None).await.unwrap();
        assert!(result_local.starts_with("[QVAC Local]"));

        // 2. Disable QVAC, test fallback
        operator.disable_qvac();
        let result_fallback = operator.infer_with_strategy("test prompt", None).await.unwrap();
        assert_eq!(result_fallback, "[Fallback] test prompt");
    }

    #[tokio::test]
    async fn test_reflect_observation() {
        let config = QVACConfig::default();
        let operator = AutogenesisOperator::new_with_qvac("test_hash", config).await.unwrap();

        let context = EvolutionContext {
            resource_id: "res1".to_string(),
            agent_id: "agent1".to_string(),
            goal: "improve performance".to_string(),
        };

        let obs = operator.reflect(&context).await.unwrap();
        assert_eq!(obs.resource_id, "res1");
        assert!(obs.context.starts_with("[QVAC Local]"));
    }
}
