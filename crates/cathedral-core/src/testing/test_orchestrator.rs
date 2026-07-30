//! Cathedral ARKHE v28.5.0 — Orquestrador de Testes Soberano

use std::sync::Arc;
use tracing::{info, error, instrument};
use serde_json::json;

use crate::testing::test_agent::{TestAgent, TestResult};
use crate::orchestrator::subagent_spawner::SubagentSpawner;
use crate::attestation::{AttestationManager, AttestationSigner};
use crate::memory::TrajectoryStore;

/// Orquestrador que executa múltiplos agentes de teste e agrega resultados.
pub struct TestOrchestrator {
    pub spawner: Arc<SubagentSpawner>,
    pub attestation_manager: Arc<AttestationManager>,
    pub store: Arc<dyn TrajectoryStore + Send + Sync>,
    pub signer: Arc<dyn AttestationSigner + Send + Sync>,
    pub test_agents: Vec<Arc<dyn TestAgent>>,
}

impl TestOrchestrator {
    pub fn new(
        spawner: Arc<SubagentSpawner>,
        attestation_manager: Arc<AttestationManager>,
        store: Arc<dyn TrajectoryStore + Send + Sync>,
        signer: Arc<dyn AttestationSigner + Send + Sync>,
    ) -> Self {
        Self {
            spawner,
            attestation_manager,
            store,
            signer,
            test_agents: Vec::new(),
        }
    }

    pub fn register_test_agent(&mut self, agent: Arc<dyn TestAgent>) {
        info!("📋 Agente de teste registado: {}", agent.test_name());
        self.test_agents.push(agent);
    }

    /// Executa todos os agentes de teste registados.
    #[instrument(name = "test_orchestrator.run_all", skip(self))]
    pub async fn run_all_tests(&self) -> Vec<TestResult> {
        info!("🚀 Executando todos os {} testes...", self.test_agents.len());

        let context = crate::testing::test_agent::TestContext::new("orchestrator");

        let mut handles = Vec::new();
        for agent in &self.test_agents {
            let ctx = context.clone();
            let agent_clone = agent.clone();
            handles.push(tokio::spawn(async move {
                agent_clone.run_test(&ctx).await
            }));
        }

        let results = futures::future::join_all(handles).await;
        let mut test_results = Vec::new();

        for result in results {
            match result {
                Ok(Ok(test_result)) => {
                    let json = serde_json::to_string(&test_result).unwrap_or_default();
                    let _ = self.store.record_trajectory(
                        "test_orchestrator",
                        &format!("test_result:{}", test_result.test_name),
                        vec![format!("{:?}", test_result.test_type)],
                        &json,
                        vec![],
                        vec![],
                    ).await;
                    test_results.push(test_result);
                }
                Ok(Err(e)) => error!("Erro no teste: {}", e),
                Err(e) => error!("Panic no teste: {}", e),
            }
        }

        self.generate_report(&test_results).await;
        info!("✅ Testes concluídos: {} resultados", test_results.len());
        test_results
    }

    pub async fn generate_report(&self, results: &[TestResult]) {
        let total = results.len();
        let passed = results.iter().filter(|r| r.passed).count();
        let failed = total - passed;

        let report = json!({
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": if total > 0 { passed as f64 / total as f64 } else { 0.0 },
            "results": results.iter().map(|r| json!({
                "name": r.test_name,
                "type": format!("{:?}", r.test_type),
                "passed": r.passed,
                "duration_ms": r.duration_ms,
                "details": &r.details,
            })).collect::<Vec<_>>(),
        });

        let report_json = serde_json::to_string_pretty(&report).unwrap_or_default();
        info!("📊 Relatório de testes:\n{}", report_json);

        let _ = self.store.record_trajectory(
            "test_orchestrator",
            "test_report",
            vec![],
            &report_json,
            vec![],
            vec![],
        ).await;

        // Gerar atestado do relatório (assinado)
        let mut attestation = crate::attestation::ExecutionAttestation::new(
            "test_report",
            &report_json,
            "test_orchestrator",
            0.0,
            vec!["test".to_string()],
            1.0,
            &self.signer.public_key(),
        );
        let _ = attestation.sign(self.signer.as_ref());
        let _ = self.attestation_manager.store_attestation(attestation).await;
    }

    pub async fn stats(&self) -> serde_json::Value {
        let trajs = self.store.list_trajectories().await;
        let test_results: Vec<_> = trajs.iter()
            .filter(|t| t.goal.starts_with("test_result:"))
            .collect();

        json!({
            "total_test_results": test_results.len(),
            "registered_test_agents": self.test_agents.len(),
        })
    }
}
