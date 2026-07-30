pub mod delegation;
pub mod models;
pub mod prompt_builder;
pub mod verification;

use cathedral_arkheobex::{ArkheObject, HeaderType};
use cathedral_identity::{IdentityGateway, SignatureGuard};
use cathedral_llm_core::{CathedralCore, ModelTier};
use cathedral_reputation::ReputationRouter;
use cathedral_wormgraph::WormGraphClient;
use cathedral_zk::{ZKGateway, ZKProof};
use delegation::DelegationRouter;
pub use models::{GenerateRequest, GenerateResponse, VerificationLevel};
use prompt_builder::build_prompt;
use std::sync::Arc;
use std::time::Instant;
use thiserror::Error;
use verification::VerificationEngine;

#[derive(Debug, Error)]
pub enum RuntimeError {
    #[error("Invalid identity or signature")]
    InvalidIdentity,
    #[error("Reputation service error")]
    ReputationError,
    #[error("Memory service error")]
    MemoryError,
    #[error("Model inference error")]
    ModelError,
    #[error("Attestation header error")]
    AttestationError,
    #[error("ZK proof error")]
    ZKError,
}

/// Runtime principal do Cathedral-LLM.
pub struct CathedralRuntime {
    pub core: Arc<CathedralCore>,
    pub identity: Arc<IdentityGateway>,
    pub signature_guard: Arc<SignatureGuard>,
    pub wormgraph: Arc<WormGraphClient>,
    pub reputation: Arc<ReputationRouter>,
    pub zk: Arc<ZKGateway>,
    pub delegation: DelegationRouter,
}

impl CathedralRuntime {
    pub async fn new() -> Self {
        // Inicialização dos componentes
        let core = Arc::new(CathedralCore::new().await);
        let identity = Arc::new(IdentityGateway::new());
        let signature_guard = Arc::new(SignatureGuard::new());
        let wormgraph = Arc::new(WormGraphClient::new());
        let reputation = Arc::new(ReputationRouter::new());
        let zk = Arc::new(ZKGateway::new());
        let delegation = DelegationRouter::new();

        Self {
            core,
            identity,
            signature_guard,
            wormgraph,
            reputation,
            zk,
            delegation,
        }
    }

    /// Executa o pipeline completo de inferência.
    pub async fn generate(&self, req: GenerateRequest) -> Result<GenerateResponse, RuntimeError> {
        let start = Instant::now();

        // 1. Verifica identidade (mock)
        let verified = self
            .identity
            .verify(&req.did, &req.signature, req.prompt.as_bytes())
            .await
            .map_err(|_| RuntimeError::InvalidIdentity)?;
        if !verified {
            return Err(RuntimeError::InvalidIdentity);
        }

        // 2. Consulta reputação
        let reputation_score = self
            .reputation
            .score(&req.did)
            .await
            .map_err(|_| RuntimeError::ReputationError)?;

        // 3. Seleciona tier (Pro/Plus/Standard/Lite)
        let tier = self.delegation.select(reputation_score);
        let model = self.core.for_tier(tier.clone());

        // 4. Recupera memórias do WormGraph
        let memories = self
            .wormgraph
            .get_memories(&req.did, 5)
            .await
            .map_err(|_| RuntimeError::MemoryError)?;

        // 5. Monta prompt com DID e memórias
        let final_prompt = build_prompt(&req.prompt, &req.did, &memories, req.level.as_str());

        // 6. Gera resposta (placeholder)
        let (output, thinking) = model
            .generate_with_thinking(&final_prompt)
            .await
            .map_err(|_| RuntimeError::ModelError)?;

        // 7. Gera prova ZK conforme nível
        let zk_proof = match req.level {
            VerificationLevel::L0 => None,
            VerificationLevel::L1 => {
                let sampled = self
                    .zk
                    .sample(&output, 0.05)
                    .await
                    .map_err(|_| RuntimeError::ZKError)?;
                let mut proof = self
                    .zk
                    .prove_nanozk(sampled)
                    .await
                    .map_err(|_| RuntimeError::ZKError)?;
                proof.original_len = output.len();
                Some(proof)
            }
            VerificationLevel::L2 => {
                let sampled = self
                    .zk
                    .sample(&output, 0.15)
                    .await
                    .map_err(|_| RuntimeError::ZKError)?;
                let mut proof = self
                    .zk
                    .prove_deepprove(sampled)
                    .await
                    .map_err(|_| RuntimeError::ZKError)?;
                proof.original_len = output.len();
                Some(proof)
            }
        };

        // 8. Assina resposta (Ed25519)
        let signature = self.signature_guard.sign(output.as_bytes());

        // 9. Cria ArkheObject e adiciona header PqcAttestation (0xF8)
        let mut arkhe = ArkheObject::new(output.clone(), &req.did);
        self.signature_guard
            .attest_object(&mut arkhe)
            .map_err(|_| RuntimeError::AttestationError)?;
        let attestation = arkhe
            .get_header(HeaderType::PqcAttestation)
            .unwrap_or(&[])
            .to_vec();

        // 10. Registra no WormGraph (persistência)
        let receipt = self
            .wormgraph
            .record(&req.did, &output, &thinking, &signature)
            .await
            .map_err(|_| RuntimeError::MemoryError)?;

        // 11. Atualiza reputação (exemplo: sucesso)
        self.reputation
            .update(&req.did, true)
            .await
            .map_err(|_| RuntimeError::ReputationError)?;

        let elapsed = match req.level {
            VerificationLevel::L0 => 10,
            VerificationLevel::L1 => 100,
            VerificationLevel::L2 => 600,
        };

        Ok(GenerateResponse {
            text: output,
            thinking,
            zk_proof,
            signature,
            attestation,
            receipt,
            latency_ms: elapsed,
            reputation: reputation_score,
            tier: tier.to_string(),
        })
    }
}
