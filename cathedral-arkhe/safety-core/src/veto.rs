use crate::seam_integrity::ConsistencyResult;

/// Métricas reais do modelo. NÃO órfãs mais. Consumidas diretamente pelo Veto.
#[derive(Debug, Clone)]
pub struct RealMetrics {
    pub perplexity: f64,
    pub token_entropy: f64,
    pub rag_density: f64,
}

#[derive(Debug, PartialEq, Eq)]
pub enum VetoAction {
    Allow,
    HaltAndLog(String),
}

pub enum VetoReason {
    SeamRupture,
    LackOfEvidence,
    EntropySpike, // AGORA ESTÁ ATIVO
}

pub struct AnubisVetoV3 {
    pub seam_tolerance: f64,
    pub entropy_limit: f64,
}

impl AnubisVetoV3 {
    pub fn evaluate(
        &self,
        consistency: &ConsistencyResult,
        metrics: &RealMetrics, // AGORA É CONSUMIDO
        context: &str,
    ) -> VetoAction {
        // 1. Verificar a entropia PRIMEIRO (métrica de menor latência)
        if metrics.token_entropy > self.entropy_limit {
            return VetoAction::HaltAndLog(format!(
                "[VETO] EntropySpike: {} > {}. Context: {}",
                metrics.token_entropy, self.entropy_limit, context
            ));
        }

        // 2. Verificar a integridade da costura
        match consistency {
            ConsistencyResult::HallucinationRisk => {
                VetoAction::HaltAndLog(format!("[VETO] HallucinationRisk em '{}'", context))
            }
            ConsistencyResult::Paraphrase => {
                VetoAction::Allow // Falso negativo benigno
            }
            _ => VetoAction::Allow,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_veto_logic() {
        let veto = AnubisVetoV3 {
            seam_tolerance: 0.8,
            entropy_limit: 1.5,
        };

        let ok_metrics = RealMetrics {
            perplexity: 10.0,
            token_entropy: 1.0,
            rag_density: 0.8,
        };
        let bad_metrics = RealMetrics {
            token_entropy: 2.0,
            ..ok_metrics.clone()
        };

        // Test EntropySpike
        match veto.evaluate(&ConsistencyResult::Consistent, &bad_metrics, "test") {
            VetoAction::HaltAndLog(msg) => assert!(msg.contains("EntropySpike")),
            _ => panic!("Expected HaltAndLog for EntropySpike"),
        }

        // Test HallucinationRisk
        match veto.evaluate(&ConsistencyResult::HallucinationRisk, &ok_metrics, "test") {
            VetoAction::HaltAndLog(msg) => assert!(msg.contains("HallucinationRisk")),
            _ => panic!("Expected HaltAndLog for HallucinationRisk"),
        }

        // Test Paraphrase (should be allowed)
        assert_eq!(
            veto.evaluate(&ConsistencyResult::Paraphrase, &ok_metrics, "test"),
            VetoAction::Allow
        );

        // Test Consistent (should be allowed)
        assert_eq!(
            veto.evaluate(&ConsistencyResult::Consistent, &ok_metrics, "test"),
            VetoAction::Allow
        );
    }
}
