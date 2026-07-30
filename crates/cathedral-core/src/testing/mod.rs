//! Cathedral ARKHE v28.5.0 — Testes Soberanos
//! Agentes especializados em testar a integridade, performance, resiliência e segurança do sistema.

mod test_agent;
mod integrity_test_agent;
mod performance_test_agent;
mod chaos_test_agent;
mod security_test_agent;
mod compliance_test_agent;
mod integration_test_agent;
mod test_orchestrator;
mod test_attestation;
mod otel_integration;

pub use test_agent::{TestAgent, TestResult, TestType, TestContext};
pub use integrity_test_agent::IntegrityTestAgent;
pub use performance_test_agent::PerformanceTestAgent;
pub use chaos_test_agent::ChaosTestAgent;
pub use security_test_agent::SecurityTestAgent;
pub use compliance_test_agent::ComplianceTestAgent;
pub use integration_test_agent::IntegrationTestAgent;
pub use test_orchestrator::TestOrchestrator;
pub use test_attestation::{TestAttestation, TestAttestationExt};
pub use otel_integration::TraceableTestAgent;
