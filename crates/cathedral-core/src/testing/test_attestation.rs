//! Cathedral ARKHE v28.5.0 — Atestado Especializado para Testes

use serde::{Deserialize, Serialize};

use crate::testing::test_agent::{TestResult};
use crate::attestation::ExecutionAttestation;
use crate::memory::TrajectoryStore;

/// Atestado especializado para testes (extends ExecutionAttestation).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestAttestation {
    pub attestation_id: String,
    pub test_result: TestResult,
    pub signature: Option<String>,
    pub verified: bool,
}

impl TestAttestation {
    pub fn new(test_result: TestResult) -> Self {
        Self {
            attestation_id: uuid::Uuid::new_v4().to_string(),
            test_result,
            signature: None,
            verified: false,
        }
    }

    /// Assina o atestado com o signer fornecido.
    pub async fn sign(
        &mut self,
        signer: &dyn crate::attestation::AttestationSigner,
    ) -> Result<(), String> {
        let data = serde_json::to_string(&self)
            .map_err(|e| format!("Serialization error: {}", e))?;
        self.signature = Some(signer.sign(&data)?);
        Ok(())
    }

    /// Verifica a assinatura.
    pub fn verify(&self, signer: &dyn crate::attestation::AttestationSigner) -> Result<bool, String> {
        let sig = self.signature.as_ref().ok_or("No signature")?;
        let data = serde_json::to_string(self)
            .map_err(|e| format!("Serialization error: {}", e))?;
        signer.verify(&data, sig)
    }

    /// Persiste o atestado no TrajectoryStore.
    pub async fn persist(
        &self,
        store: &dyn TrajectoryStore,
    ) -> Result<String, String> {
        let json = serde_json::to_string(self)
            .map_err(|e| format!("Serialization error: {}", e))?;
        let goal = format!(
            "test_attestation:{}:{:?}",
            self.test_result.test_name,
            self.test_result.test_type
        );
        store.record_trajectory(
            "test_orchestrator",
            &goal,
            vec![self.test_result.test_name.clone()],
            &json,
            vec![],
            vec![],
        ).await
    }

    /// Converte para um ExecutionAttestation (para compatibilidade).
    pub fn to_execution_attestation(&self) -> ExecutionAttestation {
        let details = serde_json::to_string(&self.test_result.details).unwrap_or_default();
        ExecutionAttestation::new(
            &format!("test:{}", self.test_result.test_name),
            &details,
            "test_orchestrator",
            0.0,
            vec![self.test_result.test_name.clone()],
            if self.test_result.passed { 1.0 } else { 0.0 },
            "test_public_key",
        )
    }
}

/// Atualiza o TestOrchestrator para usar TestAttestation.
pub trait TestAttestationExt {
    async fn store_test_result_as_attestation(
        &self,
        signer: &dyn crate::attestation::AttestationSigner,
        store: &dyn TrajectoryStore,
    ) -> Result<String, String>;
}

impl TestAttestationExt for TestResult {
    async fn store_test_result_as_attestation(
        &self,
        signer: &dyn crate::attestation::AttestationSigner,
        store: &dyn TrajectoryStore,
    ) -> Result<String, String> {
        let mut att = TestAttestation::new(self.clone());
        att.sign(signer).await?;
        att.persist(store).await
    }
}
