use crate::skill::builtin::qvac_inference::QVACConfig;
use crate::evolution::sepl::AutogenesisOperator;

pub struct SecondSelfOrchestrator {
    pub operator: Option<AutogenesisOperator>,
}

impl SecondSelfOrchestrator {
    pub fn new() -> Self {
        Self { operator: None }
    }

    pub async fn init_evolution_system_with_qvac(
        &mut self,
        default_model_hash: &str,
        qvac_config: QVACConfig,
    ) -> Result<(), String> {
        let operator = AutogenesisOperator::new_with_qvac(
            default_model_hash,
            qvac_config,
        ).await?;

        self.operator = Some(operator);

        tracing::info!("✅ Sistema de evolução inicializado com QVAC local");
        Ok(())
    }
}
