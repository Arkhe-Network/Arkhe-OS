use hyperon_bridge::{init_cathedral_atomspace, expose_dla_state, expose_merkle_root};
use metacognitive_regulator::{MetacognitiveRegulator, PolicySuggestion};
use srta_client::{VerifierClient, Evidence, Action, EvidenceStatus};
use crate::accelerator::TensorZkpAccelerator;
use crate::memory_proof_policy::MemoryProofPolicy;

pub struct DlaEngine;
impl DlaEngine {
    pub fn global() -> Self { Self }
    pub fn try_global() -> Option<Self> { Some(Self) }
    pub fn active_segments(&self) -> usize { 42 }
    pub fn utilization(&self) -> f32 { 0.7 }
    pub fn memory_utilization(&self) -> f32 { 0.7 }
}

pub struct ConsentTokenV3 {
    pub merkle_root: [u8; 32],
}

pub struct EmbodiedCognitiveCore {
    hyperon_space: Option<hyperon::AtomSpace>,
    pub meta_regulator: MetacognitiveRegulator,
    verifier_client: VerifierClient,
    policy: MemoryProofPolicy,
    dla_engine: DlaEngine,
    last_merkle_root: Option<[u8; 32]>,
    device_id: [u8; 16],
    secret_key: ed25519_dalek::SigningKey,
}

impl EmbodiedCognitiveCore {
    pub fn new(gpu_enabled: bool) -> Self {
        let mut space = init_cathedral_atomspace();
        let dla_state = DlaEngine::global();
        expose_dla_state(&mut space, dla_state.active_segments(), dla_state.utilization());
        Self {
            hyperon_space: Some(space),
            meta_regulator: MetacognitiveRegulator::new(100),
            verifier_client: VerifierClient::new("http://localhost"),
            policy: MemoryProofPolicy::default(),
            dla_engine: DlaEngine::global(),
            last_merkle_root: None,
            device_id: [0; 16],
            secret_key: ed25519_dalek::SigningKey::from_bytes(&[1; 32]),
        }
    }

    fn update_hyperon_state(&mut self) {
        if let Some(space) = &mut self.hyperon_space {
            let segments = self.dla_engine.active_segments();
            let util = self.dla_engine.memory_utilization();
            expose_dla_state(space, segments, util);
            if let Some(root) = self.last_merkle_root {
                expose_merkle_root(space, &hex::encode(root));
            }
        }
    }

    pub fn query_symbolic_plan(&self, query: &str) -> Option<String> {
        let space = self.hyperon_space.as_ref()?;
        Some(format!("Plano para '{}': usar prova ZK e enviar evidência.", query))
    }

    pub fn request_consent_with_merkle_commitment(&mut self) -> Result<ConsentTokenV3, &'static str> {
        Ok(ConsentTokenV3 { merkle_root: [0; 32] })
    }

    pub fn tick_zk_with_accelerator(&mut self) -> Result<(), &'static str> {
        let start = std::time::Instant::now();
        let token = self.request_consent_with_merkle_commitment()?;
        let proof_time_ms = start.elapsed().as_millis();

        let confidence = (1.0 - (proof_time_ms as f32 / 1000.0)).clamp(0.0, 1.0);
        let success = true;
        self.meta_regulator.record_confidence(confidence, success);

        for suggestion in self.meta_regulator.suggest_policy_changes() {
            match suggestion {
                PolicySuggestion::AddRule(rule) => {
                    self.policy.add_rule(());
                }
                PolicySuggestion::AdjustThreshold { field, new_value } => {
                    if field == "commitment_interval" {
                        self.policy.set_commitment_interval(new_value as usize);
                    }
                }
                _ => {}
            }
        }

        self.update_hyperon_state();

        let _ = self.submit_consent_evidence(&token);

        Ok(())
    }

    pub async fn submit_consent_evidence(&mut self, token: &ConsentTokenV3) -> EvidenceStatus {
        let action = Action::MemoryProof {
            merkle_root: token.merkle_root,
        };
        let mut evidence = Evidence::new(self.device_id, action, token.merkle_root);
        let _ = evidence.sign(&self.secret_key.to_bytes());
        self.verifier_client.submit_evidence(evidence);
        let statuses = self.verifier_client.send_pending().await;
        statuses.first().cloned().unwrap_or(EvidenceStatus::Pending)
    }
}
