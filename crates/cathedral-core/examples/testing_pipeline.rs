//! Cathedral ARKHE v28.5.0 — Pipeline de Testes Soberanos

use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use cathedral_core::orchestrator::subagent_spawner::{SubagentSpawner, SandboxType};
use cathedral_core::orchestrator::sandbox::create_sandbox;
use cathedral_core::attestation::{AttestationManager, IdentityAttestation};
use cathedral_core::attestation::ed25519_signer::Ed25519Signer;
use cathedral_core::governance::GeometricPolicyEngine;
use cathedral_core::memory::TrajectoryStoreImpl;
use cathedral_core::testing::{
    TestOrchestrator,
    IntegrityTestAgent,
    PerformanceTestAgent,
    ChaosTestAgent,
    SecurityTestAgent,
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("🏛️ Cathedral ARKHE — Pipeline de Testes Soberanos v28.5.0");

    let signer = Arc::new(Ed25519Signer::new_random());
    let parent_identity = Arc::new(RwLock::new(IdentityAttestation::default()));
    let policy_engine = Arc::new(GeometricPolicyEngine::new());
    let store = Arc::new(TrajectoryStoreImpl::new());
    let attestation_manager = Arc::new(AttestationManager::new(Some(store.clone())));
    let sandbox = create_sandbox(SandboxType::Process { cmd: "echo".to_string(), args: vec![] });

    let spawner = Arc::new(SubagentSpawner::new(
        parent_identity,
        signer.clone() as Arc<dyn cathedral_core::attestation::AttestationSigner + Send + Sync>,
        policy_engine,
        attestation_manager.clone(),
        store.clone(),
        50,
        sandbox,
        None,
    ));

    info!("📦 Criando subagentes para testar...");
    let sub1 = spawner.spawn("test_target_1", vec!["echo".to_string()]).await?;
    let sub2 = spawner.spawn("test_target_2", vec!["echo".to_string()]).await?;
    info!("✅ Subagentes criados: {}, {}", sub1.identity.id, sub2.identity.id);

    let mut orchestrator = TestOrchestrator::new(
        spawner.clone(),
        attestation_manager.clone(),
        store.clone(),
        signer.clone(),
    );

    orchestrator.register_test_agent(Arc::new(IntegrityTestAgent::new(
        attestation_manager.clone(),
        store.clone(),
        signer.clone(),
        10,
    )));
    orchestrator.register_test_agent(Arc::new(PerformanceTestAgent::new(
        spawner.clone(),
        signer.clone(),
        5,
    )));
    orchestrator.register_test_agent(Arc::new(ChaosTestAgent::new(
        spawner.clone(),
        0.3,
        20.0,
    )));
    orchestrator.register_test_agent(Arc::new(SecurityTestAgent::new()));

    let results = orchestrator.run_all_tests().await;

    let passed = results.iter().filter(|r| r.passed).count();
    let total = results.len();
    info!("📊 Resultados: {}/{} testes passaram", passed, total);

    for result in results {
        info!(
            "   {}: {} ({:?}) - {}ms",
            if result.passed { "✅" } else { "❌" },
            result.test_name,
            result.test_type,
            result.duration_ms
        );
    }

    let stats = orchestrator.stats().await;
    info!("📊 Estatísticas do orquestrador:\n{}", serde_json::to_string_pretty(&stats)?);

    spawner.terminate(&sub1.identity.id).await?;
    spawner.terminate(&sub2.identity.id).await?;
    spawner.terminate_all().await?;
    info!("🧹 Pipeline concluído.");

    Ok(())
}
