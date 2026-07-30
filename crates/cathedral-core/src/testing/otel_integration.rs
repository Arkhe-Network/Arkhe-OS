//! Cathedral ARKHE v28.5.0 — OpenTelemetry Integration for Testing

use tracing::{info, error, span, Level, instrument};
use async_trait::async_trait;

use crate::testing::test_agent::{TestAgent, TestResult, TestContext};
use crate::testing::TestOrchestrator;
use crate::testing::test_attestation::TestAttestationExt;

/// Extensão para adicionar tracing a TestAgent.
#[async_trait]
pub trait TraceableTestAgent: TestAgent {
    async fn run_test_with_tracing(&self, context: &TestContext) -> Result<TestResult, String> {
        let span = span!(
            Level::INFO,
            "test.agent",
            test_name = %self.test_name(),
            test_type = ?self.test_type(),
            agent_id = %context.agent_id,
        );
        let _enter = span.enter();

        info!("🔄 Executando teste com tracing: {}", self.test_name());

        let result = self.run_test(context).await;

        match &result {
            Ok(test_result) => {
                span.record("passed", &test_result.passed);
                span.record("duration_ms", &test_result.duration_ms);
                info!("✅ Teste concluído: {} (passou: {})", test_result.test_name, test_result.passed);
            }
            Err(e) => {
                span.record("error", &e.as_str());
                error!("❌ Teste falhou: {} - {}", self.test_name(), e);
            }
        }

        result
    }
}

/// Aplica automaticamente a todos os TestAgent.
impl<T: ?Sized + TestAgent> TraceableTestAgent for T {}

/// Atualiza o TestOrchestrator para usar tracing em cada teste.
impl TestOrchestrator {
    #[instrument(name = "test_orchestrator.run_all", skip(self))]
    pub async fn run_all_tests_with_tracing(&self) -> Vec<TestResult> {
        info!("🚀 Executando todos os testes com OpenTelemetry...");

        let context = crate::testing::test_agent::TestContext::new("orchestrator");

        let mut handles = Vec::new();
        for agent in &self.test_agents {
            let ctx = context.clone();
            let agent_clone = agent.clone();
            handles.push(tokio::spawn(async move {
                agent_clone.run_test_with_tracing(&ctx).await
            }));
        }

        let results = futures::future::join_all(handles).await;
        let mut test_results = Vec::new();

        for result in results {
            match result {
                Ok(Ok(test_result)) => {
                    // Persistir como TestAttestation
                    if let Err(e) = test_result.store_test_result_as_attestation(
                        self.signer.as_ref(),
                        self.store.as_ref(),
                    ).await {
                        error!("Falha ao persistir atestado de teste: {}", e);
                    }
                    test_results.push(test_result);
                }
                Ok(Err(e)) => error!("Erro no teste: {}", e),
                Err(e) => error!("Panic no teste: {}", e),
            }
        }

        self.generate_report(&test_results).await;
        info!("✅ Testes concluídos com tracing: {} resultados", test_results.len());
        test_results
    }
}
