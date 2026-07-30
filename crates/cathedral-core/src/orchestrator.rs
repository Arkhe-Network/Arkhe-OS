pub mod subagent_spawner {
    use std::sync::Arc;
    use tokio::sync::RwLock;

    pub enum SandboxType {
        Process { cmd: String, args: Vec<String> }
    }

    pub struct SubagentIdentity {
        pub id: String,
    }

    pub struct Subagent {
        pub identity: SubagentIdentity,
    }

    impl Subagent {
        pub async fn execute(&self, _task: &str, _timeout: Option<f64>) -> Result<crate::attestation::ExecutionAttestation, String> {
            Ok(crate::attestation::ExecutionAttestation {
                id: uuid::Uuid::new_v4().to_string(),
                details: "".to_string(),
                creator: self.identity.id.clone(),
                confidence: 1.0,
                tags: vec![],
                score: 1.0,
                public_key: "".to_string(),
                signature: None,
            })
        }
    }

    pub struct SubagentSpawner {}

    impl SubagentSpawner {
        #[allow(clippy::too_many_arguments)]
        pub fn new(
            _parent_identity: Arc<RwLock<crate::attestation::IdentityAttestation>>,
            _signer: Arc<dyn crate::attestation::AttestationSigner + Send + Sync>,
            _policy_engine: Arc<crate::governance::GeometricPolicyEngine>,
            _attestation_manager: Arc<crate::attestation::AttestationManager>,
            _store: Arc<dyn crate::memory::TrajectoryStore + Send + Sync>,
            _max_subagents: usize,
            _sandbox: SandboxType,
            _llm: Option<()>,
        ) -> Self {
            Self {}
        }

        pub async fn spawn(&self, purpose: &str, _cmd: Vec<String>) -> Result<Subagent, String> {
            Ok(Subagent {
                identity: SubagentIdentity {
                    id: purpose.to_string(),
                }
            })
        }

        pub async fn get(&self, id: &str) -> Option<Subagent> {
            Some(Subagent {
                identity: SubagentIdentity {
                    id: id.to_string(),
                }
            })
        }

        pub async fn terminate(&self, _id: &str) -> Result<(), String> {
            Ok(())
        }

        pub async fn terminate_all(&self) -> Result<(), String> {
            Ok(())
        }

        pub async fn list_active(&self) -> Vec<Subagent> {
            vec![]
        }
    }
}

pub mod sandbox {
    pub fn create_sandbox(sandbox_type: super::subagent_spawner::SandboxType) -> super::subagent_spawner::SandboxType {
        sandbox_type
    }

    pub struct WasiPreview2Sandbox {}

    impl WasiPreview2Sandbox {
        pub async fn new(_wasm: Vec<u8>) -> Result<Self, String> {
            Ok(Self {})
        }

        pub async fn execute(&self, _func: &str, _args: &str) -> Result<(), String> {
            Ok(())
        }
    }
}
